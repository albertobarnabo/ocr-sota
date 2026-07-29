#!/usr/bin/env bash
# glm_ocr adapter installer -- idempotent, own venv at .venv.
#
# zai-org/GLM-OCR: ~1.3B (CogViT encoder + GLM-0.5B decoder), single 2.47 GB
# safetensors, MIT. Natively in transformers as model_type glm_ocr. NO
# flash-attn needed. VERSION RISK per spec: GLM-OCR landed on transformers
# main first; if GlmOcrForConditionalGeneration is missing from the installed
# release, fall back to installing transformers from source (handled below).
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
pip install "transformers>=5.0" accelerate pillow pyarrow

# Fallback: source install only if the release lacks the GLM-OCR class.
python -c "from transformers import GlmOcrForConditionalGeneration" 2>/dev/null \
  || pip install "git+https://github.com/huggingface/transformers.git"
