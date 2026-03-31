#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-/root/autodl-tmp/Guqin-Digitization-Core}"
CONDA_ROOT="${CONDA_ROOT:-/root/miniconda3}"
ENV_NAME="${ENV_NAME:-guqin-core}"
SKIP_DATASET_TOOLS_REQ="${SKIP_DATASET_TOOLS_REQ:-0}"

if [ ! -d "$REPO_ROOT" ]; then
  echo "Repo root not found: $REPO_ROOT" >&2
  exit 1
fi

source "$CONDA_ROOT/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" python=3.11
fi

conda activate "$ENV_NAME"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$REPO_ROOT/apps/ocr-engine/requirements.txt"
if [ "$SKIP_DATASET_TOOLS_REQ" != "1" ]; then
  python -m pip install -r "$REPO_ROOT/apps/dataset-tools/requirements.txt"
fi

python - <<'PY'
import sys
print("python", sys.version)
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
except Exception as exc:
    print("torch_import_error", repr(exc))
try:
    import ultralytics
    print("ultralytics", ultralytics.__version__)
except Exception as exc:
    print("ultralytics_import_error", repr(exc))
PY
