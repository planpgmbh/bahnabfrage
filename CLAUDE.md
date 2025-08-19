# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Deutsche Bahn Train Connection Monitor** that automatically monitors new train connections between Hamburg Hbf and Landeck-Zams for March 2025. The application:

- Monitors connections 4x daily (6:00, 12:00, 18:00, 00:00) using systemd timers
- Uses the free Community API (v6.db.transport.rest) - no official DB API authentication needed  
- Sends Telegram notifications for new connections with retry logic
- Operates session-based (no persistent database storage)
- Implements rate limiting (75/100 requests/minute for stability)

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

### Required Environment Variables (.env)
```bash
# Mandatory
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Route settings  
DEPARTURE_STATION=Hamburg Hbf
DESTINATION_STATION=Landeck-Zams
TARGET_MONTH=2025-03

# Optional optimization
API_TIMEOUT_SECONDS=30
MAX_RESULTS_PER_QUERY=20
LOG_LEVEL=INFO
```

### Production vs Test Mode
- **Production**: Scans all 31 days of March 2025, sends startup notifications
- **Test**: Only scans days 15-17, skips startup notifications, faster execution

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

### Key Constants
- Hamburg Hbf Station ID: `8002549` (db_client.py:232)
- Landeck-Zams Station ID: `8100063` (db_client.py:233)
- Rate limit: 75 requests/minute (25% safety margin from API limit)
- Test mode checks days 15-17 of March 2025
- Production mode checks all 31 days of March 2025

### Common Issues
- **Telegram not working**: Verify bot token format includes colon (BOT_ID:TOKEN)
- **API rate limiting**: Application automatically throttles to 75/100 requests/minute
- **No connections found**: Check station IDs and date range (March 2025 only)
- **Permission errors**: Ensure service user `bahnmonitor` owns all files in `/opt/bahnabfrage/`

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