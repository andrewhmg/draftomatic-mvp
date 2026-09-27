#!/bin/bash
# Draftomatic screenshot driver — self-contained: boots server, shoots 4 screens, kills everything.
set -u
cd "$(dirname "$0")"
rm -f /tmp/drafto_shots_done
/usr/bin/python3 server.py > server.log 2>&1 &
SRV=$!
sleep 1.5
# read the port the server actually bound (8765..8784)
PORT=""
for p in 8765 8766 8767 8768 8769 8770 8771 8772; do
  if curl -s --max-time 2 "http://127.0.0.1:$p/api/health" | grep -q '"ok"'; then PORT=$p; break; fi
done
if [ -z "$PORT" ]; then echo "no server up" > /tmp/drafto_shots_done; kill $SRV; exit 1; fi
echo "port=$PORT"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
i=0
for pair in "01-connect:/" "02-topics:/topics" "03-preview:/preview" "04-dashboard:/dashboard"; do
  name="${pair%%:*}"; path="${pair#*:}"
  out="screens/$name.png"
  rm -f "$out"
  ud="/tmp/chrome-drafto-$name"
  "$CHROME" --headless --disable-gpu --user-data-dir="$ud" --no-first-run \
    --screenshot="$out" --window-size=1440,900 --virtual-time-budget=5000 --hide-scrollbars \
    "http://127.0.0.1:$PORT$path" > /dev/null 2>&1 &
  CPID=$!
  for n in 1 2 3 4 5 6 7 8 9 10 11 12; do [ -s "$out" ] && break; sleep 1; done
  kill $CPID 2>/dev/null
  pkill -f "user-data-dir=$ud" 2>/dev/null
  if [ -s "$out" ]; then echo "$name OK $(stat -f%z "$out")"; else echo "$name MISSING"; fi
done
kill $SRV 2>/dev/null
pkill -f "server.py" 2>/dev/null
echo done > /tmp/drafto_shots_done