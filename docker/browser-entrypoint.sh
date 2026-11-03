#!/bin/sh
set -eu
export DISPLAY=:99
Xvfb "$DISPLAY" -screen 0 1440x900x24 > /tmp/xvfb.log 2>&1 &
xvfb_pid=$!

# Chromium is started during FastAPI startup. Do not let it race Xvfb: a
# headed Playwright browser exits immediately when the display socket is not
# ready yet.
ready=false
for _ in $(seq 1 100); do
    if [ -S /tmp/.X11-unix/X99 ]; then
        ready=true
        break
    fi
    if ! kill -0 "$xvfb_pid" 2>/dev/null; then
        cat /tmp/xvfb.log >&2
        exit 1
    fi
    sleep 0.1
done
if [ "$ready" != true ]; then
    echo "Timed out waiting for Xvfb on $DISPLAY" >&2
    cat /tmp/xvfb.log >&2
    exit 1
fi

fluxbox &
x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
exec uvicorn app.browser.control:app --host 0.0.0.0 --port 9000
