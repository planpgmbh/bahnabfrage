# Deutsche Bahn Verbindungsüberwachung

Automatische Überwachung neuer Zugverbindungen Hamburg Hbf → Landeck-Zams für März 2025 mit Telegram-Benachrichtigungen.

## 🎯 Funktionen

- **4x tägliche Überwachung** (6:00, 12:00, 18:00, 00:00 Uhr - alle 6 Stunden)
- **Community API**: Kostenlose DB API (v6.db.transport.rest) - keine offizielle DB API nötig
- **Telegram-Benachrichtigungen**: Sofortige Meldung neuer Verbindungen mit Retry-Logik
- **Session-basiert**: Keine persistente Datenspeicherung
- **Rate-Limit optimiert**: 75% Nutzung für Stabilität (75/100 Requests/Minute)

## 🚀 Quick Start

### 1. Setup ausführen
```bash
git clone <repository>
cd bahnabfrage
sudo ./scripts/setup.sh
```

### 2. Produktions-Konfiguration (bereits vorbereitet)
Die Konfiguration ist bereits optimiert:
- ✅ Telegram Bot Token konfiguriert
- ✅ Chat ID: 7144646940 (Ihr Chat)
- ✅ Rate Limits optimiert
- ✅ Logging aktiviert

### 3. Test ausführen
```bash
sudo -u bahnmonitor /opt/bahnabfrage/venv/bin/python /opt/bahnabfrage/src/main.py --test
```

### 4. Timer starten
```bash
sudo systemctl start bahnabfrage.timer
sudo systemctl status bahnabfrage.timer
```

## 📋 Kommandos

```bash
# Test-Modus (wenige Tage)
python src/main.py --test

# Telegram-Verbindung testen
python src/main.py --test-telegram

# Production-Lauf
python src/main.py --run

# Mit Debug-Logging
python src/main.py --test --verbose

# Mit spezifischer Config
python src/main.py --test --config config/.env
```

## 🔧 Konfiguration

### Umgebungsvariablen (.env)
```bash
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

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=false
LOG_FILE_PATH=bahnabfrage.log

# Test-Modus
TEST_MODE=false
TEST_START_DAY=15
TEST_END_DAY=17
```

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