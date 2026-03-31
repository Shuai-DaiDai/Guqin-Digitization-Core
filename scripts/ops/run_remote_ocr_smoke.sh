#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-/root/autodl-tmp/Guqin-Digitization-Core}"
CONDA_ROOT="${CONDA_ROOT:-/root/miniconda3}"
ENV_NAME="${ENV_NAME:-guqin-core}"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/guqin-runs}"

source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

cd "$REPO_ROOT"
mkdir -p "$RUN_ROOT"

OCR_BUNDLES="$RUN_ROOT/ocr_bundles"
WORKSPACE_ROOT="$RUN_ROOT/dataset_workspace"
YOLO_DATASETS="$RUN_ROOT/yolo_datasets"
TRAIN_RUNS="$RUN_ROOT/train_runs"
PREDICT_RUNS="$RUN_ROOT/predict_runs"

PYTHONPATH=apps/ocr-engine/src \
python -m ocr_engine detect \
  --input apps/ocr-engine/examples/minimal_ocr_input.json \
  --expected-layout apps/ocr-engine/examples/minimal_expected_layout.json \
  --output "$OCR_BUNDLES"

LATEST_OCR_BUNDLE="$(ls -1dt "$OCR_BUNDLES"/* | head -n 1)"

PYTHONPATH=apps/dataset-tools/src \
python -m dataset_tools import-ocr-bundle \
  --input "$LATEST_OCR_BUNDLE" \
  --output "$WORKSPACE_ROOT"

LATEST_WORKSPACE_BUNDLE="$(ls -1dt "$WORKSPACE_ROOT"/* | head -n 1)"

PYTHONPATH=apps/dataset-tools/src \
python -m dataset_tools process-bundle \
  --bundle "$LATEST_WORKSPACE_BUNDLE"

PYTHONPATH=apps/ocr-engine/src \
python -m ocr_engine export-yolo-detect \
  --bundle "$LATEST_WORKSPACE_BUNDLE" \
  --output "$YOLO_DATASETS"

LATEST_YOLO_DATASET="$(ls -1dt "$YOLO_DATASETS"/* | head -n 1)"

PYTHONPATH=apps/ocr-engine/src \
python -m ocr_engine train-yolo-detect \
  --dataset "$LATEST_YOLO_DATASET" \
  --output "$TRAIN_RUNS" \
  --model yolo11n.pt \
  --epochs 5 \
  --imgsz 1024 \
  --batch 2 \
  --device 0

LATEST_TRAIN_RUN="$(ls -1dt "$TRAIN_RUNS"/* | head -n 1)"
BEST_MODEL="$(find "$LATEST_TRAIN_RUN" -path '*/weights/best.pt' | head -n 1)"

if [ -n "${BEST_MODEL:-}" ] && [ -f "$BEST_MODEL" ]; then
  PYTHONPATH=apps/ocr-engine/src \
  python -m ocr_engine detect-yolo \
    --input apps/ocr-engine/examples/minimal_ocr_input.json \
    --model "$BEST_MODEL" \
    --output "$PREDICT_RUNS" \
    --source-id smoke-yolo
fi

nvidia-smi
