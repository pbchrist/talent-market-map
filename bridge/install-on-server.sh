#!/usr/bin/env bash
# Installs the model bridge on the machine that already runs llama-server.
#
# Puts the bridge behind a systemd unit and publishes it with Tailscale
# Funnel, so the public apps reach the model without anyone's laptop being
# awake. Touches nothing about llama-server itself.
#
#   curl -fsSL https://raw.githubusercontent.com/pbchrist/talent-market-map/main/bridge/install-on-server.sh | bash

set -euo pipefail

MODEL_URL="${MODEL_URL:-http://127.0.0.1:8082/v1/chat/completions}"
PORT="${PORT:-8767}"
ALLOW="${ALLOW:-https://pbchrist.github.io}"
DIR="$HOME/.model-bridge"
RAW="https://raw.githubusercontent.com/pbchrist/talent-market-map/main/bridge/bridge.py"

echo "==> model bridge installer"
echo "    forwarding to : $MODEL_URL"
echo "    listening on  : 127.0.0.1:$PORT"

command -v python3 >/dev/null || { echo "!! python3 not found"; exit 1; }
mkdir -p "$DIR"

echo "==> fetching bridge.py"
curl -fsSL "$RAW" -o "$DIR/bridge.py"

echo "==> python venv + httpx"
python3 -m venv "$DIR/venv" 2>/dev/null || true
"$DIR/venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
"$DIR/venv/bin/pip" install -q httpx

echo "==> checking the model is answering"
if ! curl -fsS -m 10 "${MODEL_URL%/v1/chat/completions}/v1/models" >/dev/null 2>&1; then
  echo "!! nothing answering at ${MODEL_URL%/v1/chat/completions} — start llama-server first"
  exit 1
fi

echo "==> installing systemd user unit"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/model-bridge.service" <<UNIT
[Unit]
Description=Public bridge to the local model
After=network-online.target

[Service]
Type=simple
Environment=PORT=$PORT
Environment=MODEL_URL=$MODEL_URL
Environment=ALLOW=$ALLOW
ExecStart=$DIR/venv/bin/python $DIR/bridge.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now model-bridge.service
loginctl enable-linger "$USER" >/dev/null 2>&1 || \
  echo "   (could not enable linger; run: sudo loginctl enable-linger $USER)"

sleep 3
if curl -fsS -m 8 "http://127.0.0.1:$PORT/health" >/dev/null; then
  echo "==> bridge is up locally"
else
  echo "!! bridge did not start. journalctl --user -u model-bridge -n 40"
  exit 1
fi

echo "==> publishing with Tailscale Funnel"
if ! command -v tailscale >/dev/null; then
  echo "!! tailscale CLI not found; install it, then: sudo tailscale funnel --bg $PORT"
  exit 1
fi
sudo tailscale funnel --bg "$PORT" >/dev/null 2>&1 || tailscale funnel --bg "$PORT" || {
  echo "!! funnel failed. Try: sudo tailscale funnel --bg $PORT"; exit 1; }

sleep 3
URL="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("https://"+d["Self"]["DNSName"].rstrip("."))' 2>/dev/null || true)"

echo
echo "============================================================"
echo " DONE. Public endpoint:"
echo
echo "   ${URL:-https://<this-machine>.<tailnet>.ts.net}"
echo
echo " Paste that URL back to Claude and it will point both apps at it."
echo "============================================================"
