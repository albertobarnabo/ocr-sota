#!/usr/bin/env bash
# pix2text adapter installer -- idempotent, own venv at .venv.
#
# pix2text 1.1.6 (2026-02-07) pulls cnocr, cnstd, torch. It is a full
# document->Markdown pipeline (layout+table+formula+text) but we only use the
# pure-OCR path (recognize_text), which uses CnOCR for en/zh and EasyOCR for
# other Latin langs -- those text-OCR models (~0.1-0.3 GB) download on first
# call.
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
pip install pix2text==1.1.6 pyarrow pillow
