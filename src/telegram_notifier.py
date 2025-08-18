#!/usr/bin/env python3
"""
Telegram Notifier  
Sendet Benachrichtigungen über neue Zugverbindungen via Telegram Bot
Produktionsversion - optimiert für zuverlässige Nachrichten
"""

import requests
import logging
from typing import List, Optional
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
    
    def notify_new_connections(self, 
                             new_connections: List[Journey], 
                             date: str,
                             from_station: str = "Hamburg Hbf",
                             to_station: str = "Landeck-Zams") -> bool:
        """Benachrichtige über neue Verbindungen"""
        
        if not new_connections:
            return True
        
        # Header
        count = len(new_connections)
        plural = "en" if count != 1 else ""
        message_lines = [
            f"🚄 *Neue Verbindung{plural} verfügbar!*",
            f"📅 *Datum:* {date}",
            f"🚉 *Route:* {from_station} → {to_station}",
            "",
        ]
        
        # Verbindungen auflisten
        for i, journey in enumerate(new_connections, 1):
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
            f"⏰ *Gefunden am:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Überwachung Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_error(self, error_message: str, context: str = "") -> bool:
        """Benachrichtige über Fehler"""
        message_lines = [
            "⚠️ *Fehler bei Verbindungsüberwachung*",
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
                     total_connections: int,
                     new_connections: int = 0) -> bool:
        """Sende Status-Update"""
        message_lines = [
            "📊 *Verbindungsüberwachung Status*",
            "",
            f"📅 *Geprüfte Tage:* {checked_dates}",
            f"🚄 *Gefundene Verbindungen:* {total_connections}",
        ]
        
        if new_connections > 0:
            message_lines.append(f"✨ *Neue Verbindungen:* {new_connections}")
        else:
            message_lines.append("✅ *Keine neuen Verbindungen*")
        
        message_lines.extend([
            "",
            f"⏰ *Letzter Check:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🤖 _Automatische Überwachung Hamburg → Landeck-Zams_"
        ])
        
        message = "\n".join(message_lines)
        return self.send_message(message)
    
    def notify_startup(self) -> bool:
        """Benachrichtige über Anwendungsstart"""
        message_lines = [
            "🚀 *Verbindungsüberwachung gestartet*",
            "",
            "🚉 *Route:* Hamburg Hbf → Landeck-Zams",
            "📅 *Zeitraum:* März 2025",
            "⏰ *Frequenz:* 4x täglich",
            "",
            f"*Gestartet:* {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "",
            "🔍 _Überwachung läuft..._"
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