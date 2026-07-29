#!/usr/bin/env bash
# olmocr adapter installer -- idempotent, own venv at .venv.
#
# allenai/olmOCR-2-7B-1025 = Qwen2.5-VL-7B-Instruct fine-tune; 4 shards,
# 15.76 GB download, ~16-18 GB VRAM at bf16 batch 1 (fits a 4090). The
# `olmocr` pip package is NOT needed: it only provides the PDF renderer /
# prompt builder, and the prompt is inlined verbatim in predict.py while we
# feed PIL images directly. flash-attn is an optional speedup only, so a
# build failure must not sink the install.
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
pip install "transformers>=4.49" accelerate pillow pyarrow

# Optional: speeds the 7B up; tolerate failure.
pip install packaging ninja psutil || true
pip install flash-attn --no-build-isolation \
  || echo "flash-attn build failed; continuing without (optional speedup)" >&2
