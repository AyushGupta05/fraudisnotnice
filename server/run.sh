#!/usr/bin/env bash
# Start the public tunnel and the server together, and print the address to put in the app.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a; source .env; set +a
fi
PORT="${PORT:-5055}"

cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate > tunnel.log 2>&1 &
trap 'kill %1 2>/dev/null' EXIT

until BASE_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1); [ -n "$BASE_URL" ]; do
  sleep 1
done
export BASE_URL PORT

echo
echo "  Scam Check is reachable at  $BASE_URL"
echo "  Put that address and your token from .env into the app's Settings."
echo
.venv/bin/python app.py
