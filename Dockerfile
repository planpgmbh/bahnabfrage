FROM python:3.11-slim

# Metadaten
LABEL maintainer="Deutsche Bahn Verbindungsüberwachung"
LABEL description="Hamburg → Landeck-Zams Verbindungsmonitor"

# Arbeitsverzeichnis
WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY src/ ./src/
COPY config/ ./config/

# Logs-Verzeichnis
RUN mkdir -p /var/log/bahnabfrage

# Cron-Job Setup
COPY crontab /etc/cron.d/bahnabfrage
RUN chmod 0644 /etc/cron.d/bahnabfrage
RUN crontab /etc/cron.d/bahnabfrage

# Entrypoint Script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root User (aber Container startet als Root für Cron)
RUN useradd -r -s /bin/bash bahnmonitor
RUN chown -R bahnmonitor:bahnmonitor /app /var/log/bahnabfrage
# USER bahnmonitor  # Entfernt - Container startet als Root für Cron

# Health Check (nur Konfiguration prüfen, keine Nachrichten)
HEALTHCHECK --interval=6h --timeout=30s --start-period=1m \
    CMD python src/config.py || exit 1

# Port für Health-Check (optional)
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
CMD ["cron", "-f"]