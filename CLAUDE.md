# CLAUDE.md

Diese Datei bietet Anleitung für Claude Code (claude.ai/code) beim Arbeiten mit Code in diesem Repository.

## Wichtige Anweisung
**Alle Antworten und Kommunikation sollen auf Deutsch erfolgen.**

## Projektübersicht

Dies ist ein **Deutsche Bahn Zugverbindungs-Monitor**, der automatisch nach Verbindungen zwischen Hamburg Hbf und Landeck-Zams für März 2025 sucht. Die Anwendung:

- Überwacht Verbindungen 4x täglich (6:00, 12:00, 18:00, 00:00) mit systemd timers
- Nutzt die kostenlose Community API (v6.db.transport.rest) - keine offizielle DB API Authentifizierung erforderlich
- Sendet Telegram-Benachrichtigungen für neue Verbindungen mit Retry-Logik
- Arbeitet session-basiert (keine persistente Datenspeicherung)
- Implementiert Rate-Limiting (75/100 requests/minute für Stabilität)

### Wichtige Designentscheidung: Single-Day Approach
Die Anwendung wurde von einem Multi-Day-Ansatz auf einen **Single-Day-Ansatz** umgestellt:
- Überwacht nur einen konfigurierbaren Tag (TARGET_DAY) im März 2025
- Vereinfacht die Logik und reduziert API-Aufrufe erheblich
- Keine Duplikats-Erkennung mehr erforderlich, da nur ein Tag geprüft wird

## Multi-Agent Architecture Integration

### Analysis Agent Specialization
- **API Research Sub-Agent:** DB API Endpoints, Rate Limits, Documentation Analysis
- **System Integration Sub-Agent:** systemd, Linux Service Management, Deployment
- **Monitoring Strategy Sub-Agent:** Logging, Alerting, Health Checks

### Implementation Agent Specialization  
- **Python Backend Sub-Agent:** Async Code, API Clients, Error Handling
- **System Integration Sub-Agent:** systemd Services, Deployment Scripts
- **Quality Assurance Sub-Agent:** Testing, Logging, Performance Monitoring

### Multi-Agent Workflow Commands

#### Analysis Agent Commands
- `/analyze-db-api-issue [description]` - Spezialisierte DB API Bug-Analyse
- `/plan-telegram-feature [feature]` - Telegram Bot Feature Planning
- `/research-systemd-optimization` - systemd Service Optimierung

#### Implementation Agent Commands
- `/implement-python-async-feature [issue_number]` - Python Feature Implementation
- `/optimize-db-api-client` - API Client Performance Optimization  
- `/setup-monitoring-infrastructure` - Production Monitoring Setup

#### Specialized Workflow Commands
- `/deploy-to-systemd [environment]` - Automated systemd Deployment
- `/diagnose-service-issues` - Service Troubleshooting
- `/bahnabfrage-health-dashboard` - Real-time Health Monitoring

### VS Code Multi-Agent Integration
- **Ctrl+Shift+A:** Analysis Agent - DB API Issue Analysis
- **Ctrl+Shift+I:** Implementation Agent - Process Queue
- **Ctrl+Shift+T:** Test Suite Execution
- **Ctrl+Shift+M:** Agent Status Dashboard

## Development Commands

### Setup and Installation
```bash
# Automatic production setup (creates user, systemd service, etc.)
sudo ./scripts/setup.sh

# Manual Python environment setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Testing Commands
```bash
# Test mode (checks only 3 days: 15-17 March)
python src/main.py --test

# Test Telegram connection only
python src/main.py --test-telegram  

# Production run (full March scan)
python src/main.py --run

# Verbose debug logging
python src/main.py --test --verbose

# Use specific config file
python src/main.py --test --config config/.env
```

### Production System Management
```bash
# Start/stop the monitoring timer
sudo systemctl start bahnabfrage.timer
sudo systemctl stop bahnabfrage.timer
sudo systemctl status bahnabfrage.timer

# View logs
sudo journalctl -u bahnabfrage -f
sudo journalctl -u bahnabfrage -n 50

# Manual service execution
sudo systemctl start bahnabfrage.service

