#!/usr/bin/env bash
# One-time box setup for the OCR benchmark (Ubuntu box, e.g. Vast.ai RTX 4090).
#
#   bash benchmark/vast/setup.sh
#
# - apt basics: tesseract (+ the DE/IT/FR language packs the receipts need),
#   python venv, tmux, and the GL/glib libs opencv-based OCR stacks link against
# - runner venv at benchmark/.venv (pyarrow for score.py, huggingface_hub)
# - downloads ONLY data/eval-0000.parquet from the HF dataset
#   albertobarnabo/synthetic-receipts-ocr into <repo>/data/eval-0000.parquet,
#   which is the default --parquet location run_model.sh expects.
set -uo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$BENCH/.." && pwd)"

die() { echo "setup.sh: $*" >&2; exit 1; }

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -y || die "apt-get update failed"
$SUDO apt-get install -y --no-install-recommends \
  tesseract-ocr tesseract-ocr-deu tesseract-ocr-ita tesseract-ocr-fra \
  python3-venv python3-pip tmux git \
  libgl1 libglib2.0-0 \
  || die "apt-get install failed"

if [ ! -x "$BENCH/.venv/bin/python" ]; then
  python3 -m venv "$BENCH/.venv" || die "venv creation failed"
fi
"$BENCH/.venv/bin/pip" install --quiet --upgrade pip
"$BENCH/.venv/bin/pip" install --quiet pyarrow huggingface_hub || die "pip install failed"

PARQUET="$REPO/data/eval-0000.parquet"
if [ -f "$PARQUET" ]; then
  echo "eval shard already present: $PARQUET"
else
  echo "downloading eval shard from albertobarnabo/synthetic-receipts-ocr ..."
  "$BENCH/.venv/bin/python" - "$REPO" <<'PY' || die "eval shard download failed"
import sys
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="albertobarnabo/synthetic-receipts-ocr",
    repo_type="dataset",
    filename="data/eval-0000.parquet",
    local_dir=sys.argv[1],
)
print("eval shard:", path)
PY
fi
[ -f "$PARQUET" ] || die "expected $PARQUET after download"

echo "setup complete"
tesseract --version 2>/dev/null | head -1 || true
nvidia-smi -L 2>/dev/null || echo "note: nvidia-smi not available (CPU-only box?)"
