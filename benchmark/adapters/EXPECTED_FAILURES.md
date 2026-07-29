# Expected failures

Adapters listed here ship with their best-known install recipe, but the
install (or run) is expected to fail on the current stack. The box run
records the actual outcome either way; an install failure is itself a
recorded benchmark result for a timeboxed engine.

## mmocr — expected install failure (terminal dependency conflict)

mmocr 1.0.1 is the final release (2023-07-04; project effectively
unmaintained) and hard-asserts `mmcv>=2.0.0rc4,<2.1.0` and
`mmdet>=3.0.0rc5,<3.2.0`. Prebuilt mmcv wheels for that 2.0.x range only
exist against torch <= 2.1. Verified directly on the OpenMMLab wheel index:
`cu118/torch2.5.0`, `torch2.6.0`, `torch2.7.0` all return HTTP 404 (the
index stops at torch2.4.0), and the torch2.1.0/torch2.4.0 indexes only serve
mmcv 2.1.0/2.2.0 — both rejected by mmocr's own version assertion. Building
mmcv 2.0.x from source against a current torch also fails. The only working
setup is a fully separate legacy environment (torch 2.0/2.1 + CUDA 11.8 +
mmcv 2.0.1 + mmdet 3.1.0 + mmocr 1.0.1), which is fragile and outside the
shared adapter contract. Result to record: install failure (timeboxed).

## Watch list (measured rows, known risks — not expected failures)

- **unlimited_ocr**: weights are open and downloadable, so this is a
  measured row. Two verified risks: (1) the bespoke `model.infer()` defaults
  to `save_results=True` writing files to `output_path`; whether it ALSO
  returns the text string must be verified on the box — the adapter tries
  the return value first and falls back to reading the written file;
  (2) license is UNVERIFIED (one card scrape said MIT, but the repo ships a
  custom "License agreement" file + NOTICE) — confirm before publishing.
  flash-attn is not in the README deps but the DeepSeek-OCR-derived modeling
  imports it; the installer builds it, which can itself fail on mismatched
  torch/CUDA.
- **dots_ocr**: flash-attn is effectively required (custom vision path; sdpa
  fallback reported but unverified), so the flash-attn build is the risky
  install step.
- **glm_ocr**: GLM-OCR landed on transformers main first; if the pinned
  release lacks `GlmOcrForConditionalGeneration`, the installer falls back
  to a transformers source install.
- **trocr_lines**: the installer pins `transformers>=5.0` but predict.py
  uses the legacy `TrOCRProcessor` / `VisionEncoderDecoderModel` classes;
  whether the 5.x line still ships them is unverified off-box. If the import
  fails on the box, relax the pin to `transformers>=4.49,<5`.
