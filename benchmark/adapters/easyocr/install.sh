#!/usr/bin/env bash
# easyocr adapter installer -- idempotent, own venv at .venv.
#
# easyocr 1.7.2 is the latest release (2024-09-24, stable but stale); it pulls
# torch, torchvision, opencv-python-headless, scipy, etc. and may emit
# torch/numpy deprecation warnings on a modern stack. The default Linux torch
# wheel is CUDA-enabled, which is what the 4090 box needs.
set -euo pipefail
cd "$(dirname "$0")"

if command -v apt-get >/dev/null 2>&1; then
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
  $SUDO apt-get update -y || true
  $SUDO apt-get install -y libgl1 libglib2.0-0
fi

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install easyocr==1.7.2 pyarrow pillow
