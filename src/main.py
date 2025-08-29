#!/usr/bin/env python3
"""
Deutsche Bahn Verbindungsüberwachung
Hauptanwendung für automatische Überwachung Hamburg Hbf → Landeck-Zams
"""

import sys
import logging
import argparse
# datetime import nicht mehr benötigt

from config import load_config
from db_client import DBClient
from telegram_notifier import TelegramNotifier
from connection_monitor import ConnectionMonitor

def setup_argument_parser():
    """Setup Command Line Arguments"""
    parser = argparse.ArgumentParser(
        description="Deutsche Bahn Verbindungsüberwachung Hamburg → Landeck-Zams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python main.py --run                 # Normale Ausführung (Production)
  python main.py --test                # Test-Modus (wenige Tage)
  python main.py --test-telegram       # Nur Telegram-Verbindung testen
  python main.py --config config/.env  # Mit spezifischer .env Datei
        """
    )
    
    parser.add_argument(
        "--run", 
        action="store_true",
        help="Führe normale Verbindungsüberwachung durch"
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Test-Modus: Prüfe nur wenige Tage (schnell)"
    )
    
    parser.add_argument(
        "--test-telegram", 
        action="store_true",
        help="Teste nur Telegram-Verbindung"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="Pfad zur .env Konfigurationsdatei"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose Logging (DEBUG Level)"
    )
    
    return parser

def test_telegram_connection(config) -> bool:
    """Teste Telegram Bot Verbindung"""
    print("🧪 Teste Telegram-Verbindung...")
    
    try:
        telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
        
        # Teste Bot-Verbindung
        if not telegram.test_connection():
            print("❌ Telegram Bot-Verbindung fehlgeschlagen")
            return False
        
        print("✅ Telegram Bot-Verbindung erfolgreich")
        
        # Sende Test-Nachricht
        if telegram.send_test_message():
            print("✅ Test-Nachricht erfolgreich gesendet")
            return True
        else:
            print("❌ Test-Nachricht konnte nicht gesendet werden")
            return False
            
    except Exception as e:
        print(f"❌ Telegram Test Exception: {str(e)}")
        return False

def run_application(config, test_mode: bool = False) -> bool:
    """Führe Hauptanwendung aus"""
    logger = logging.getLogger(__name__)
    
    try:
        # Komponenten initialisieren
        db_client = DBClient(timeout=config.api_timeout_seconds)
        telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
        monitor = ConnectionMonitor(db_client, telegram, config)
        
        logger.info("🚀 Starte Deutsche Bahn Verbindungsüberwachung")
        logger.info(f"Route: {config.departure_station} → {config.destination_station}")
        logger.info(f"Zieltag: {config.get_formatted_date_description()}")
        logger.info(f"Modus: {'Test' if test_mode else 'Production'}")
        
        # Überwachung starten (führt Datumsabfrage durch und sendet Ergebnisse)
        if test_mode:
            success = monitor.run_test_mode()
        else:
            success = monitor.run_daily_check()
        
        # Keine automatische Startup-Benachrichtigung mehr - nur bei gefundenen Verbindungen
        
        # Session-Zusammenfassung
        summary = monitor.get_session_summary()
        logger.info(f"Session abgeschlossen: {summary['runtime_formatted']} Laufzeit")
        logger.info(f"Statistik: {summary['dates_checked']} Tage, {summary['total_api_calls']} API calls")
        logger.info(f"Gefunden: {summary['connections_found']} Verbindungen")
        
        if summary['errors']:
            logger.warning(f"Fehler aufgetreten: {len(summary['errors'])}")
        
        return success
        
    except Exception as e:
        logger.error(f"Kritischer Fehler in Hauptanwendung: {str(e)}")
        
        # Versuche Fehler-Benachrichtigung zu senden
        try:
            telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
            telegram.notify_error(f"Kritischer Anwendungsfehler: {str(e)}", "main.py")
        except:
            pass  # Ignoriere Telegram-Fehler bei kritischen Fehlern
        
        return False

def main():
    """Hauptfunktion"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Mindestens ein Modus muss gewählt werden
    if not any([args.run, args.test, args.test_telegram]):
        parser.print_help()
        print("\n❌ Bitte wähle einen Modus: --run, --test oder --test-telegram")
        sys.exit(1)
    
    try:
        # Konfiguration laden
        config = load_config(args.config)
        
        # Logging konfigurieren
        if args.verbose:
            config.log_level = "DEBUG"
        
        config.setup_logging()
        logger = logging.getLogger(__name__)
        
        # Konfiguration anzeigen
        config.print_config_summary()
        
        # Test-Modus in Config setzen falls --test
        if args.test:
            config.test_mode = True
        
        # Modus ausführen
        if args.test_telegram:
            success = test_telegram_connection(config)
            
        elif args.test:
            logger.info("Starte Test-Modus")
            success = run_application(config, test_mode=True)
            
        elif args.run:
            logger.info("Starte Production-Modus")
            success = run_application(config, test_mode=False)
        
        # Exit Code setzen
        if success:
            print("✅ Anwendung erfolgreich beendet")
            sys.exit(0)
        else:
            print("❌ Anwendung mit Fehlern beendet")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Anwendung durch Benutzer unterbrochen")
        sys.exit(130)
    
    except Exception as e:
        print(f"❌ Kritischer Fehler: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()