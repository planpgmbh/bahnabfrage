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
telegram.send_message(f\"🐳 **Container gestartet**\n\nBahnverbindungsüberwachung läuft jetzt in Docker!\n\n⏰ Nächste Prüfung: {next_check.strftime(\\\"%H:%M\\\")}\")
'"

echo "✅ Container bereit - starte Cron-Daemon..."

# Cron-Daemon im Vordergrund starten
exec "$@"