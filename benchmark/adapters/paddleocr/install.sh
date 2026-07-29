#!/usr/bin/env bash
# paddleocr adapter installer -- idempotent, own venv at .venv.
#
# paddlepaddle (CPU) and paddlepaddle-gpu must NEVER be installed together;
# this script picks ONE based on nvidia-smi and uninstalls the other so
# re-runs stay consistent. GPU wheel index matches the box CUDA (RTX 4090
# -> cu126 works; other indexes: /cu118/ /cu129/ /cu130/).
set -euo pipefail
cd "$(dirname "$0")"

if command -v apt-get >/dev/null 2>&1; then
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
  $SUDO apt-get update -y || true
  $SUDO apt-get install -y libgl1 libglib2.0-0 libgomp1
fi

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip

if command -v nvidia-smi >/dev/null 2>&1; then
  pip uninstall -y paddlepaddle >/dev/null 2>&1 || true
  pip install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
else
  pip uninstall -y paddlepaddle-gpu >/dev/null 2>&1 || true
  pip install paddlepaddle==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
fi

pip install paddleocr==3.7.0 pyarrow pillow
