#!/bin/bash
# Docker Entrypoint für Bahnabfrage
set -e

echo "🚀 Starte Deutsche Bahn Verbindungsüberwachung Container"
echo "=============================================="

# Als Root laufend - alle Setup-Tasks als bahnmonitor User ausführen
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

# Deutsche Bahn API für März 2025 testen (ohne Benachrichtigungen)
echo "🚄 Teste Deutsche Bahn Verbindungssuche für März 2025..."
CONNECTION_TEST_RESULT=$(su bahnmonitor -c "cd /app && PYTHONPATH=/app python -c '
import sys
sys.path.insert(0, \"/app/src\")
from db_client import DBClient, HAMBURG_HBF_ID, LANDECK_ZAMS_ID
from config import load_config

try:
    config = load_config()
    db_client = DBClient(timeout=config.api_timeout_seconds)
    
    # Teste März 2025 Verbindungen (Sample: nur 3 Tage)
    total_connections = 0
    test_dates = [15, 16, 17]  # Test-Sample
    
    from datetime import datetime
    for day in test_dates:
        try:
            test_date = datetime(2025, 3, day, 10, 0)
            journeys = db_client.search_journeys(
                HAMBURG_HBF_ID, 
                LANDECK_ZAMS_ID, 
                test_date, 
                max_results=10
            )
            total_connections += len(journeys)
        except:
            pass
    
    print(f\"SUCCESS:{total_connections}\")
except Exception as e:
    print(f\"ERROR:{str(e)}\")
' 2>&1")

# Parse Ergebnis
if [[ "$CONNECTION_TEST_RESULT" =~ SUCCESS:([0-9]+) ]]; then
    CONNECTION_COUNT="${BASH_REMATCH[1]}"
    echo "✅ Deutsche Bahn API Test erfolgreich: $CONNECTION_COUNT Verbindungen gefunden"
    DB_STATUS="✅ $CONNECTION_COUNT Verbindungen gefunden"
else
    echo "⚠️ Deutsche Bahn API Test mit Problemen (Container startet trotzdem)"
    echo "Details: $CONNECTION_TEST_RESULT"
    DB_STATUS="⚠️ API-Test fehlgeschlagen"
fi

# Startup-Benachrichtigung senden
echo "📢 Sende Startup-Benachrichtigung..."
su bahnmonitor -c "cd /app && PYTHONPATH=/app python -c '
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

message = f\"🐳 **Container gestartet**\\n\\n\" + \
          f\"📅 März 2025: {db_status}\\n\" + \
          f\"🚄 Route: Hamburg Hbf → Landeck-Zams\\n\" + \
          f\"⏰ Nächste Prüfung: {next_check.strftime(time_format)}\\n\\n\" + \
          f\"🤖 Überwachung läuft alle 6 Stunden\"
          
telegram.send_message(message)
'"

# Umgebungsvariable für Python-Script setzen
export DB_STATUS

echo "✅ Container bereit - starte Cron-Daemon..."

# Cron-Daemon im Vordergrund starten
exec "$@"