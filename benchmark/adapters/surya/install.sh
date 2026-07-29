#!/usr/bin/env bash
# surya adapter installer -- idempotent, own venv at .venv.
#
# PINNED to surya-ocr==0.17.1, the last v1 release (2026-01-30), on purpose:
# current 0.20+ ("Surya 2") is a 650M VLM that is NOT run in-process -- it
# auto-spawns a vllm server (GPU, inside Docker with the NVIDIA Container
# Toolkit) or a llama.cpp llama-server (CPU), which breaks the one-venv,
# load-once-loop-rows adapter contract. v1 runs directly in PyTorch.
# If Surya 2 numbers are wanted later, that adapter must stand up
# vllm/llama.cpp -- budget for it separately.
#
# LICENSE NOTE: code is Apache-2.0 but the MODEL WEIGHTS are a modified
# AI-Pubs OpenRAIL-M (free for research/personal/startups under $5M) --
# NOT plain permissive; flagged for the published benchmark table.
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
pip install surya-ocr==0.17.1 pyarrow pillow
