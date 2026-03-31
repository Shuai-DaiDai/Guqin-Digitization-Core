#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BUNDLE="${BUNDLE:-}"
OUTPUT="${OUTPUT:-}"

if [[ -z "$BUNDLE" ]]; then
  echo "BUNDLE is required" >&2
  exit 1
fi

if [[ -n "$OUTPUT" ]]; then
  PYTHONPATH="$REPO_ROOT/apps/dataset-tools/src" \
  python3 - <<PY
from pathlib import Path
from dataset_tools.pipeline import evaluate_review_impact
evaluate_review_impact(Path("$BUNDLE"), Path("$OUTPUT"))
PY
else
  PYTHONPATH="$REPO_ROOT/apps/dataset-tools/src" \
  python3 - <<PY
from pathlib import Path
from dataset_tools.pipeline import evaluate_review_impact
evaluate_review_impact(Path("$BUNDLE"))
PY
fi