# Run as the service user for testing
sudo -u bahnmonitor /opt/bahnabfrage/venv/bin/python /opt/bahnabfrage/src/main.py --test
```

### Configuration Testing
```bash
# Test configuration loading
python src/config.py

# Validate configuration and create example .env if missing
python src/config.py
```

### Docker Development
```bash
# Build Docker image
docker build -t bahnabfrage .

# Run with Docker Compose
docker compose up -d

# View Docker logs
docker compose logs -f

# Stop Docker container
docker compose down

# Rebuild and restart container
docker compose down && docker compose build --no-cache && docker compose up -d

# Execute commands in running container
docker-compose exec bahnabfrage bash

# View cron jobs status
docker-compose exec bahnabfrage crontab -u bahnmonitor -l
```

## Architecture Overview

### Core Components

**main.py** - Entry point with CLI argument parsing and orchestration
- Handles --run, --test, --test-telegram modes
- Sets up logging and loads configuration  
- Coordinates all other components

**config.py** - Configuration management using python-dotenv
- Loads settings from .env files
- Validates required fields (Telegram bot token, chat ID)
- Supports test mode configuration

**db_client.py** - Deutsche Bahn API client
- Uses Community API v6.db.transport.rest (no auth required)
- Implements rate limiting (75/100 requests per minute)
- Station IDs: Hamburg Hbf (8002549), Landeck-Zams (8100063)
- Returns Journey objects with departure/arrival times, duration, transfers

**connection_monitor.py** - Core monitoring logic
- Session-based duplicate detection using connection signatures
- Checks all days in March 2025 (or test range 15-17)
- Filters new connections and triggers notifications
- Tracks statistics (API calls, connections found, errors)

**telegram_notifier.py** - Telegram Bot integration
- Sends formatted connection notifications with journey details
- Implements retry logic (3 attempts with 5s delays)
- Handles startup notifications, error reports, status updates

### Data Flow
1. main.py loads config and initializes components
2. ConnectionMonitor checks each date in March 2025
3. DBClient makes API calls with rate limiting  
4. New connections (not seen in current session) trigger Telegram notifications
5. Session statistics and errors are logged and reported

### Session-Based Operation
- **No persistent storage** - each run starts fresh
- **First run**: All connections are "new" and generate notifications
- **Subsequent runs**: Only genuinely new connections trigger alerts  
- **Restart behavior**: After restart, all connections appear new again

## Key Configuration

### Erforderliche Umgebungsvariablen (.env)
```bash
# Pflichtfelder
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Route-Einstellungen
DEPARTURE_STATION=Hamburg Hbf
DESTINATION_STATION=Landeck-Zams
TARGET_MONTH=2025-03
TARGET_DAY=15  # Konfigurierbarer Zieltag (1-31)

# Zeitsteuerung
CHECK_START_HOUR=8
CHECK_END_HOUR=20

