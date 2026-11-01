#!/bin/sh
set -eu
export DISPLAY=:99
Xvfb :99 -screen 0 1440x900x24 &
fluxbox &
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
exec uvicorn app.browser.control:app --host 0.0.0.0 --port 9000
