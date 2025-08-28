#!/bin/bash
# Docker Entrypoint für Bahnabfrage
set -e

echo "🚀 Starte Deutsche Bahn Verbindungsüberwachung Container"
echo "=============================================="

# Container läuft als Root - Setup für bahnmonitor User
# Stelle sicher, dass bahnmonitor User Zugriff auf cron hat
chown bahnmonitor:bahnmonitor /var/log/bahnabfrage

# Installiere Crontab für bahnmonitor User
crontab -u bahnmonitor /etc/cron.d/bahnabfrage
echo "✅ Crontab für bahnmonitor User installiert"

# Konfiguration prüfen
echo "🔧 Prüfe Konfiguration..."
su bahnmonitor -c "cd /app && python src/config.py"

# Telegram-Verbindung testen (nur Konnektivität, keine Nachrichten)
echo "📱 Teste Telegram-Verbindung..."
su bahnmonitor -c "cd /app && PYTHONPATH=/app python -c '
import sys
sys.path.insert(0, \"/app/src\")
from telegram_notifier import TelegramNotifier
from config import load_config

config = load_config()
telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
if telegram.test_connection():
    print(\"✅ Telegram Bot erfolgreich verbunden\")
else:
    print(\"❌ Telegram Bot Verbindung fehlgeschlagen\")
    exit(1)
'"

# Deutsche Bahn API testen (ohne Benachrichtigungen)
echo "🚄 Teste Deutsche Bahn Verbindungssuche..."
CONNECTION_TEST_RESULT=$(su bahnmonitor -c "cd /app && PYTHONPATH=/app python -c '
import sys
sys.path.insert(0, \"/app/src\")
from db_client import DBClient, HAMBURG_HBF_ID, LANDECK_ZAMS_ID
from config import load_config

try:
    config = load_config()
    db_client = DBClient(timeout=config.api_timeout_seconds)
    
    # Teste konfigurierten Tag aus .env
    year, month = config.get_target_year_month()
    target_day = config.target_day
    
    from datetime import datetime
    test_date = datetime(year, month, target_day, 10, 0)
    journeys = db_client.search_journeys(
        HAMBURG_HBF_ID, 
        LANDECK_ZAMS_ID, 
        test_date, 
        max_results=10
    )
    
    total_connections = len(journeys)
    print(f\"SUCCESS:{total_connections}:{target_day}:{month}:{year}\")
except Exception as e:
    print(f\"ERROR:{str(e)}\")
' 2>&1")

# Parse Ergebnis
if [[ "$CONNECTION_TEST_RESULT" =~ SUCCESS:([0-9]+):([0-9]+):([0-9]+):([0-9]+) ]]; then
    CONNECTION_COUNT="${BASH_REMATCH[1]}"
    TARGET_DAY="${BASH_REMATCH[2]}"
    TARGET_MONTH="${BASH_REMATCH[3]}"
    TARGET_YEAR="${BASH_REMATCH[4]}"
    echo "✅ Deutsche Bahn API Test erfolgreich: $CONNECTION_COUNT Verbindungen für ${TARGET_DAY}.${TARGET_MONTH}.${TARGET_YEAR} gefunden"
    if [ "$CONNECTION_COUNT" -gt 0 ]; then
        DB_STATUS="✅ $CONNECTION_COUNT Verbindungen für ${TARGET_DAY}.${TARGET_MONTH}.${TARGET_YEAR}"
    else
        DB_STATUS="⚠️ API erreichbar, aber keine Verbindungen für ${TARGET_DAY}.${TARGET_MONTH}.${TARGET_YEAR}"
    fi
else
    echo "⚠️ Deutsche Bahn API Test mit Problemen (Container startet trotzdem)"
    echo "Details: $CONNECTION_TEST_RESULT"
    DB_STATUS="❌ API-Test fehlgeschlagen"
fi

# Startup-Benachrichtigung mit Verbindungscheck senden
echo "📢 Sende Container-Startup-Benachrichtigung mit Verbindungscheck..."
su bahnmonitor -c "cd /app && source .env 2>/dev/null && PYTHONPATH=/app python -c '
import sys
sys.path.insert(0, \"/app/src\")
from telegram_notifier import TelegramNotifier
from config import load_config
from db_client import DBClient, HAMBURG_HBF_ID, LANDECK_ZAMS_ID
from datetime import datetime

config = load_config()
telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
db_client = DBClient(timeout=config.api_timeout_seconds)

# Echte Verbindungssuche für Startup-Nachricht
try:
    year, month = config.get_target_year_month()
    target_day = config.target_day
    test_date = datetime(year, month, target_day, 10, 0)
    
    journeys = db_client.search_journeys(
        HAMBURG_HBF_ID, 
        LANDECK_ZAMS_ID, 
        test_date, 
        max_results=10
    )
    
    connection_count = len(journeys)
    date_desc = config.get_formatted_date_description()
    
    if connection_count > 0:
        connection_status = f\"✅ {connection_count} Verbindung(en) verfügbar für {date_desc}\"
    else:
        connection_status = f\"❌ Keine Verbindungen für {date_desc} vorhanden\"
        
except Exception as e:
    connection_status = f\"⚠️ Fehler bei Verbindungscheck: {str(e)}\"

# Startup-Nachricht mit aktuellem Verbindungsstatus
message = f\"🐳 **Container gestartet**\\n\\n\" + \
          f\"🚄 Route: {config.departure_station} → {config.destination_station}\\n\" + \
          f\"🎯 Überwacht: {date_desc}\\n\" + \
          f\"{connection_status}\\n\\n\" + \
          f\"⏰ Checks: 07:00, 10:00, 13:00, 15:00, 18:00, 21:00, 00:00\\n\" + \
          f\"💬 Benachrichtigung nur bei gefundenen Verbindungen\"

telegram.send_message(message)
print(f\"✅ Startup-Benachrichtigung gesendet: {connection_count if 'connection_count' in locals() else 0} Verbindungen\")
'"

echo "🎯 Container bereit für 7x tägliche Überwachung"
echo "📅 Zieldatum: 27. Februar 2026"
echo "💬 Telegram-Benachrichtigungen nur bei gefundenen Verbindungen"

# Umgebungsvariable für Python-Script setzen
export DB_STATUS

echo "✅ Container bereit - starte Cron-Daemon (7x täglich)..."

# Zeige installierte Cron-Jobs
echo "🕐 Installierte Cron-Jobs:"
crontab -u bahnmonitor -l

# Erstelle Debug-Log-Eintrag
echo "$(date '+%Y-%m-%d %H:%M:%S') - Container gestartet - Cron-Daemon wird gestartet" >> /var/log/bahnabfrage/cron.log

# Cron-Daemon im Vordergrund starten
exec "$@"