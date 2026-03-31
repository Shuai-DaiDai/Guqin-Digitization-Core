#!/usr/bin/env bash
set -euo pipefail

TOKEN="${1:?usage: run_remote_review_service.sh <token> [port]}"
PORT="${2:-8787}"

RUNTIME_DIR="/root/autodl-tmp/guqin-review-live/runtime"
SITE_ROOT="/root/autodl-tmp/guanpinghu-batch-001-live"
SRC_ROOT="/root/autodl-tmp/review-service/src"

mkdir -p "$RUNTIME_DIR"
pkill -f "review_service.cli" 2>/dev/null || true

cd "$SRC_ROOT"
nohup /root/miniconda3/bin/python -u -m review_service.cli \
  --site-root "$SITE_ROOT" \
  --db "$RUNTIME_DIR/review.db" \
  --token "$TOKEN" \
  --host 127.0.0.1 \
  --port "$PORT" \
  >"$RUNTIME_DIR/review-service.log" 2>&1 </dev/null &

sleep 2
/usr/bin/curl -m 3 -sS "http://127.0.0.1:${PORT}/healthz" || true
