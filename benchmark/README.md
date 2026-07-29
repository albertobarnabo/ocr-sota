# Receipt OCR benchmark

The tables in the main README rank projects by GitHub stars, which says nothing
about accuracy. This directory measures it: every model in the roster below is
run, unmodified, over the same 500 receipts, and the results are rendered into
the `## Receipt OCR benchmark` section of the main README by
[`render_results.py`](render_results.py).

## Dataset

[albertobarnabo/synthetic-receipts-ocr](https://huggingface.co/datasets/albertobarnabo/synthetic-receipts-ocr)
— 32,000 synthetic thermal-printer receipts in five locales (US/UK/DE/IT/FR)
with full ground-truth text, word boxes, and key fields. The eval split has
2,000 receipts whose fonts, vocabulary, and merchants never appear in the
training split.

The benchmark subset is fixed: the **first 500 rows of the eval shard**
(`data/eval-0000.parquet`, ids `eval-000000`–`eval-000499`). The columns used
are `id`, `image_photo` (PNG-rendered receipt photographed at an angle with
degradations), `image_clean` (flat render), `full_text` (ground truth), and
`locale`.

## Tracks

- **photo** (`image_photo`) — perspective photo with lighting, blur, and other
  degradations. The headline number.
- **clean** (`image_clean`) — flat, undegraded render. The gap between clean
  and photo CER is each model's robustness delta.

## Metrics

All metrics are micro-averaged over the 500 rows and computed by
[`score.py`](score.py):

- **CER** (primary; models are ranked by photo-track CER, lower is better).
  For the primary CER, newlines are treated as spaces so a model that preserves
  reading order is not penalized for where it breaks lines. A secondary
  `cer_newline_kept` keeps them as characters.
- **WER** over whitespace-split tokens.
- **word-F1** (plus precision/recall) — order-independent bag-of-words
  (multiset) overlap, which rewards getting the words right even when reading
  order differs.
- **per-locale CER** — the primary CER split by the `locale` column.

### Text normalization (v1)

Applied identically to prediction and ground truth before any metric:

1. Unicode NFC
2. uppercase
3. per line: runs of spaces/tabs collapsed to one space, line stripped
4. empty lines dropped
5. lines joined with a single newline

## Hardware protocol

All numbers come from a single rented box (Vast.ai, one RTX 4090):

- **GPU timing** — mean wall seconds per image over all 500, per track,
  reported by each adapter and averaged by `score.py`.
- **CPU probe** — the photo track over the first 10 rows with `--device cpu`,
  timeboxed at 15 minutes. Ten images are enough to place a model against
  thresholds an order of magnitude apart (2 s vs 60 s per receipt), and a
  timeout is itself the **GPU required** verdict.
- **Peak VRAM** — `nvidia-smi` `memory.used` polled every 2 s during the cuda
  runs, written to `results/<model>.vram.txt`.
- **Installs** are timeboxed at 30 minutes; an install failure is itself a
  recorded result (see [`adapters/EXPECTED_FAILURES.md`](adapters/EXPECTED_FAILURES.md)),
  rendered as an "install failed" row, not silently dropped.

Verdict thresholds (fixed before measuring):

| Verdict | Condition |
| :--- | :--- |
| CPU-friendly | CPU probe under 2 s/receipt |
| GPU recommended | CPU works but takes 2 s/receipt or more |
| GPU required | cannot run on CPU, or exceeds 60 s/receipt there |

## Roster

Measured end-to-end: tesseract, paddleocr, easyocr, doctr, surya, got_ocr2,
dots_ocr, olmocr, glm_ocr, unlimited_ocr, pix2text, and mmocr (timeboxed —
its install is expected to fail on a current torch stack, and that outcome is
recorded).

Annex: **trocr_lines** — TrOCR is a line-level recognition model, so it runs
recognition-only over ground-truth line crops (line membership from the clean
word boxes, crop coordinates from the boxes matching the rendered image). Its
row is footnoted, sorts after the full-page models, and is not directly
comparable to them: besides seeing ground-truth regions, its CER carries a
fixed floor of roughly 27% of reference characters from the dash separator
rules in `full_text`, which are not word boxes and so can never appear in a
line-crop transcription.

Deliberately not benchmarked (wrappers whose numbers would measure their
backend, plus Donut, which emits structured JSON rather than a transcription):
listed with reasons in [`excluded.yaml`](excluded.yaml) and rendered into the
main README.

## Layout

```
benchmark/
  adapters/<name>/install.sh   # per-model venv, idempotent
  adapters/<name>/predict.py   # shared CLI (see contract below)
  run_model.sh                 # one adapter + one track: install, predict, score
  vast/setup.sh                # one-time box setup + eval-shard download
  vast/run_all.sh              # full roster with timeboxes and VRAM polling
  score.py                     # metrics (stdlib + pyarrow)
  render_results.py            # results/ + excluded.yaml -> main README section
  excluded.yaml                # models deliberately not benchmarked, with reasons
  preds/  logs/  results/      # run artifacts (results/ travels back home)
```

## Adapter contract

Every adapter is a directory under `adapters/` with exactly two entry points:

**`install.sh`** — creates the adapter's own venv at `.venv` inside the
adapter directory with `python3 -m venv` and pip-installs everything the model
needs, including torch where required. Idempotent: safe to re-run.

**`predict.py`** — shared CLI:

```
.venv/bin/python predict.py --parquet PATH --rows A:B \
    --image-col image_photo|image_clean --out preds.jsonl --device cuda|cpu
```

Requirements:

- loads the model **once**, then loops over rows `A:B`
- writes one JSON line per row: `{"id": ..., "text": ..., "sec": ...}` where
  `sec` is the per-image wall time
- never crashes on a single bad image — log it and emit `""` as the text for
  that id
- prints `PROGRESS <done>/<total>` to stdout every 10 images (the runner tails
  this into a progress bar)

## Running

One model, one track (installs on first use, resume-safe, re-scores existing
complete predictions):

```bash
bash benchmark/run_model.sh tesseract photo --device cuda --rows 0:500
```

Full roster with timeboxes and VRAM polling (per-model failures are recorded
and skipped, never fatal):

```bash
tmux new -s bench 'bash benchmark/vast/run_all.sh'
```

## Reproducing on a rented GPU box

Five commands, start to rendered table (1–3 on the box, 4–5 at home):

```bash
git clone https://github.com/albertobarnabo/ocr-sota.git && cd ocr-sota   # 1  on the box
bash benchmark/vast/setup.sh                                              # 2  deps + eval shard
tmux new -s bench 'bash benchmark/vast/run_all.sh'                        # 3  full roster (hours)
rsync -a box:ocr-sota/benchmark/results/ benchmark/results/               # 4  copy results home
python3 benchmark/render_results.py                                       # 5  render into README.md
```

`score.py` needs only stdlib + pyarrow; `render_results.py` needs stdlib +
PyYAML. Neither touches the network.

## Limitations

The data is synthetic and thermal-receipt-shaped only — results say nothing
about handwriting, dense documents, tables, or natural scenes, and synthetic
degradations are at best an approximation of real camera noise. Every model
runs with out-of-the-box defaults; no per-task tuning, prompt engineering, or
fine-tuning, which understates what a tuned deployment would achieve —
uniformly, but not necessarily fairly for models that expect task prompts.
Timings are from a single run on a single box (one driver stack, one CPU), not
averaged over repeats, so treat small speed differences as noise. The TrOCR
annex row uses ground-truth line crops and is not comparable to the full-page
rows.
