#!/usr/bin/env bash
# got_ocr2 adapter installer -- idempotent, own venv at .venv.
#
# stepfun-ai/GOT-OCR-2.0-hf: 580M encoder-decoder, runs via plain transformers
# (class GotOcr2ForConditionalGeneration / AutoModelForImageTextToText).
# NO flash-attn needed. Single model.safetensors = 1.04 GB, Apache-2.0.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

if command -v nvidia-smi >/dev/null 2>&1; then
  pip install torch --index-url https://download.pytorch.org/whl/cu124
else
  pip install torch
fi
pip install "transformers>=4.49" accelerate pillow numpy pyarrow
