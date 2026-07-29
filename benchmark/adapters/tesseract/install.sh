#!/usr/bin/env bash
# tesseract adapter installer -- idempotent, own venv at .venv.
#
# pytesseract is only a thin wrapper: it shells out to the `tesseract` binary,
# which MUST be installed system-wide (Ubuntu 22.04 ships Tesseract 5.x, LSTM
# engine, default OEM 3) and be on PATH. Language packs must cover the dataset
# locales (US/UK/DE/IT/FR): eng, deu, ita, fra.
set -euo pipefail
cd "$(dirname "$0")"

if command -v apt-get >/dev/null 2>&1; then
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
  $SUDO apt-get update -y || true
  $SUDO apt-get install -y \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-ita tesseract-ocr-fra
fi

if ! command -v tesseract >/dev/null 2>&1; then
  echo "WARNING: no 'tesseract' binary on PATH; predict.py will fail until it is installed." >&2
fi

[ -x .venv/bin/python ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install pytesseract==0.3.13 pillow pyarrow
