#!/usr/bin/env bash
# dots_ocr adapter installer -- idempotent, own venv at .venv.
#
# rednote-hilab/dots.ocr (~3B VLM, MIT). Plain transformers works with
# trust_remote_code=True; vllm==0.9.1 (their eval baseline) is OPTIONAL and
# not used here. flash-attn is effectively REQUIRED (custom vision path; the
# sdpa fallback is reported to work but unverified). The repo's
# `pip install -e .` registers the custom model class. GPU-required.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu124
pip install "transformers>=4.51" accelerate qwen-vl-utils pillow pyarrow
# flash-attn builds against the already-installed torch; helpers first.
pip install packaging ninja psutil
pip install flash-attn --no-build-isolation

# Idempotent clone. NOTE the known gotcha: a LOCAL weights folder must have NO
# dot in its name (rename to e.g. DotsOCR) or the dynamic import fails; loading
# straight from the hub id 'rednote-hilab/dots.ocr' (what predict.py does) is
# fine. The source checkout dir name is irrelevant to that gotcha.
[ -d dots.ocr ] || git clone https://github.com/rednote-hilab/dots.ocr
pip install -e dots.ocr
