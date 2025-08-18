#!/usr/bin/env python3
"""
Konfiguration für Deutsche Bahn Verbindungsüberwachung
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Zentrale Konfigurationsklasse"""
    
    def __init__(self, env_file: Optional[str] = None):
        # Lade .env Datei falls angegeben
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            # Versuche .env im aktuellen Verzeichnis
            load_dotenv()
        
        self._load_config()
    
    def _load_config(self):
        """Lade Konfiguration aus Umgebungsvariablen"""
        
        # Telegram Bot Konfiguration
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Reisedaten
        self.departure_station = os.getenv("DEPARTURE_STATION", "Hamburg Hbf")
        self.destination_station = os.getenv("DESTINATION_STATION", "Landeck-Zams")
        self.target_month = os.getenv("TARGET_MONTH", "2025-03")
        
        # API Konfiguration
        self.api_timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
        self.max_results_per_query = int(os.getenv("MAX_RESULTS_PER_QUERY", "20"))
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
        self.log_file_path = os.getenv("LOG_FILE_PATH", "bahnabfrage.log")
        
        # Timing
        self.check_start_hour = int(os.getenv("CHECK_START_HOUR", "8"))
        self.check_end_hour = int(os.getenv("CHECK_END_HOUR", "20"))
        
        # Test Modus
        self.test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
        self.test_start_day = int(os.getenv("TEST_START_DAY", "15"))
        self.test_end_day = int(os.getenv("TEST_END_DAY", "17"))
    
    def validate(self) -> bool:
        """Validiere Konfiguration"""
        errors = []
        
        # Pflichtfelder prüfen
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN fehlt")
        
        if not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID fehlt")
        
        # Telegram Bot Token Format prüfen
        if self.telegram_bot_token and ":" not in self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN hat ungültiges Format (sollte BOT_ID:TOKEN enthalten)")
        
        # Zeitbereich prüfen
        if not (0 <= self.check_start_hour <= 23):
            errors.append("CHECK_START_HOUR muss zwischen 0 und 23 liegen")
        
        if not (0 <= self.check_end_hour <= 23):
            errors.append("CHECK_END_HOUR muss zwischen 0 und 23 liegen")
        
        # Test-Modus Validierung
        if self.test_mode:
            if not (1 <= self.test_start_day <= 31):
                errors.append("TEST_START_DAY muss zwischen 1 und 31 liegen")
            
            if not (1 <= self.test_end_day <= 31):
                errors.append("TEST_END_DAY muss zwischen 1 und 31 liegen")
            
            if self.test_start_day > self.test_end_day:
                errors.append("TEST_START_DAY darf nicht größer als TEST_END_DAY sein")
        
        if errors:
            for error in errors:
                print(f"Konfigurationsfehler: {error}")
            return False
        
        return True
    
    def setup_logging(self):
        """Konfiguriere Logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Basis-Konfiguration
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # File-Logging falls gewünscht
        if self.log_to_file:
            file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            file_handler.setLevel(getattr(logging, self.log_level))
            file_handler.setFormatter(logging.Formatter(log_format))
            
            # Füge File Handler zu Root Logger hinzu
            logging.getLogger().addHandler(file_handler)
    
    def get_target_year_month(self) -> tuple[int, int]:
        """Parse Target Month (Format: YYYY-MM)"""
        try:
            year_str, month_str = self.target_month.split("-")
            return int(year_str), int(month_str)
        except (ValueError, AttributeError):
            # Fallback zu März 2025
            return 2025, 3
    
    def print_config_summary(self):
        """Drucke Konfigurations-Zusammenfassung"""
        print("🔧 Konfiguration geladen:")
        print(f"   Route: {self.departure_station} → {self.destination_station}")
        print(f"   Zeitraum: {self.target_month}")
        print(f"   Test-Modus: {'✅ Aktiviert' if self.test_mode else '❌ Deaktiviert'}")
        
        if self.test_mode:
            print(f"   Test-Tage: {self.test_start_day}-{self.test_end_day}")
        
        print(f"   Telegram Bot: {'✅ Konfiguriert' if self.telegram_bot_token else '❌ Fehlt'}")
        print(f"   Log Level: {self.log_level}")
        
        if self.log_to_file:
            print(f"   Log File: {self.log_file_path}")


def load_config(env_file: Optional[str] = None) -> Config:
    """Lade und validiere Konfiguration"""
    config = Config(env_file)
    
    if not config.validate():
        raise ValueError("Konfiguration ungültig - siehe Fehler oben")
    
    return config


# Beispiel .env Datei erstellen falls nicht vorhanden
def create_example_env():
    """Erstelle .env.example falls sie nicht existiert"""
    example_content = """# Deutsche Bahn Verbindungsüberwachung Konfiguration

# Telegram Bot (PFLICHT)
TELEGRAM_BOT_TOKEN=8286320781:AAFezNqBWPS-yUznAp_gWEo-Y58RIPOGCq8
TELEGRAM_CHAT_ID=your_chat_id_here

# Reisedaten
DEPARTURE_STATION=Hamburg Hbf
DESTINATION_STATION=Landeck-Zams
TARGET_MONTH=2025-03

# API Einstellungen
API_TIMEOUT_SECONDS=30
MAX_RESULTS_PER_QUERY=20

# Zeitsteuerung
CHECK_START_HOUR=8
CHECK_END_HOUR=20

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=false
LOG_FILE_PATH=bahnabfrage.log

# Test-Modus (für Entwicklung)
TEST_MODE=false
TEST_START_DAY=15
TEST_END_DAY=17
"""
    
    if not os.path.exists(".env"):
        with open(".env", "w", encoding="utf-8") as f:
            f.write(example_content)
        print("✅ .env Datei erstellt - bitte TELEGRAM_CHAT_ID konfigurieren!")


if __name__ == "__main__":
    # Test der Konfiguration
    create_example_env()
    
    try:
        config = load_config()
        config.setup_logging()
        config.print_config_summary()
        print("✅ Konfiguration erfolgreich geladen und validiert")
    except Exception as e:
        print(f"❌ Konfigurationsfehler: {str(e)}")