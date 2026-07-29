#!/usr/bin/env bash
# trocr_lines adapter installer -- idempotent, own venv at .venv.
#
# ANNEX TRACK (recognition-only): TrOCR is a LINE-LEVEL model with no
# detector, so this adapter recognizes ground-truth line crops instead of
# full pages -- see predict.py header. microsoft/trocr-base-printed,
# ~1.33 GB safetensors, weights MIT.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

if command -v nvidia-smi >/dev/null 2>&1; then
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
else
  pip install torch torchvision
fi
pip install "transformers>=5.0" pillow pyarrow
