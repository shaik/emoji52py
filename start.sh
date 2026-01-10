#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$ROOT_DIR/.venv" ]; then
  echo "Missing .venv. Run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR"
PORT=8200

if command -v lsof >/dev/null 2>&1; then
  existing_pids="$(lsof -n -P -ti tcp:$PORT || true)"
  if [ -n "$existing_pids" ]; then
    echo "Port $PORT in use by PID(s) $existing_pids; stopping them."
    for pid in $existing_pids; do
      kill "$pid" || true
    done
    for _ in 1 2 3 4 5; do
      all_gone=true
      for pid in $existing_pids; do
        if kill -0 "$pid" 2>/dev/null; then
          all_gone=false
        fi
      done
      if [ "$all_gone" = true ]; then
        break
      fi
      sleep 0.2
    done
    for pid in $existing_pids; do
      if kill -0 "$pid" 2>/dev/null; then
        echo "PID $pid still running; force killing."
        kill -9 "$pid" || true
      fi
    done
  fi
else
  echo "lsof not found; unable to auto-kill process on port $PORT." >&2
fi

exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
