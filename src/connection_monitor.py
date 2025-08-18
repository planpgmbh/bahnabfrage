#!/usr/bin/env python3
"""
Connection Monitor
Überwacht neue Zugverbindungen Hamburg → Landeck-Zams für März 2025
"""

import logging
from datetime import datetime, timedelta
from typing import Set, List, Dict, Any
from dataclasses import dataclass
import hashlib
import json

from db_client import DBClient, Journey, HAMBURG_HBF_ID, LANDECK_ZAMS_ID
from telegram_notifier import TelegramNotifier

@dataclass
class ConnectionSignature:
    """Eindeutige Signatur einer Verbindung für Duplikatserkennung"""
    date: str
    departure_time: str
    arrival_time: str
    transfers: int
    duration_minutes: int
    
    def to_hash(self) -> str:
        """Erstelle Hash für diese Verbindung"""
        content = f"{self.date}-{self.departure_time}-{self.arrival_time}-{self.transfers}-{self.duration_minutes}"
        return hashlib.md5(content.encode()).hexdigest()

class ConnectionMonitor:
    """Hauptlogik für die Verbindungsüberwachung"""
    
    def __init__(self, db_client: DBClient, telegram_notifier: TelegramNotifier):
        self.db_client = db_client
        self.telegram = telegram_notifier
        self.logger = logging.getLogger(__name__)
        
        # Session-basierte Duplikatsvermeidung (kein persistenter Speicher)
        self.known_connections: Set[str] = set()
        
        # Statistiken für diese Session
        self.session_stats = {
            "start_time": datetime.now(),
            "total_api_calls": 0,
            "dates_checked": 0,
            "connections_found": 0,
            "new_connections_found": 0,
            "errors": []
        }
    
    def create_connection_signature(self, journey: Journey, date: str) -> ConnectionSignature:
        """Erstelle eindeutige Signatur für eine Verbindung"""
        return ConnectionSignature(
            date=date,
            departure_time=journey.departure_time.strftime("%H:%M"),
            arrival_time=journey.arrival_time.strftime("%H:%M"),
            transfers=journey.transfers,
            duration_minutes=journey.duration_minutes
        )
    
    def is_connection_known(self, signature: ConnectionSignature) -> bool:
        """Prüfe ob Verbindung bereits bekannt ist (in dieser Session)"""
        hash_value = signature.to_hash()
        return hash_value in self.known_connections
    
    def add_known_connection(self, signature: ConnectionSignature):
        """Füge Verbindung zu bekannten Verbindungen hinzu"""
        hash_value = signature.to_hash()
        self.known_connections.add(hash_value)
    
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
                self.logger.info(f"Keine Verbindungen für {date_str}")
            
            return journeys
            
        except Exception as e:
            error_msg = f"Fehler bei Abfrage für {date_str}: {str(e)}"
            self.logger.error(error_msg)
            self.session_stats["errors"].append(error_msg)
            return []
    
    def filter_new_connections(self, journeys: List[Journey], date_str: str) -> List[Journey]:
        """Filtere neue Verbindungen (noch nicht in dieser Session gesehen)"""
        new_connections = []
        
        for journey in journeys:
            signature = self.create_connection_signature(journey, date_str)
            
            if not self.is_connection_known(signature):
                new_connections.append(journey)
                self.add_known_connection(signature)
                self.logger.debug(f"Neue Verbindung: {signature.departure_time} → {signature.arrival_time}")
            else:
                self.logger.debug(f"Bekannte Verbindung: {signature.departure_time} → {signature.arrival_time}")
        
        return new_connections
    
    def check_march_2025_connections(self, 
                                   start_day: int = 1, 
                                   end_day: int = 31,
                                   start_hour: int = 8) -> Dict[str, List[Journey]]:
        """Prüfe Verbindungen für März 2025"""
        self.logger.info(f"Starte Überwachung März 2025 (Tag {start_day}-{end_day})")
        
        new_connections_by_date = {}
        total_new_connections = 0
        
        for day in range(start_day, end_day + 1):
            try:
                # Prüfe ob Tag im März 2025 existiert
                target_date = datetime(2025, 3, day, start_hour, 0)
                
                # Prüfe Verbindungen für diesen Tag
                journeys = self.check_single_date(target_date)
                
                if journeys:
                    date_str = target_date.strftime("%Y-%m-%d")
                    new_journeys = self.filter_new_connections(journeys, date_str)
                    
                    if new_journeys:
                        new_connections_by_date[date_str] = new_journeys
                        total_new_connections += len(new_journeys)
                        
                        self.logger.info(f"✨ {len(new_journeys)} neue Verbindungen für {date_str}")
                        
                        # Sofort Telegram-Benachrichtigung senden
                        self.telegram.notify_new_connections(
                            new_journeys, 
                            date_str,
                            "Hamburg Hbf",
                            "Landeck-Zams"
                        )
                    else:
                        self.logger.info(f"Keine neuen Verbindungen für {date_str}")
                
            except ValueError as e:
                # Tag existiert nicht (z.B. 32. März)
                self.logger.warning(f"Ungültiger Tag: {day}. März 2025 - {str(e)}")
                continue
            except Exception as e:
                error_msg = f"Fehler bei Tag {day}: {str(e)}"
                self.logger.error(error_msg)
                self.session_stats["errors"].append(error_msg)
                continue
        
        # Update Session Stats
        self.session_stats["new_connections_found"] = total_new_connections
        
        return new_connections_by_date
    
    def run_daily_check(self) -> bool:
        """Führe tägliche Überprüfung durch (4x täglich ausgeführt)"""
        self.logger.info("🚀 Starte tägliche Verbindungsüberwachung")
        
        try:
            # Teste Telegram-Verbindung
            if not self.telegram.test_connection():
                self.logger.error("Telegram-Verbindung fehlgeschlagen")
                return False
            
            # Prüfe März 2025 Verbindungen
            new_connections = self.check_march_2025_connections()
            
            # Gesamtstatistik
            total_new = sum(len(journeys) for journeys in new_connections.values())
            
            if total_new > 0:
                self.logger.info(f"✨ {total_new} neue Verbindungen gefunden!")
            else:
                self.logger.info("Keine neuen Verbindungen gefunden")
            
            # Status-Update senden (nur wenn keine neuen Verbindungen)
            if total_new == 0:
                self.telegram.notify_status(
                    checked_dates=self.session_stats["dates_checked"],
                    total_connections=self.session_stats["connections_found"],
                    new_connections=0
                )
            
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
        """Führe Test-Modus durch (prüfe nur wenige Tage)"""
        self.logger.info("🧪 Starte Test-Modus")
        
        try:
            # Teste nur 3 Tage im März
            test_connections = self.check_march_2025_connections(
                start_day=15, 
                end_day=17,
                start_hour=10
            )
            
            total_new = sum(len(journeys) for journeys in test_connections.values())
            
            # Test-Zusammenfassung
            summary = self.get_session_summary()
            self.logger.info(f"Test abgeschlossen: {total_new} neue Verbindungen, {summary['total_api_calls']} API calls")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler im Test-Modus: {str(e)}")
            return False