# Optional
API_TIMEOUT_SECONDS=30
MAX_RESULTS_PER_QUERY=20
LOG_LEVEL=INFO
LOG_TO_FILE=false
```

### Production vs Test Mode
- **Production**: Überwacht den konfigurierten TARGET_DAY täglich, sendet Startup-Benachrichtigungen
- **Test**: Verwendet ebenfalls TARGET_DAY, aber ohne Startup-Benachrichtigungen, schnellere Ausführung

### API Rate Limiting
The application implements conservative rate limiting:
- Community API limit: 100 requests/minute
- Application limit: 75 requests/minute (25% safety margin)
- Requests are tracked and throttled automatically

## Deployment Architecture

### Native Linux Deployment
The production setup creates:
- Dedicated user `bahnmonitor` for security
- Python virtual environment in `/opt/bahnabfrage/`
- Systemd service + timer for 4x daily execution (6:00, 12:00, 18:00, 00:00)
- Log directory `/var/log/bahnabfrage/`
- Configuration file at `/opt/bahnabfrage/.env`

### Docker Deployment
Alternative containerized deployment:
- Uses Python 3.11-slim base image
- Runs cron jobs inside container for scheduling
- Persistent logs via volume mount (`./logs:/var/log/bahnabfrage`)
- Health checks via configuration validation
- Environment variables loaded from `.env` file

## Error Handling

- API failures are logged and reported via Telegram
- Rate limit violations pause requests automatically  
- Telegram sending uses retry logic with backoff (3 attempts, 5s delays)
- Invalid dates (like March 32) are handled gracefully
- Session statistics track all errors for debugging
- Critical errors trigger immediate Telegram notifications
- Graceful handling of keyboard interrupts and exceptions

## File Structure and Key Locations

### Source Files (`src/`)
- `main.py:17-61` - CLI argument parser with --run, --test, --test-telegram modes
- `config.py:140-147` - Configuration loader and validator function
- `db_client.py:232-233` - Predefined station IDs for Hamburg Hbf and Landeck-Zams
- `connection_monitor.py:52-60` - Connection signature creation for duplicate detection
- `telegram_notifier.py:78-120` - New connection notification formatting

### Configuration Files
- `.env` - Environment variables (Telegram token, chat ID, API settings)
- `config/.env.example` - Configuration template
- `requirements.txt` - Python dependencies (requests, python-dotenv)

### Deployment Scripts
- `scripts/setup.sh` - Automated Linux production setup
- `Dockerfile` - Container image definition
- `docker-compose.yml` - Container orchestration
- `entrypoint.sh` - Docker container startup script

## Development Tips

### Testing Workflow
1. Always test configuration first: `python src/config.py`
2. Test Telegram connection: `python src/main.py --test-telegram`
3. Run limited test: `python src/main.py --test --verbose`
4. Only run full production scan when confident

### Wichtige Konstanten
- Hamburg Hbf Station ID: `8002549` (db_client.py:232)
- Landeck-Zams Station ID: `8100063` (db_client.py:233)
- Rate Limit: 75 Requests/Minute (25% Sicherheitsmarge)
- Standard TARGET_DAY: 15. März 2025 (konfigurierbar über .env)
- Test-Modus nutzt denselben TARGET_DAY wie Production

### Architektur-Highlights
- **Single-Day Focus**: Reduziert Komplexität durch Fokus auf einen Tag
- **Session-Based**: Keine persistente Speicherung, jeder Lauf startet fresh
- **Error-Resilient**: Umfassendes Error Handling mit Telegram-Benachrichtigungen
- **Rate-Limited**: Automatische Drosselung zum Schutz der API

### Häufige Probleme
- **Telegram funktioniert nicht**: Bot-Token-Format prüfen (muss Doppelpunkt enthalten: BOT_ID:TOKEN)
- **API Rate Limiting**: Anwendung drosselt automatisch auf 75/100 Requests/Minute
- **Keine Verbindungen gefunden**: Station-IDs und TARGET_DAY prüfen (nur März 2025)
- **Berechtigungsfehler**: Service-User `bahnmonitor` muss Eigentümer aller Dateien in `/opt/bahnabfrage/` sein
- **Falscher Tag**: TARGET_DAY muss zwischen 1-31 liegen und für März 2025 gültig sein

### Docker-specific Troubleshooting

#### Cron Jobs Not Running
Check if cron jobs are scheduled and running:
```bash
# View installed cron jobs
docker-compose exec bahnabfrage crontab -u bahnmonitor -l

# Check if cron daemon is running
docker-compose exec bahnabfrage ps aux | grep cron

# Monitor cron logs in real-time
docker-compose exec bahnabfrage tail -f /var/log/bahnabfrage/cron.log

# Or view logs from host
tail -f logs/cron.log
```

#### Environment Variables Not Loading
Verify `.env` file is properly mounted and accessible:
```bash
# Check .env file in container
docker-compose exec bahnabfrage ls -la /app/.env
docker-compose exec bahnabfrage cat /app/.env

# Test configuration loading
docker-compose exec bahnabfrage su bahnmonitor -c "cd /app && python src/config.py"
```

#### Manual Job Execution for Testing
```bash
# Run single job manually to test
docker-compose exec bahnabfrage su bahnmonitor -c "cd /app && python src/main.py --test"

# Check if environment variables are available during manual run
docker-compose exec bahnabfrage su bahnmonitor -c "cd /app && source .env && python src/main.py --test-telegram"
```

#### Container Logs
```bash
# View container startup logs
docker-compose logs bahnabfrage

# Follow live container logs
docker-compose logs -f bahnabfrage

# Check Docker container status
docker-compose ps
```