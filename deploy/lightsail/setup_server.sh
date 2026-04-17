#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-ubuntu}"
APP_HOME="${APP_HOME:-/home/$APP_USER}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
APP_PORT="${APP_PORT:-8008}"
APP_HOST="${APP_HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Updating apt packages..."
sudo apt-get update -y
sudo apt-get install -y git nginx python3 python3-venv python3-pip

if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
  echo "Could not find requirements.txt in $APP_DIR"
  echo "Upload or clone the repo onto the server first, then run this script from inside the repo."
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Creating .env from .env.example"
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

if [[ ! -d "$APP_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
fi

source "$APP_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$APP_DIR/requirements.txt"

sudo cp "$APP_DIR/deploy/lightsail/gains.service" /etc/systemd/system/gains.service
sudo cp "$APP_DIR/deploy/lightsail/nginx-gains.conf" /etc/nginx/sites-available/gains
sudo ln -sf /etc/nginx/sites-available/gains /etc/nginx/sites-enabled/gains
sudo rm -f /etc/nginx/sites-enabled/default

sudo systemctl daemon-reload
sudo systemctl enable gains
sudo systemctl restart gains
sudo nginx -t
sudo systemctl restart nginx

echo
echo "Lightsail server setup complete."
echo "Next:"
echo "1. Edit $APP_DIR/.env"
echo "2. sudo systemctl restart gains"
echo "3. sudo systemctl status gains"
echo "4. Open http://<your-server-ip>"
