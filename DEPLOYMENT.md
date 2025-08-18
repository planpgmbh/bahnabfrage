# 🚀 Produktions-Deployment Guide

## Schnelle Installation

### 1. Server Vorbereitung
```bash
# Projekt auf Server kopieren
scp -r bahnabfrage/ user@your-server:/tmp/

# SSH auf Server
ssh user@your-server
```

### 2. Automatische Installation
```bash
cd /tmp/bahnabfrage
sudo ./scripts/setup.sh
```

**Das Setup-Script installiert automatisch:**
- ✅ Python3 & Dependencies  
- ✅ Dedicated User `bahnmonitor`
- ✅ Virtual Environment in `/opt/bahnabfrage/`
- ✅ Produktions-Konfiguration (Chat ID bereits gesetzt)
- ✅ Systemd Timer (alle 6 Stunden)
- ✅ Log-Verzeichnis `/var/log/bahnabfrage/`

### 3. Service starten
```bash
# Timer aktivieren
sudo systemctl start bahnabfrage.timer
sudo systemctl enable bahnabfrage.timer

# Status prüfen
sudo systemctl status bahnabfrage.timer
```

### 4. Test ausführen
```bash
sudo -u bahnmonitor /opt/bahnabfrage/venv/bin/python /opt/bahnabfrage/src/main.py --test
```

## 📊 Produktions-Optimierungen

### Rate Limits & Timing
- **API Calls**: 31 Tage × 4 = 124 Requests/Tag
- **Rate Limit**: 75/100 Requests/Minute (25% Sicherheitsmarge)
- **Frequenz**: Alle 6 Stunden (6:00, 12:00, 18:00, 00:00)
- **Randomized Delay**: ±5 Minuten zur Lastverteilung

### Error Handling  
- **Telegram Retry**: 3 Versuche mit 5s Pause
- **API Timeout**: 30 Sekunden
- **Logging**: Strukturierte Logs in `/var/log/bahnabfrage/`

### Konfiguration
```bash
# Produktions-.env automatisch installiert
TELEGRAM_BOT_TOKEN=8286320781:AAFezNqBWPS-yUznAp_gWEo-Y58RIPOGCq8
TELEGRAM_CHAT_ID=7144646940
LOG_TO_FILE=true
LOG_LEVEL=INFO
```

## 🔍 Monitoring & Wartung

### Logs überwachen
```bash
# Live Logs
sudo journalctl -u bahnabfrage -f

# Letzte 50 Einträge
sudo journalctl -u bahnabfrage -n 50

# Timer Status
sudo systemctl status bahnabfrage.timer
sudo systemctl list-timers bahnabfrage
```

### Service Management
```bash
# Timer stoppen/starten
sudo systemctl stop bahnabfrage.timer
sudo systemctl start bahnabfrage.timer

# Manuelle Ausführung
sudo systemctl start bahnabfrage.service

# Service deaktivieren
sudo systemctl disable bahnabfrage.timer
```

### Wartung
```bash
# Log-Rotation (optional)
sudo logrotate -f /etc/logrotate.d/bahnabfrage

# Konfiguration ändern
sudo nano /opt/bahnabfrage/.env
sudo systemctl daemon-reload
```

## 🚨 Troubleshooting

### Häufige Probleme

**Service startet nicht:**
```bash
sudo journalctl -u bahnabfrage -n 20
sudo systemctl daemon-reload
```

**Telegram-Nachrichten kommen nicht an:**
```bash
sudo -u bahnmonitor /opt/bahnabfrage/venv/bin/python /opt/bahnabfrage/src/main.py --test-telegram
```

**API-Fehler:**
```bash
curl "https://v6.db.transport.rest/locations?query=Hamburg"
```

**Berechtigungsfehler:**
```bash
sudo chown -R bahnmonitor:bahnmonitor /opt/bahnabfrage/
sudo chmod +x /opt/bahnabfrage/src/main.py
```

## 📈 Erwartete Performance

### Erste Ausführung
- **Dauer**: ~2-3 Minuten
- **API Calls**: 31 (ein Call pro Tag im März)
- **Telegram-Nachrichten**: 31 (alle Verbindungen sind "neu")

### Folge-Ausführungen  
- **Dauer**: ~2-3 Minuten
- **API Calls**: 31
- **Telegram-Nachrichten**: 0-5 (nur neue Verbindungen)

### Monatliche Statistik
- **API Calls**: ~3.720 (31 × 4 × 30 Tage)
- **Uptime**: 99%+ erwartet
- **False Positives**: Minimal (Session-basierte Duplikatserkennung)

## ✅ Go-Live Checklist

- [ ] Setup-Script ausgeführt
- [ ] Timer gestartet: `sudo systemctl start bahnabfrage.timer`  
- [ ] Test erfolgreich: `--test` Modus ausgeführt
- [ ] Telegram-Nachrichten empfangen
- [ ] Logs funktionieren: `sudo journalctl -u bahnabfrage -f`
- [ ] Timer läuft: `sudo systemctl list-timers bahnabfrage`

**Die Anwendung ist produktionsbereit und optimiert für 24/7 Betrieb!**