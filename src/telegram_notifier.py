#!/usr/bin/env python3
"""
Telegram Notifier  
Sendet Benachrichtigungen über neue Zugverbindungen via Telegram Bot
Produktionsversion - optimiert für zuverlässige Nachrichten
"""

import requests
import logging
from typing import List, Optional, Dict
from datetime import datetime
from db_client import Journey

class TelegramNotifier:
    """Telegram Bot für Bahnverbindungs-Benachrichtigungen"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, message: str, retry_count: int = 2) -> bool:
        """Sende Textnachricht an Telegram Chat mit Retry-Logik"""
        url = f"{self.api_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        for attempt in range(retry_count + 1):
            try:
                self.logger.debug(f"Sende Telegram Nachricht (Versuch {attempt + 1}): {message[:50]}...")
                response = requests.post(url, json=payload, timeout=15)
                
                if response.status_code == 200:
                    self.logger.info("Telegram Nachricht erfolgreich gesendet")
                    return True
                else:
                    self.logger.error(f"Telegram API Error {response.status_code}: {response.text}")
                    if attempt < retry_count:
                        self.logger.info(f"Wiederhole in 5 Sekunden... (Versuch {attempt + 2})")
                        import time
                        time.sleep(5)
                        
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Telegram Request Exception: {str(e)}")
                if attempt < retry_count:
                    self.logger.info(f"Wiederhole in 5 Sekunden... (Versuch {attempt + 2})")
                    import time
                    time.sleep(5)
        
        self.logger.error("Telegram Nachricht konnte nach allen Versuchen nicht gesendet werden")
        return False
    
    def test_connection(self) -> bool:
        """Teste Telegram Bot Verbindung"""
        url = f"{self.api_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                bot_name = bot_info.get("result", {}).get("username", "Unknown")
                self.logger.info(f"Telegram Bot verbunden: @{bot_name}")
                return True
            else:
                self.logger.error(f"Telegram Bot Test fehlgeschlagen: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Telegram Test Exception: {str(e)}")
            return False
    
    def notify_connections(self, 
                         connections: List[Journey], 
                         date: str,
                         from_station: str = "Hamburg Hbf",
                         to_station: str = "Landeck-Zams") -> bool:
        """Benachrichtige über gefundene Verbindungen"""
        
        if not connections:
            return True
        
        # Header
        count = len(connections)
        plural = "en" if count != 1 else ""
        message_lines = [
            f"🚄 *Verbindung{plural} gefunden*",
            f"📅 *Datum:* {date}",
            f"🚉 *Route:* {from_station} → {to_station}",
            "",
        ]
        
        # Verbindungen auflisten
        for i, journey in enumerate(connections, 1):
            dep_time = journey.departure_time.strftime("%H:%M")
            arr_time = journey.arrival_time.strftime("%H:%M")
            duration_hours = journey.duration_minutes // 60
            duration_mins = journey.duration_minutes % 60
            duration_str = f"{duration_hours}h {duration_mins:02d}m"
            
            transfers_text = "Direktverbindung" if journey.transfers == 0 else f"{journey.transfers} Umstieg{'e' if journey.transfers > 1 else ''}"
            
            message_lines.append(f"*{i}.* {dep_time} → {arr_time}")
            message_lines.append(f"   Dauer: {duration_str}, {transfers_text}")
            message_lines.append("")
        
        # Footer
        message_lines.extend([
            f"⏰ *Abfrage vom:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Verbindungssuche Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_single_day_connections(self, 
                                    connections: List[Journey], 
                                    date: str,
                                    from_station: str = "Hamburg Hbf",
                                    to_station: str = "Landeck-Zams",
                                    date_description: str = None) -> bool:
        """Benachrichtige über Verbindungen für einen einzelnen Tag"""
        
        if not connections:
            return True
        
        # Header
        count = len(connections)
        plural = "en" if count != 1 else ""
        display_date = date_description if date_description else date
        message_lines = [
            f"🚄 *{count} Verbindung{plural} am {display_date}*",
            f"🚉 *Route:* {from_station} → {to_station}",
            "",
        ]
        
        # Verbindungen auflisten
        for i, journey in enumerate(connections, 1):
            dep_time = journey.departure_time.strftime("%H:%M")
            arr_time = journey.arrival_time.strftime("%H:%M")
            duration_hours = journey.duration_minutes // 60
            duration_mins = journey.duration_minutes % 60
            duration_str = f"{duration_hours}h {duration_mins:02d}m"
            
            transfers_text = "Direktverbindung" if journey.transfers == 0 else f"{journey.transfers} Umstieg{'e' if journey.transfers > 1 else ''}"
            
            message_lines.append(f"**{i}.** {dep_time} → {arr_time}")
            message_lines.append(f"   _{duration_str}, {transfers_text}_")
            message_lines.append("")
        
        # Footer
        message_lines.extend([
            f"⏰ *Abfrage vom:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Verbindungssuche Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_all_connections(self, 
                             connections_by_date: Dict[str, List[Journey]],
                             from_station: str = "Hamburg Hbf",
                             to_station: str = "Landeck-Zams") -> bool:
        """Benachrichtige über alle gefundenen Verbindungen (alle Tage zusammen)"""
        
        if not connections_by_date:
            return True
        
        # Berechne Gesamtzahl
        total_connections = sum(len(journeys) for journeys in connections_by_date.values())
        total_days = len(connections_by_date)
        
        # Header
        message_lines = [
            f"🚄 *Alle gefundenen Verbindungen*",
            f"🚉 *Route:* {from_station} → {to_station}",
            f"📊 *{total_connections} Verbindungen an {total_days} Tagen*",
            "",
        ]
        
        # Pro Tag auflisten
        for date_str in sorted(connections_by_date.keys()):
            journeys = connections_by_date[date_str]
            message_lines.append(f"📅 **{date_str}** ({len(journeys)} Verbindungen):")
            
            for journey in journeys:
                dep_time = journey.departure_time.strftime("%H:%M")
                arr_time = journey.arrival_time.strftime("%H:%M")
                duration_hours = journey.duration_minutes // 60
                duration_mins = journey.duration_minutes % 60
                duration_str = f"{duration_hours}h {duration_mins:02d}m"
                
                transfers_text = "Direktverbindung" if journey.transfers == 0 else f"{journey.transfers} Umstieg{'e' if journey.transfers > 1 else ''}"
                
                message_lines.append(f"   • {dep_time} → {arr_time} ({duration_str}, {transfers_text})")
            
            message_lines.append("")  # Leerzeile nach jedem Tag
        
        # Footer
        message_lines.extend([
            f"⏰ *Abfrage vom:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Verbindungssuche Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_error(self, error_message: str, context: str = "") -> bool:
        """Benachrichtige über Fehler"""
        message_lines = [
            "⚠️ *Fehler bei Verbindungssuche*",
            "",
            f"*Fehler:* {error_message}",
        ]
        
        if context:
            message_lines.append(f"*Kontext:* {context}")
        
        message_lines.extend([
            "",
            f"*Zeit:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🔧 _Prüfung der Anwendung empfohlen_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_status(self, 
                     checked_dates: int, 
                     total_connections: int) -> bool:
        """Sende Status-Update"""
        message_lines = [
            "📊 *Verbindungssuche Status*",
            "",
            f"📅 *Geprüfte Tage:* {checked_dates}",
            f"🚄 *Gefundene Verbindungen:* {total_connections}",
        ]
        
        if total_connections == 0:
            message_lines.append("⚠️ *Keine Verbindungen verfügbar*")
        
        message_lines.extend([
            "",
            f"⏰ *Letzter Check:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Verbindungssuche Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_startup(self) -> bool:
        """Benachrichtige über Anwendungsstart"""
        message_lines = [
            "🚀 *Verbindungssuche gestartet*",
            "",
            "🚉 *Route:* Hamburg Hbf → Landeck-Zams",
            "⏰ *Frequenz:* 4x täglich",
            "",
            f"*Gestartet:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🔍 _Verbindungssuche läuft..._"
        ]
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_startup_completed(self, target_day: int, connections_found: int, 
                               from_station: str = "Hamburg Hbf", 
                               to_station: str = "Landeck-Zams",
                               date_description: str = None) -> bool:
        """Benachrichtige über abgeschlossenen Startup mit Suchergebnissen"""
        display_date = date_description if date_description else f"{target_day}. Tag"
        message_lines = [
            "🚀 *Verbindungssuche abgeschlossen*",
            "",
            f"🚉 *Route:* {from_station} → {to_station}",
            f"📅 *Zieltag:* {display_date}",
        ]
        
        if connections_found > 0:
            plural = "en" if connections_found != 1 else ""
            message_lines.append(f"✅ *{connections_found} Verbindung{plural} gefunden*")
        else:
            message_lines.append("⚠️ *Keine Verbindungen verfügbar*")
        
        message_lines.extend([
            "",
            "⏰ *Nächste Suche:* In 3 Minuten",
            "",
            f"*Gestartet:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Überwachung alle 3 Minuten..._"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_connections_now_available(self, 
                                       connections: List[Journey], 
                                       date: str,
                                       from_station: str = "Hamburg Hbf",
                                       to_station: str = "Landeck-Zams",
                                       date_description: str = None) -> bool:
        """Benachrichtige über ERSTMALIG verfügbare Verbindungen (wichtig!)"""
        
        if not connections:
            return True
        
        count = len(connections)
        plural = "en" if count != 1 else ""
        display_date = date_description if date_description else date
        
        message_lines = [
            "🎉 *NEUE VERBINDUNGEN VERFÜGBAR!*",
            "",
            f"🚄 *{count} Verbindung{plural} für {display_date}*",
            f"🚉 *Route:* {from_station} → {to_station}",
            "",
            "🔥 *Diese Verbindungen sind jetzt buchbar:*",
            "",
        ]
        
        # Verbindungen auflisten
        for i, journey in enumerate(connections, 1):
            dep_time = journey.departure_time.strftime("%H:%M")
            arr_time = journey.arrival_time.strftime("%H:%M")
            duration_hours = journey.duration_minutes // 60
            duration_mins = journey.duration_minutes % 60
            duration_str = f"{duration_hours}h {duration_mins:02d}m"
            
            transfers_text = "Direktverbindung" if journey.transfers == 0 else f"{journey.transfers} Umstieg{'e' if journey.transfers > 1 else ''}"
            
            message_lines.append(f"🚆 **{i}.** {dep_time} → {arr_time}")
            message_lines.append(f"     ⏱ {duration_str} • {transfers_text}")
            message_lines.append("")
        
        # Footer
        message_lines.extend([
            "⚡ *SCHNELL BUCHEN EMPFOHLEN!*",
            "",
            f"📅 *Erkannt am:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🎯 _Zukünftige Verbindungen erfolgreich gefunden_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_no_connections_found(self, target_day: int, checked_dates: int,
                                   from_station: str = "Hamburg Hbf",
                                   to_station: str = "Landeck-Zams", 
                                   date_description: str = None) -> bool:
        """Benachrichtige dass keine Verbindungen gefunden wurden"""
        display_date = date_description if date_description else f"{target_day}. Tag"
        message_lines = [
            "🔍 *Verbindungssuche durchgeführt*",
            "",
            f"🚉 *Route:* {from_station} → {to_station}",
            f"📅 *Zieltag:* {display_date}",
            "",
            "⚠️ *Keine Verbindungen verfügbar*",
            "",
            f"📊 *Geprüfte Tage:* {checked_dates}",
            f"⏰ *Letzter Check:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🔄 _Nächste Suche in 3 Minuten_"
        ]
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def send_test_message(self) -> bool:
        """Sende Test-Nachricht"""
        message = (
            "🧪 *Test-Nachricht*\n\n"
            f"Bot funktioniert korrekt!\n"
            f"Zeit: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            "🤖 _Bahnverbindungsüberwachung Hamburg → Landeck-Zams_"
        )
        return self.send_message(message)