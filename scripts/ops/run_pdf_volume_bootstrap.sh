#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" || "${2:-}" == "" ]]; then
  echo "Usage: $0 <rendered_pages_dir> <source_id> [epochs] [batch] [imgsz] [shutdown_on_finish]" >&2
  exit 2
fi

RENDERED_PAGES_DIR="$1"
SOURCE_ID="$2"
EPOCHS="${3:-30}"
BATCH="${4:-4}"
IMGSZ="${5:-1024}"
SHUTDOWN_ON_FINISH="${6:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/guqin-runs}"
OCR_OUTPUT_ROOT="${OCR_OUTPUT_ROOT:-${RUN_ROOT}/ocr_bundles_pdf_clustered_full}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-${RUN_ROOT}/dataset_workspace_pdf_clustered_full}"
YOLO_OUTPUT_ROOT="${YOLO_OUTPUT_ROOT:-${RUN_ROOT}/yolo_datasets_clustered_full}"
TRAIN_OUTPUT_ROOT="${TRAIN_OUTPUT_ROOT:-${RUN_ROOT}/train_runs_clustered_full}"
MODEL_NAME="${MODEL_NAME:-yolo11n.yaml}"
WORKERS="${WORKERS:-8}"
DEVICE="${DEVICE:-0}"
DETECT_WORKERS="${DETECT_WORKERS:-8}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-guqin-core}"
LOG_PATH="${LOG_PATH:-${RUN_ROOT}/$(date -u +%Y%m%dT%H%M%SZ)-${SOURCE_ID}-bootstrap.log}"

mkdir -p "${RUN_ROOT}"

if [[ -f /root/miniconda3/etc/profile.d/conda.sh ]]; then
  # shellcheck disable=SC1091
  source /root/miniconda3/etc/profile.d/conda.sh
  conda activate "${CONDA_ENV_NAME}"
fi

export PYTHONPATH="${REPO_ROOT}/apps/ocr-engine/src:${REPO_ROOT}/apps/dataset-tools/src"

{
  echo "[INFO] Started bootstrap pipeline at $(date -u +%FT%TZ)"
  echo "[INFO] Rendered pages: ${RENDERED_PAGES_DIR}"
  echo "[INFO] Source id: ${SOURCE_ID}"

  cd "${REPO_ROOT}"

  python -m ocr_engine detect \
    --input "${RENDERED_PAGES_DIR}" \
    --output "${OCR_OUTPUT_ROOT}" \
    --source-id "${SOURCE_ID}" \
    --workers "${DETECT_WORKERS}"
  OCR_BUNDLE="$(ls -dt "${OCR_OUTPUT_ROOT}"/* | head -n 1)"
  echo "[INFO] OCR bundle: ${OCR_BUNDLE}"

  python -m dataset_tools import-ocr-bundle \
    --input "${OCR_BUNDLE}" \
    --output "${WORKSPACE_ROOT}"
  WORKSPACE_BUNDLE="$(ls -dt "${WORKSPACE_ROOT}"/* | head -n 1)"
  echo "[INFO] Workspace bundle: ${WORKSPACE_BUNDLE}"

  python -m dataset_tools process-bundle \
    --bundle "${WORKSPACE_BUNDLE}"

  python -m ocr_engine export-yolo-detect \
    --bundle "${WORKSPACE_BUNDLE}" \
    --output "${YOLO_OUTPUT_ROOT}"
  YOLO_DATASET="$(ls -dt "${YOLO_OUTPUT_ROOT}"/* | head -n 1)"
  echo "[INFO] YOLO dataset: ${YOLO_DATASET}"

  python -m ocr_engine train-yolo-detect \
    --dataset "${YOLO_DATASET}" \
    --output "${TRAIN_OUTPUT_ROOT}" \
    --model "${MODEL_NAME}" \
    --epochs "${EPOCHS}" \
    --imgsz "${IMGSZ}" \
    --batch "${BATCH}" \
    --device "${DEVICE}" \
    --workers "${WORKERS}"
  TRAIN_RUN="$(ls -dt "${TRAIN_OUTPUT_ROOT}"/* | head -n 1)"
  echo "[INFO] Training run: ${TRAIN_RUN}"
  echo "[INFO] Finished bootstrap pipeline at $(date -u +%FT%TZ)"
} 2>&1 | tee "${LOG_PATH}"

if [[ "${SHUTDOWN_ON_FINISH}" == "1" ]]; then
  shutdown -h now
fi
