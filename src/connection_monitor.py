#!/usr/bin/env python3
"""
Connection Monitor
Überwacht neue Zugverbindungen Hamburg → Landeck-Zams für März 2025
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from db_client import DBClient, Journey, HAMBURG_HBF_ID, LANDECK_ZAMS_ID
from telegram_notifier import TelegramNotifier

# ConnectionSignature entfernt - keine Duplikatserkennung mehr nötig

class ConnectionMonitor:
    """Hauptlogik für die Verbindungsüberwachung"""
    
    def __init__(self, db_client: DBClient, telegram_notifier: TelegramNotifier, config):
        self.db_client = db_client
        self.telegram = telegram_notifier
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Statistiken für diese Session (vereinfacht)
        self.session_stats = {
            "start_time": datetime.now(),
            "total_api_calls": 0,
            "dates_checked": 0,
            "connections_found": 0,
            "errors": []
        }
        
        # Für Zukunfts-Monitoring: Tracke ob schon mal Verbindungen gefunden wurden
        self.previous_connections_found = False
    
    # Duplikats-Erkennungs-Methoden entfernt - zeige immer alle Verbindungen
    
    def check_single_date(self, target_date: datetime) -> List[Journey]:
        """Prüfe Verbindungen für ein bestimmtes Datum"""
        date_str = target_date.strftime("%Y-%m-%d")
        self.logger.info(f"Prüfe Verbindungen für {date_str}")
        
        try:
            # API-Aufruf
            journeys = self.db_client.search_journeys(
                HAMBURG_HBF_ID, 
                LANDECK_ZAMS_ID, 
                target_date,
                max_results=20
            )
            
            self.session_stats["total_api_calls"] += 1
            self.session_stats["dates_checked"] += 1
            self.session_stats["connections_found"] += len(journeys)
            
            if journeys:
                self.logger.info(f"Gefunden: {len(journeys)} Verbindungen für {date_str}")
            else:
                self.logger.debug(f"Keine Verbindungen für {date_str} (bei Zukunfts-Monitoring normal)")
            
            return journeys
            
        except Exception as e:
            error_msg = f"Fehler bei Abfrage für {date_str}: {str(e)}"
            self.logger.error(error_msg)
            self.session_stats["errors"].append(error_msg)
            return []
    
    # filter_new_connections entfernt - verwende immer alle gefundenen Verbindungen
    
    def check_target_day_connections(self, target_day: int, start_hour: int = 8) -> List[Journey]:
        """Prüfe Verbindungen für einen einzelnen Tag im konfigurierten Monat"""
        date_description = self.config.get_formatted_date_description()
        self.logger.info(f"Starte Verbindungssuche für {date_description}")
        
        try:
            # Hole Jahr und Monat aus Konfiguration
            year, month = self.config.get_target_year_month()
            
            # Erstelle Zieldatum aus Konfiguration
            target_date = datetime(year, month, target_day, start_hour, 0)
            
            # Prüfe Verbindungen für diesen Tag
            journeys = self.check_single_date(target_date)
            
            if journeys:
                date_str = target_date.strftime("%Y-%m-%d")
                self.logger.info(f"📅 {len(journeys)} Verbindungen gefunden für {date_str}")
                
                # Prüfe ob das ERSTMALIG gefundene Verbindungen sind
                if not self.previous_connections_found:
                    # ERSTE MAL - Spezielle "NEUE VERBINDUNGEN VERFÜGBAR" Nachricht
                    self.telegram.notify_connections_now_available(
                        journeys,
                        date_str,
                        self.config.departure_station,
                        self.config.destination_station,
                        date_description
                    )
                    self.previous_connections_found = True
                    self.logger.info("🎉 ERSTMALIG Verbindungen gefunden - Spezielle Benachrichtigung gesendet")
                else:
                    # Wiederholter Fund - normale Nachricht
                    self.telegram.notify_single_day_connections(
                        journeys,
                        date_str,
                        self.config.departure_station,
                        self.config.destination_station,
                        date_description
                    )
            else:
                self.logger.info(f"Keine Verbindungen für {date_description}")
            
            return journeys
            
        except ValueError as e:
            # Tag existiert nicht (z.B. 32. März)
            error_msg = f"Ungültiger Tag: {date_description} - {str(e)}"
            self.logger.error(error_msg)
            self.session_stats["errors"].append(error_msg)
            return []
        except Exception as e:
            error_msg = f"Fehler bei Tag {target_day}: {str(e)}"
            self.logger.error(error_msg)
            self.session_stats["errors"].append(error_msg)
            return []
    
    def run_daily_check(self) -> bool:
        """Führe häufige Überprüfung durch (alle 3 Minuten für Zukunfts-Monitoring)"""
        self.logger.debug("🔍 Starte 3-Minuten-Check für zukünftige Verbindungen")
        
        try:
            # Teste Telegram-Verbindung (nur bei Fehlern loggen)
            if not self.telegram.test_connection():
                self.logger.error("Telegram-Verbindung fehlgeschlagen")
                return False
            
            # Prüfe konfigurierten Zieltag
            connections = self.check_target_day_connections(self.config.target_day)
            
            if len(connections) > 0:
                self.logger.info(f"🎉 {len(connections)} Verbindungen gefunden für zukünftiges Datum!")
            else:
                self.logger.debug(f"Keine Verbindungen für {self.config.get_formatted_date_description()} (normal bei Zukunfts-Monitoring)")
                # Sende nur alle 60 Minuten eine "Keine Verbindungen" Nachricht (um Spam zu vermeiden)
                current_time = datetime.now()
                minutes_since_start = (current_time - self.session_stats["start_time"]).total_seconds() / 60
                
                # Sende Nachricht nur beim ersten Check oder alle 60 Minuten (alle 20. Check bei 3-Min-Intervall)
                if minutes_since_start < 1 or (minutes_since_start % 60) < 3:  
                    self.telegram.notify_no_connections_found(
                        target_day=self.config.target_day,
                        checked_dates=self.session_stats["dates_checked"],
                        date_description=self.config.get_formatted_date_description()
                    )
                else:
                    self.logger.debug("Überspringe Telegram-Nachricht (Spam-Schutz) - keine Verbindungen")
            
            # Fehler-Report falls Fehler aufgetreten
            if self.session_stats["errors"]:
                error_summary = f"{len(self.session_stats['errors'])} Fehler aufgetreten"
                first_error = self.session_stats["errors"][0] if self.session_stats["errors"] else ""
                self.telegram.notify_error(error_summary, first_error)
            
            return True
            
        except Exception as e:
            error_msg = f"Kritischer Fehler bei täglicher Überprüfung: {str(e)}"
            self.logger.error(error_msg)
            self.telegram.notify_error(error_msg, "run_daily_check")
            return False
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Hole Session-Zusammenfassung"""
        runtime = datetime.now() - self.session_stats["start_time"]
        return {
            "runtime_seconds": int(runtime.total_seconds()),
            "runtime_formatted": str(runtime).split('.')[0],  # HH:MM:SS
            **self.session_stats
        }
    
    def run_test_mode(self) -> bool:
        """Führe Test-Modus durch (verwendet konfigurierten Zieltag)"""
        self.logger.info("🧪 Starte Test-Modus")
        
        try:
            # Teste konfigurierten Zieltag
            test_connections = self.check_target_day_connections(
                self.config.target_day,
                start_hour=10
            )
            
            # Test-Zusammenfassung
            summary = self.get_session_summary()
            self.logger.info(f"Test abgeschlossen: {len(test_connections)} Verbindungen gefunden, {summary['total_api_calls']} API calls")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler im Test-Modus: {str(e)}")
            return False