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

# The phone talks to this Mac by its local name, which stays the same on any Wi-Fi or hotspot you share.
# Only the links inside drills use the tunnel, because those must work from anyone's phone.
LOCAL_URL="http://$(scutil --get LocalHostName | tr 'A-Z' 'a-z').local:$PORT"
.venv/bin/python ../phone/make_shortcuts.py "$LOCAL_URL" > /dev/null \
  || echo "  Could not rebuild the shortcuts. Run: python3 phone/make_shortcuts.py $LOCAL_URL"

echo
echo "  Drill links use            $BASE_URL"
echo "  Your phone uses            $LOCAL_URL   (same Wi-Fi or hotspot as this Mac)"
echo "  Put the second address and the token from .env into the app's Settings."
echo "  The two shortcuts in ../phone are built for it; import them on the phone once."
echo
.venv/bin/python app.py
