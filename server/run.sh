#!/usr/bin/env bash
# Start the public tunnel and the server together, and print the address to put in the app.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a; source .env; set +a
fi
PORT="${PORT:-5055}"

# http2 rather than the default quic: many venue and university networks block the UDP port quic needs.
cloudflared tunnel --url "http://localhost:$PORT" --protocol http2 --no-autoupdate > tunnel.log 2>&1 &
trap 'kill %1 2>/dev/null' EXIT

until BASE_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1); [ -n "$BASE_URL" ]; do
  sleep 1
done
export BASE_URL PORT

for _ in $(seq 20); do
  grep -q "Registered tunnel connection" tunnel.log && break
  sleep 1
done
if ! grep -q "Registered tunnel connection" tunnel.log; then
  echo
  echo "  The tunnel has an address but cannot connect: this network blocks outbound port 7844."
  echo "  Switch to your phone's hotspot or another network and run this again."
fi

echo
echo "  Scam Check is reachable at  $BASE_URL"
echo "  Put that address and the token from .env into the app's Settings."
echo
.venv/bin/python app.py
