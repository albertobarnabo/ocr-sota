#!/usr/bin/env bash
# doctr adapter installer -- idempotent, own venv at .venv.
#
# Install the [torch] extra: a legacy TF backend also exists, but PyTorch is
# the default and the one we want. python-doctr 1.0.1 requires Python >= 3.10.
# Default models (db_resnet50 ~95 MB + crnn_vgg16_bn ~60 MB) auto-download on
# first use.
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
pip install "python-doctr[torch]==1.0.1" pyarrow pillow
