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

# Startup-Benachrichtigung senden
echo "📢 Sende Startup-Benachrichtigung..."
su bahnmonitor -c "cd /app && DB_STATUS='$DB_STATUS' PYTHONPATH=/app python -c '
import sys
sys.path.insert(0, \"/app/src\")
from telegram_notifier import TelegramNotifier
from config import load_config
import os
from datetime import datetime, timedelta

config = load_config()
telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
next_check = datetime.now() + timedelta(hours=6)
time_format = \"%H:%M\"

# DB-Test Ergebnis aus Umgebung lesen
db_status = os.environ.get(\"DB_STATUS\", \"⚠️ Status unbekannt\")

# Konfigurierte Daten aus .env
year, month = config.get_target_year_month()
target_day = config.target_day
months_german = [
    \"Januar\", \"Februar\", \"März\", \"April\", \"Mai\", \"Juni\",
    \"Juli\", \"August\", \"September\", \"Oktober\", \"November\", \"Dezember\"
]
month_name = months_german[month - 1]

message = f\"🐳 **Container gestartet**\\n\\n\" + \
          f\"{db_status}\\n\" + \
          f\"🚄 Route: {config.departure_station} → {config.destination_station}\\n\" + \
          f\"⏰ Nächste Prüfung: {next_check.strftime(time_format)}\\n\\n\" + \
          
telegram.send_message(message)
'"

# Umgebungsvariable für Python-Script setzen
export DB_STATUS

echo "✅ Container bereit - starte Cron-Daemon..."

# Zeige installierte Cron-Jobs
echo "🕐 Installierte Cron-Jobs:"
crontab -u bahnmonitor -l

# Erstelle Debug-Log-Eintrag
echo "$(date '+%Y-%m-%d %H:%M:%S') - Container gestartet - Cron-Daemon wird gestartet" >> /var/log/bahnabfrage/cron.log

# Cron-Daemon im Vordergrund starten
exec "$@"