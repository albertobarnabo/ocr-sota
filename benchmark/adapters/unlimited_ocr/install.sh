#!/usr/bin/env bash
# unlimited_ocr adapter installer -- idempotent, own venv at .venv.
#
# baidu/Unlimited-OCR: ~3.34B, DeepSeek-OCR-derived, single 6.67 GB
# safetensors. Weights are open and downloadable => this is a MEASURED row.
# Pinned deps per the model README (the per-adapter venv keeps this older
# transformers==4.57.1 away from GLM-OCR's >=5.0). flash-attn is NOT listed
# in their README deps but the model is DeepSeek-OCR-derived, whose modeling
# imports flash_attn -- installed to be safe. GPU-required (custom high-res
# multi-crop pipeline).
#
# LICENSE UNVERIFIED: one card scrape said MIT, but the repo ships a custom
# 'License agreement' file + NOTICE (typical of Baidu's own license) --
# confirm before publishing numbers.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu124
pip install transformers==4.57.1 pillow==12.1.1 einops accelerate pyarrow
pip install packaging ninja psutil
pip install flash-attn --no-build-isolation
