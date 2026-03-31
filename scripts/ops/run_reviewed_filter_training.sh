#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: $0 <reviewed_crop_dataset_dir> [epochs] [batch] [imgsz] [device] [dry_run]" >&2
  exit 2
fi

DATASET_DIR="$1"
EPOCHS="${2:-50}"
BATCH="${3:-32}"
IMGSZ="${4:-224}"
DEVICE="${5:-0}"
DRY_RUN="${6:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_REPO_ROOT="${REMOTE_REPO_ROOT:-/root/autodl-tmp/Guqin-Digitization-Core}"
RUN_ROOT="${RUN_ROOT:-/root/autodl-tmp/guqin-runs}"
FILTER_RUN_ROOT="${FILTER_RUN_ROOT:-${RUN_ROOT}/reviewed_filter_runs}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-guqin-core}"
LOG_PATH="${LOG_PATH:-${RUN_ROOT}/$(date -u +%Y%m%dT%H%M%SZ)-reviewed-filter-training.log}"

if [[ ! -d "${DATASET_DIR}" ]]; then
  echo "Dataset directory not found: ${DATASET_DIR}" >&2
  exit 1
fi

mkdir -p "${RUN_ROOT}"

if [[ ! -f /root/miniconda3/etc/profile.d/conda.sh ]]; then
  echo "conda initialization script not found: /root/miniconda3/etc/profile.d/conda.sh" >&2
  exit 1
fi

# shellcheck disable=SC1091
source /root/miniconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV_NAME}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found in PATH. GPU environment is not ready." >&2
  exit 1
fi

nvidia-smi

export PYTHONPATH="${REMOTE_REPO_ROOT}/apps/ocr-engine/src:${REMOTE_REPO_ROOT}/apps/dataset-tools/src"

{
  echo "[INFO] Started reviewed-filter training at $(date -u +%FT%TZ)"
  echo "[INFO] Repository root: ${REMOTE_REPO_ROOT}"
  echo "[INFO] Dataset directory: ${DATASET_DIR}"
  echo "[INFO] Run root: ${FILTER_RUN_ROOT}"

  DATASET_DIR="${DATASET_DIR}" python - <<'PY'
import os
from pathlib import Path

dataset = Path(os.environ["DATASET_DIR"])
manifest = dataset / "manifest.csv"
export_report = dataset / "export_report.json"
if not dataset.is_dir():
    raise SystemExit(f"Dataset directory missing: {dataset}")
if not manifest.exists():
    raise SystemExit(f"Dataset manifest missing: {manifest}")
if not export_report.exists():
    raise SystemExit(f"Dataset report missing: {export_report}")
print(f"dataset_ok: {dataset}")
print(f"manifest_ok: {manifest}")
print(f"report_ok: {export_report}")
PY

  python - <<'PY'
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("cuda_device_count", torch.cuda.device_count())
        print("cuda_device_name", torch.cuda.get_device_name(0))
except Exception as exc:
    print("torch_import_error", repr(exc))

try:
    import ultralytics
    print("ultralytics", ultralytics.__version__)
except Exception as exc:
    print("ultralytics_import_error", repr(exc))
PY

  if [[ "${DRY_RUN}" == "1" ]]; then
    python -m ocr_engine train-yolo-classify \
      --dataset "${DATASET_DIR}" \
      --output "${FILTER_RUN_ROOT}" \
      --epochs "${EPOCHS}" \
      --batch "${BATCH}" \
      --imgsz "${IMGSZ}" \
      --device "${DEVICE}" \
      --dry-run
  else
    python -m ocr_engine train-yolo-classify \
      --dataset "${DATASET_DIR}" \
      --output "${FILTER_RUN_ROOT}" \
      --epochs "${EPOCHS}" \
      --batch "${BATCH}" \
      --imgsz "${IMGSZ}" \
      --device "${DEVICE}"
  fi

  LATEST_RUN="$(ls -1dt "${FILTER_RUN_ROOT}"/* | head -n 1)"
  echo "[INFO] Training run: ${LATEST_RUN}"

  if [[ -f "${LATEST_RUN}/run_status.json" ]]; then
    echo "[INFO] Run status:"
    cat "${LATEST_RUN}/run_status.json"
  fi

  echo "[INFO] Finished reviewed-filter training at $(date -u +%FT%TZ)"
} 2>&1 | tee "${LOG_PATH}"
