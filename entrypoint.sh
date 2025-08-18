#!/bin/bash
# Docker Entrypoint für Bahnabfrage
set -e

echo "🚀 Starte Deutsche Bahn Verbindungsüberwachung Container"
echo "=============================================="

# Konfiguration prüfen
echo "🔧 Prüfe Konfiguration..."
python src/config.py

# Telegram-Verbindung testen
echo "📱 Teste Telegram-Verbindung..."
python src/main.py --test-telegram

# Startup-Benachrichtigung senden
echo "📢 Sende Startup-Benachrichtigung..."
python -c "
from src.telegram_notifier import TelegramNotifier
from src.config import load_config
import os

config = load_config()
telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
telegram.send_message('🐳 **Container gestartet**\n\nBahnverbindungsüberwachung läuft jetzt in Docker!\n\n⏰ Nächste Prüfung: $(date -d \"+6 hours\" +\"%H:%M\")')
"

echo "✅ Container bereit - starte Cron-Daemon..."

# Cron-Daemon im Vordergrund starten
exec "$@"