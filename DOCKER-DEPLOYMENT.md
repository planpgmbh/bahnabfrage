# 🐳 Docker Deployment Guide

## 🚀 Schnelle Installation auf Ihrem Server

### 1. Projekt auf Server übertragen
```bash
# Lokaler Computer → Server
scp -r bahnabfrage/ user@your-server:/opt/

# SSH auf Server
ssh user@your-server
cd /opt/bahnabfrage
```

### 2. Logs-Verzeichnis erstellen
```bash
mkdir -p logs
chmod 755 logs
```

### 3. Container bauen und starten
```bash
# Container bauen
docker-compose build

# Container starten
docker-compose up -d

# Logs verfolgen
docker-compose logs -f
```

**Das war's!** Der Container läuft jetzt und überwacht 4x täglich.

## 📊 Container-Features

### ✅ Was der Container macht:
- **Startup-Test**: Prüft Konfiguration und Telegram-Verbindung
- **Startup-Nachricht**: Sendet Telegram-Bestätigung beim Start
- **Cron-Jobs**: Läuft automatisch alle 6 Stunden
- **Health-Checks**: Docker überwacht Container-Gesundheit
- **Persistente Logs**: In `./logs/` Verzeichnis

### 🕒 Zeitplan:
```
06:00 Uhr → Verbindungscheck
12:00 Uhr → Verbindungscheck  
18:00 Uhr → Verbindungscheck
00:00 Uhr → Verbindungscheck
```

## 🔍 Monitoring & Verwaltung

### Container-Status
```bash
# Status prüfen
docker-compose ps

# Health-Check Status
docker inspect bahnabfrage | grep Health -A 10

# Logs anzeigen
docker-compose logs -f
docker-compose logs --tail 50
```

### Container-Verwaltung
```bash
# Container stoppen
docker-compose down

# Container neu starten
docker-compose restart

# Container neu bauen (nach Änderungen)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Logs-Zugriff
```bash
# Container-Logs (Docker)
docker-compose logs -f

# Anwendungs-Logs (im Container)
docker-compose exec bahnabfrage cat /var/log/bahnabfrage/cron.log

# Lokale Log-Dateien
tail -f logs/cron.log
```

## 🔧 Traefik-Integration (Optional)

Falls Sie ein Web-Interface wollen (für Status-Seite):

```yaml
# In docker-compose.yml ändern:
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.bahnabfrage.rule=Host(`bahn.yourdomain.com`)"
  - "traefik.http.routers.bahnabfrage.tls.certresolver=letsencrypt"
  - "traefik.http.services.bahnabfrage.loadbalancer.server.port=8080"

networks:
  - traefik  # Ihr Traefik-Netzwerk
```

**Hinweis**: Aktuell ist Traefik deaktiviert (`traefik.enable=false`), da kein Web-Interface benötigt wird.

## 🧪 Testing

### Manuelle Tests
```bash
# Telegram-Test
docker-compose exec bahnabfrage python src/main.py --test-telegram

# Verbindungstest (3 Tage)
docker-compose exec bahnabfrage python src/main.py --test

# Konfiguration prüfen
docker-compose exec bahnabfrage python src/config.py
```

### Container in Shell öffnen
```bash
# Interactive Shell im Container
docker-compose exec bahnabfrage bash

# Als bahnmonitor User
docker-compose exec -u bahnmonitor bahnabfrage bash
```

## 🚨 Troubleshooting

### Häufige Probleme

**Container startet nicht:**
```bash
docker-compose logs bahnabfrage
docker-compose build --no-cache
```

**Telegram-Nachrichten kommen nicht an:**
```bash
docker-compose exec bahnabfrage python src/main.py --test-telegram
```

**Cron läuft nicht:**
```bash
# Cron-Status im Container prüfen
docker-compose exec bahnabfrage ps aux | grep cron
docker-compose exec bahnabfrage cat /var/log/bahnabfrage/cron.log
```

**Timezone-Probleme:**
```bash
# Timezone im Container prüfen
docker-compose exec bahnabfrage date
docker-compose exec bahnabfrage cat /etc/timezone
```

### Health-Check Fehler
```bash
# Health-Check manuell ausführen
docker-compose exec bahnabfrage python src/main.py --test-telegram

# Health-Check Status
docker inspect bahnabfrage | grep -A 5 -B 5 Health
```

## 📈 Performance & Ressourcen

### Erwartete Ressourcen:
- **RAM**: ~50MB
- **CPU**: Minimal (nur bei Ausführung aktiv)
- **Disk**: ~100MB für Container + Logs
- **Network**: ~1MB pro Tag

### Auto-Restart
Der Container startet automatisch bei Server-Reboot (`restart: unless-stopped`).

## 🔄 Updates

### Code-Updates:
```bash
cd /opt/bahnabfrage

# Änderungen pullen (falls Git-Repo)
git pull

# Container neu bauen und starten
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Dependency-Updates:
```bash
# requirements.txt ändern, dann:
docker-compose build --no-cache
docker-compose up -d
```

## ✅ Deployment-Checklist

- [ ] Projekt auf Server kopiert: `/opt/bahnabfrage/`
- [ ] Logs-Verzeichnis erstellt: `mkdir -p logs`
- [ ] Container gebaut: `docker-compose build`
- [ ] Container gestartet: `docker-compose up -d`
- [ ] Startup-Nachricht erhalten (Telegram)
- [ ] Health-Check OK: `docker-compose ps`
- [ ] Logs funktionieren: `docker-compose logs -f`

**Ihr Docker-Container läuft jetzt 24/7 und überwacht automatisch Hamburg → Landeck-Zams Verbindungen!**