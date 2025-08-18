#!/bin/bash
# Setup-Script für Deutsche Bahn Verbindungsüberwachung
# Führt alle notwendigen Installationen und Konfigurationen durch

set -e  # Exit bei Fehlern

echo "🚀 Deutsche Bahn Verbindungsüberwachung - Setup"
echo "=============================================="

# Basis-Verzeichnisse
PROJECT_DIR="/opt/bahnabfrage"
USER="bahnmonitor"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. System-Updates
print_status "System-Updates installieren..."
sudo apt update && sudo apt upgrade -y

# 2. Python3 und pip installieren
print_status "Python3 und pip installieren..."
sudo apt install -y python3 python3-pip python3-venv

# 3. Dedicated User erstellen
print_status "User '$USER' erstellen..."
if ! id "$USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d $PROJECT_DIR $USER
    print_status "User '$USER' erstellt"
else
    print_warning "User '$USER' existiert bereits"
fi

# 4. Projekt-Verzeichnis erstellen
print_status "Projekt-Verzeichnis erstellen..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# 5. Dateien kopieren (falls vom aktuellen Verzeichnis ausgeführt)
if [ -f "src/main.py" ]; then
    print_status "Projektdateien kopieren..."
    sudo cp -r src/ config/ requirements.txt $PROJECT_DIR/
    sudo chown -R $USER:$USER $PROJECT_DIR
else
    print_warning "Projektdateien nicht gefunden - manuell kopieren erforderlich"
fi

# 6. Virtual Environment erstellen
print_status "Python Virtual Environment erstellen..."
sudo -u $USER python3 -m venv $PROJECT_DIR/venv
sudo -u $USER $PROJECT_DIR/venv/bin/pip install --upgrade pip

# 7. Dependencies installieren
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    print_status "Python Dependencies installieren..."
    sudo -u $USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt
else
    print_error "requirements.txt nicht gefunden"
    exit 1
fi

# 8. Produktions-.env Datei erstellen
print_status "Produktions-.env Datei erstellen..."
if [ -f "$PROJECT_DIR/config/.env.production" ]; then
    sudo -u $USER cp $PROJECT_DIR/config/.env.production $PROJECT_DIR/.env
    print_status "Produktions-Konfiguration installiert"
else
    sudo -u $USER cp $PROJECT_DIR/config/.env.example $PROJECT_DIR/.env
    print_warning "WICHTIG: .env Datei konfigurieren! (TELEGRAM_CHAT_ID setzen)"
fi

# 9. Log-Verzeichnis erstellen
print_status "Log-Verzeichnis erstellen..."
sudo mkdir -p /var/log/bahnabfrage
sudo chown $USER:$USER /var/log/bahnabfrage

# 10. Systemd Service erstellen
print_status "Systemd Service konfigurieren..."
sudo tee /etc/systemd/system/bahnabfrage.service > /dev/null << EOF
[Unit]
Description=Deutsche Bahn Verbindungsüberwachung
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main.py --run
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 11. Systemd Timer erstellen (alle 6 Stunden - optimal für Rate Limits)
print_status "Systemd Timer konfigurieren..."
sudo tee /etc/systemd/system/bahnabfrage.timer > /dev/null << EOF
[Unit]
Description=Deutsche Bahn Verbindungsüberwachung Timer
Requires=bahnabfrage.service

[Timer]
OnCalendar=06:00,12:00,18:00,00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

# 12. Systemd Services aktivieren
print_status "Systemd Services aktivieren..."
sudo systemctl daemon-reload
sudo systemctl enable bahnabfrage.timer

# 13. Berechtigungen setzen
print_status "Berechtigungen setzen..."
sudo chmod +x $PROJECT_DIR/src/main.py
sudo chmod 600 $PROJECT_DIR/.env

# 14. Test-Lauf
print_status "Test-Lauf durchführen..."
if sudo -u $USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/config.py; then
    print_status "Konfiguration erfolgreich getestet"
else
    print_error "Konfigurationstest fehlgeschlagen"
fi

echo ""
echo "🎉 Setup abgeschlossen!"
echo "====================="
echo ""
echo "Nächste Schritte:"
echo "1. TELEGRAM_CHAT_ID in $PROJECT_DIR/.env konfigurieren"
echo "2. Timer starten: sudo systemctl start bahnabfrage.timer"
echo "3. Status prüfen: sudo systemctl status bahnabfrage.timer"
echo "4. Test ausführen: sudo -u $USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main.py --test"
echo ""
echo "Wichtige Befehle:"
echo "- Timer Status: sudo systemctl status bahnabfrage.timer"
echo "- Logs anzeigen: sudo journalctl -u bahnabfrage -f"
echo "- Timer stoppen: sudo systemctl stop bahnabfrage.timer"
echo "- Manuelle Ausführung: sudo -u $USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main.py --run"