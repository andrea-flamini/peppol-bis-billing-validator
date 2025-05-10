#!/bin/bash

SERVICE_NAME="peppol-validator.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
APP_DIR="/home/pi/peppol-bis-billing-validator"
PYTHON_BIN="$APP_DIR/venv/bin/python3"
SERVER_FILE="$APP_DIR/server.py"

create_service() {
  echo "➡️  Creazione file systemd per il servizio Peppol..."

  sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Peppol XML Validator
After=network.target

[Service]
User=pi
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_BIN $SERVER_FILE
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

  echo "✅ File creato: $SERVICE_PATH"
  echo "🔄 Ricarico systemd..."
  sudo systemctl daemon-reexec
  sudo systemctl daemon-reload

  echo "✅ Abilito il servizio per l'avvio automatico..."
  sudo systemctl enable "$SERVICE_NAME"

  echo "🚀 Avvio il servizio ora..."
  sudo systemctl restart "$SERVICE_NAME"

  echo "🔍 Stato del servizio:"
  sudo systemctl status "$SERVICE_NAME" --no-pager
}

disable_service() {
  echo "⛔ Fermo e disabilito il servizio..."
  sudo systemctl stop "$SERVICE_NAME"
  sudo systemctl disable "$SERVICE_NAME"
  echo "✅ Servizio disabilitato."
}

restart_service() {
  echo "🔄 Riavvio il servizio..."
  sudo systemctl restart "$SERVICE_NAME"
  sudo systemctl status "$SERVICE_NAME" --no-pager
}

show_status() {
  echo "🔍 Stato attuale del servizio:"
  sudo systemctl status "$SERVICE_NAME" --no-pager
}

echo "=== Gestione Servizio Peppol XML Validator ==="
echo "1) Installa e attiva il servizio"
echo "2) Ferma e disattiva il servizio"
echo "3) Riavvia il servizio"
echo "4) Mostra stato del servizio"
echo "5) Esci"
echo "=============================================="
read -p "Seleziona un'opzione (1-5): " choice

case $choice in
  1) create_service ;;
  2) disable_service ;;
  3) restart_service ;;
  4) show_status ;;
  5) echo "Uscita." ;;
  *) echo "Opzione non valida." ;;
esac

