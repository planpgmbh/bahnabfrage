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

The production setup creates:
- Dedicated user `bahnmonitor` for security
- Python virtual environment in `/opt/bahnabfrage/`
- Systemd service + timer for 4x daily execution
- Log directory `/var/log/bahnabfrage/`

## Error Handling

- API failures are logged and reported via Telegram
- Rate limit violations pause requests automatically  
- Telegram sending uses retry logic with backoff
- Invalid dates (like March 32) are handled gracefully
- Session statistics track all errors for debugging