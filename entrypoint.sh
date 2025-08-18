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

# Deutsche Bahn API und Verbindungssuche testen
echo "🚄 Teste Deutsche Bahn Verbindungssuche..."
TEST_RESULT=$(su bahnmonitor -c "cd /app && PYTHONPATH=/app python src/main.py --test 2>&1")
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Deutsche Bahn API Test erfolgreich"
    # Extrahiere Anzahl gefundener Verbindungen aus Test-Output
    CONNECTION_COUNT=$(echo "$TEST_RESULT" | grep -o "neue Verbindungen" | wc -l || echo "0")
    echo "📊 Verbindungen gefunden in Test-Modus"
else
    echo "⚠️ Deutsche Bahn API Test mit Problemen (Container startet trotzdem)"
    echo "Fehler-Details: $TEST_RESULT"
    CONNECTION_COUNT="Fehler"
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

# Test-Ergebnis aus Umgebung lesen
connection_test = os.environ.get(\"CONNECTION_COUNT\", \"Unbekannt\")
api_status = \"✅ DB API funktioniert\" if connection_test != \"Fehler\" else \"⚠️ DB API Probleme\"

message = f\"🐳 **Container gestartet**\\n\\n\" + \
          f\"🚄 Route: Hamburg Hbf → Landeck-Zams\\n\" + \
          f\"📅 Zeitraum: März 2025\\n\" + \
          f\"📊 API-Test: {api_status}\\n\" + \
          f\"⏰ Nächste Prüfung: {next_check.strftime(time_format)}\\n\\n\" + \
          f\"🤖 Überwachung läuft alle 6 Stunden\"
          
telegram.send_message(message)
'"

# Umgebungsvariable für Python-Script setzen
export CONNECTION_COUNT

echo "✅ Container bereit - starte Cron-Daemon..."

# Cron-Daemon im Vordergrund starten
exec "$@"