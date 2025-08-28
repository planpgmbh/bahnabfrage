# Deutsche Bahn Verbindungsüberwachung

**Production-Ready Docker-Container** für automatische Überwachung neuer Zugverbindungen

## 🎯 Funktionen

- **7x tägliche Überwachung** (07:00, 10:00, 13:00, 15:00, 18:00, 21:00, 00:00 Uhr)
- **Selektive Telegram-Benachrichtigungen**: Nur bei gefundenen Verbindungen (kein Spam)
- **Container-Startup-Benachrichtigung**: Mit aktuellem Verbindungsstatus bei jedem Start
- **Community API**: Kostenlose DB API (v6.db.transport.rest) - keine offizielle DB API nötig
- **Session-basiert**: Keine persistente Datenspeicherung
- **Rate-Limit optimiert**: 75% Nutzung für Stabilität (75/100 Requests/Minute)

## 🚀 Quick Start (Docker - Empfohlen)

### 1. Repository clonen
```bash
git clone <repository>
cd bahnabfrage
```

### 2. Konfiguration anpassen
Bearbeite die `.env` Datei:
```bash
# Telegram Bot Konfiguration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Zieldatum anpassen  
TARGET_MONTH=2025-02  # Format: YYYY-MM
TARGET_DAY=27         # Gewünschter Tag (1-31)
```

### 3. Container starten
```bash
docker compose up -d
```

### 4. Logs überprüfen
```bash
# Container-Logs anzeigen
docker compose logs -f

# Cron-Logs überwachen
docker compose exec bahnabfrage tail -f /var/log/bahnabfrage/cron.log
```

## 📋 Docker Kommandos

### Container-Management
```bash
# Container starten
docker compose up -d

# Container stoppen
docker compose down

# Container neu bauen
docker compose build --no-cache

# Status prüfen
docker compose ps
```

### Logs und Debugging
```bash
# Cron-Jobs anzeigen
docker compose exec bahnabfrage crontab -u bahnmonitor -l

# Manueller Test
docker compose exec bahnabfrage su bahnmonitor -c "cd /app && python src/main.py --test"

# Cron-Status prüfen
docker compose exec bahnabfrage ps aux | grep cron
```

## 🔧 Erweiterte Konfiguration

### Native Python Kommandos (optional)
```bash
# Test-Modus (wenn nicht Docker)
python src/main.py --test

# Telegram-Verbindung testen
python src/main.py --test-telegram

# Production-Lauf
python src/main.py --run

# Mit Debug-Logging
python src/main.py --test --verbose
```

## ⚙️ Konfigurationsdatei (.env)

**Vollständige .env Beispiel-Konfiguration:**
```bash
# Telegram Bot (PFLICHT)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Reisedaten
DEPARTURE_STATION=Hamburg Hbf
DESTINATION_STATION=Landeck-Zams
TARGET_MONTH=2025-02  # Format: YYYY-MM
TARGET_DAY=27         # Zieltag (1-31)

# API Einstellungen  
API_TIMEOUT_SECONDS=30
MAX_RESULTS_PER_QUERY=20

# Zeitsteuerung
CHECK_START_HOUR=8
CHECK_END_HOUR=20

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=false

# Test-Modus (optional)  
TEST_MODE=false
```

## 📅 Production-Schedule

Das System führt **7x täglich** automatische Checks durch:
- **07:00 Uhr**: Morgen-Check
- **10:00 Uhr**: Vormittags-Check  
- **13:00 Uhr**: Mittags-Check
- **15:00 Uhr**: Nachmittags-Check
- **18:00 Uhr**: Abends-Check
- **21:00 Uhr**: Nacht-Check
- **00:00 Uhr**: Mitternachts-Check

**Telegram-Benachrichtigungen erfolgen nur bei gefundenen Verbindungen** - kein Spam bei "keine Verbindungen".

## 🏗️ Projektstruktur

```
bahnabfrage/
├── src/
│   ├── main.py                 # Hauptanwendung
│   ├── config.py              # Konfigurationsverwaltung
│   ├── db_client.py           # Deutsche Bahn API Client
│   ├── telegram_notifier.py   # Telegram-Integration
│   └── connection_monitor.py  # Überwachungslogik
├── scripts/
│   └── setup.sh               # Automatisches Setup
├── config/
│   ├── .env.example          # Konfigurationsvorlage
│   └── crontab.example       # Cron-Konfiguration
├── requirements.txt
└── README.md
```

## 🔍 Monitoring

### Logs anzeigen
```bash
# Systemd Logs
sudo journalctl -u bahnabfrage -f

# Timer Status
sudo systemctl status bahnabfrage.timer

# Cron Logs (falls Cron verwendet)
tail -f /var/log/bahnabfrage/cron.log
```

### Service-Management
```bash
# Timer starten/stoppen
sudo systemctl start bahnabfrage.timer
sudo systemctl stop bahnabfrage.timer

# Service manuell ausführen
sudo systemctl start bahnabfrage.service

# Timer deaktivieren
sudo systemctl disable bahnabfrage.timer
```

## 🧪 Testing

### API-Exploration (bereits durchgeführt)
```bash
python src/api_test_working.py
```

### Komponenten-Tests
```bash
# Konfiguration testen
python src/config.py

# Telegram testen
python src/main.py --test-telegram

# DB API testen
python src/main.py --test
```

## ⚡ API Details

### Community API (v6.db.transport.rest)
- **Base URL**: `https://v6.db.transport.rest`
- **Rate Limit**: 100 Requests/Minute
- **Authentifizierung**: Keine erforderlich
- **Station IDs**: Hamburg Hbf (`8002549`), Landeck-Zams (`8100063`)

### Endpunkte
```bash
# Station suchen
GET /locations?query=Hamburg Hbf

# Verbindungen suchen
GET /journeys?from=8002549&to=8100063&departure=2025-03-15T10:00:00+01:00
```

## 🔧 Troubleshooting

### Häufige Probleme

**1. Telegram-Nachrichten kommen nicht an**
```bash
# Chat ID prüfen
python src/main.py --test-telegram
```

**2. API-Fehler**
```bash
# API-Verbindung testen
curl "https://v6.db.transport.rest/locations?query=Hamburg"
```

**3. Service startet nicht**
```bash
# Logs prüfen
sudo journalctl -u bahnabfrage -n 50
```

**4. Berechtigungsfehler**
```bash
# Berechtigungen korrigieren
sudo chown -R bahnmonitor:bahnmonitor /opt/bahnabfrage
sudo chmod +x /opt/bahnabfrage/src/main.py
```

### Debug-Modus
```bash
# Mit Debug-Logging
python src/main.py --test --verbose

# Direkte API-Tests
python src/api_test_working.py
```

## 📊 Machbarkeitsbericht

Das Projekt wurde erfolgreich validiert:

✅ **Community API funktioniert vollständig**  
✅ **Station-IDs ermittelt und getestet**  
✅ **Grenzüberschreitende Verbindungen verfügbar**  
✅ **Rate Limits eingehalten**  
✅ **März 2025 Abfragen möglich**  

Siehe `MACHBARKEITSBERICHT.md` für Details.

## 📝 Lizenz

Dieses Projekt dient der privaten Nutzung zur Überwachung von Bahnverbindungen.