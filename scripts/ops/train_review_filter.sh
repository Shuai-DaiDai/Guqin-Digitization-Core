#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DATASET="${DATASET:-}"
OUTPUT="${OUTPUT:-$REPO_ROOT/outputs/review_filter_runs}"
MODEL="${MODEL:-yolo11n-cls.pt}"
EPOCHS="${EPOCHS:-50}"
BATCH="${BATCH:-32}"
IMGSZ="${IMGSZ:-224}"
DEVICE="${DEVICE:-0}"
WORKERS="${WORKERS:-8}"
PRETRAINED="${PRETRAINED:-0}"
AMP="${AMP:-0}"
DRY_RUN="${DRY_RUN:-1}"

if [[ -z "$DATASET" ]]; then
  echo "DATASET is required" >&2
  exit 1
fi

PYTHONPATH="$REPO_ROOT/apps/ocr-engine/src" \
python3 -m ocr_engine train-yolo-classify \
  --dataset "$DATASET" \
  --output "$OUTPUT" \
  --model "$MODEL" \
  --epochs "$EPOCHS" \
  --batch "$BATCH" \
  --imgsz "$IMGSZ" \
  --device "$DEVICE" \
  --workers "$WORKERS" \
  $( [[ "$PRETRAINED" == "1" ]] && printf '%s ' --pretrained ) \
  $( [[ "$AMP" == "1" ]] && printf '%s ' --amp ) \
  $( [[ "$DRY_RUN" == "1" ]] && printf '%s ' --dry-run )
