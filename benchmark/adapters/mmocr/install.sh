#!/usr/bin/env bash
# mmocr adapter installer -- idempotent, own venv at .venv.
#
# EXPECTED FAILURE (recorded result, see benchmark/adapters/EXPECTED_FAILURES.md):
# mmocr 1.0.1 is the final release (2023-07-04, effectively unmaintained) and
# hard-asserts mmcv>=2.0.0rc4,<2.1.0 + mmdet>=3.0.0rc5,<3.2.0. Prebuilt mmcv
# wheels for that 2.0.x range only exist against torch <=2.1 -- the OpenMMLab
# wheel index stops at torch2.4.0 (cu118/torch2.5.0+ return HTTP 404) and the
# torch2.1/torch2.4 indexes only serve mmcv 2.1.0/2.2.0, both rejected by
# mmocr's own version assertion. Building mmcv 2.0.x from source against a
# current torch also fails. This is the nominal (legacy) recipe; on the
# current (2026) stack it is expected to fail, and that install failure IS
# the timeboxed benchmark result for this engine.
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
pip install pyarrow pillow
pip install -U openmim
mim install mmengine
mim install "mmcv>=2.0.0rc4,<2.1.0"
mim install "mmdet>=3.0.0rc5,<3.2.0"
mim install mmocr==1.0.1
