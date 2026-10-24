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

.venv/bin/python ../phone/make_shortcuts.py "$BASE_URL" > /dev/null

echo
echo "  Scam Check is reachable at  $BASE_URL"
echo "  Put that address and the token from .env into the app's Settings."
echo "  The two shortcuts in ../phone are rebuilt for this address. AirDrop them to the phone if it changed."
echo
.venv/bin/python app.py
