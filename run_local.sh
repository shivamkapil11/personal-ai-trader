#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [[ "${SKIP_PIP_INSTALL:-0}" != "1" ]]; then
  python -m pip install --upgrade pip || true
  python -m pip install -r "$ROOT_DIR/requirements.txt" || true
fi

export PYTHONPATH="$ROOT_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

HOST="${APP_HOST:-127.0.0.1}"
PORT="${APP_PORT:-8008}"

if [[ "${APP_RELOAD:-0}" == "1" ]]; then
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
