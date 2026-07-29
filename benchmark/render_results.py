#!/usr/bin/env python3
"""Render the receipt-OCR benchmark section of README.md from measured results.

Reads every ``benchmark/results/*.json`` (written by ``benchmark/score.py``)
plus the hand-written ``benchmark/excluded.yaml`` and rewrites the block
between the ``<!-- BENCHMARK:START -->`` and ``<!-- BENCHMARK:END -->``
markers in README.md. With no result files it still renders the methodology
and the excluded table, so the section is valid before the first measurement
run lands.

This script is deliberately independent of scripts/update_readme.py: that one
talks to the GitHub API and aborts on any fetch failure, while this one is
fully offline and must always succeed.

Result files are one JSON object per (model, track, device) run, written by
run_model.sh as ``<model>.<track>.json`` (cuda) or ``<model>.<track>.cpu.json``
(CPU probe). Grouping here uses the "model"/"track"/"device" keys inside each
file, not the filename:

    {
      "model": "tesseract",
      "track": "photo",              # "photo" | "clean"
      "device": "cuda",              # "cuda" | "cpu"
      "normalization_version": "v1",
      "n_rows": 500,
      "n_empty_preds": 0,
      "cer": 0.0342,                 # primary: newline-as-space variant
      "cer_newline_kept": 0.0351,
      "wer": 0.081,
      "word_f1": 0.912,
      "word_precision": 0.92,
      "word_recall": 0.90,
      "per_locale_cer": {"DE": ..., "FR": ..., "IT": ..., "UK": ..., "US": ...},
      "per_locale_n": {...},
      "mean_sec_per_image": 0.41
    }

Files whose model name starts with "_" (dev/smoke runs) are ignored. Rows are
merged per model: quality metrics come from the photo/cuda file when present
(photo/cpu otherwise), the clean-track CER from the clean file, GPU and CPU
seconds per image from the cuda and cpu photo files respectively. Peak VRAM is
read from ``results/<model>.vram.txt`` (written by vast/run_all.sh's
nvidia-smi poll as ``peak_mib=N baseline_mib=M``). The verdict is derived from
the CPU probe using the fixed thresholds documented in benchmark/README.md
unless a "verdict" key is present in one of the model's result files. A
``results/<model>.install_failed.txt`` marker (written by vast/run_all.sh when
a timeboxed install fails) renders as a row of dashes with verdict "install
failed" — a recorded outcome, not a gap.

Usage:
    python3 benchmark/render_results.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "benchmark" / "results"
EXCLUDED = ROOT / "benchmark" / "excluded.yaml"
README = ROOT / "README.md"

START = "<!-- BENCHMARK:START -->"
END = "<!-- BENCHMARK:END -->"

DATASET_URL = "https://huggingface.co/datasets/albertobarnabo/synthetic-receipts-ocr"

# Adapter name -> display name for the results table.
DISPLAY_NAMES = {
    "tesseract": "Tesseract",
    "paddleocr": "PaddleOCR",
    "easyocr": "EasyOCR",
    "doctr": "docTR",
    "surya": "Surya",
    "got_ocr2": "GOT-OCR2.0",
    "dots_ocr": "dots.ocr",
    "olmocr": "olmOCR",
    "glm_ocr": "GLM-OCR",
    "unlimited_ocr": "Unlimited-OCR",
    "pix2text": "Pix2Text",
    "mmocr": "MMOCR",
    "trocr_lines": "TrOCR",
}

# Standing footnotes for models whose numbers need a caveat.
NOTES = {
    "trocr_lines": "annex track — recognition-only on ground-truth line crops "
    "(TrOCR is a line-level model), not directly comparable to full-page rows. "
    "Its CER also carries a fixed floor of roughly 27% of reference characters: "
    "the ground truth includes dash separator rules that are not word boxes, so "
    "no line-crop pipeline can emit them.",
}

# CPU-probe thresholds (seconds per receipt) for the derived verdict.
CPU_FRIENDLY_MAX = 2.0
CPU_USABLE_MAX = 60.0

METHODOLOGY = f"""\
How do the models above actually compare? We ran the ones that can transcribe a
receipt end-to-end over the same 500 held-out receipts (ids
`eval-000000`–`eval-000499`) from
[synthetic-receipts-ocr]({DATASET_URL}) — synthetic
thermal-printer receipts in five locales (US/UK/DE/IT/FR) whose fonts,
vocabulary, and merchants never appear in the training split. Each model runs
twice: on the **photo** track (perspective photo with degradations — the
headline number) and on the **clean** track (flat render — the robustness
delta). The primary metric is character error rate on the photo track, lower is
better; word error rate and an order-independent word-F1 are also computed, and
per-locale CER is recorded in the result files. Predictions and ground truth
are normalized identically before scoring (Unicode NFC, uppercase, lines
stripped, whitespace runs collapsed, empty lines dropped), and the primary CER
treats newlines as spaces so models are not penalized for line-break placement.
Timings come from a single rented RTX 4090 box: GPU seconds per image over all
500, a CPU probe over the first 10, and peak VRAM polled from `nvidia-smi`.
Verdicts follow fixed thresholds: **CPU-friendly** under 2 s/receipt on CPU,
**GPU recommended** when CPU works but takes 2 s or more, **GPU required** when
a model cannot run on CPU or exceeds 60 s/receipt there."""

REPRODUCE = (
    "Full protocol, adapter contract, and reproduction steps: "
    "[benchmark/README.md](benchmark/README.md)."
)


def fmt_pct(x) -> str:
    """A fraction as a percentage with two decimals, or an em dash."""
    return f"{x * 100:.2f}%" if isinstance(x, (int, float)) else "—"


def fmt_sec(x) -> str:
    return f"{x:.2f}" if isinstance(x, (int, float)) else "—"


def fmt_vram(mb) -> str:
    if not isinstance(mb, (int, float)):
        return "—"
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def load_runs() -> dict[str, dict[tuple[str, str], dict]]:
    """All result files grouped as model -> {(track, device): record}."""
    runs: dict[str, dict[tuple[str, str], dict]] = {}
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            rec = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            print(f"  ! skipping {path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(rec, dict) or "model" not in rec:
            print(f"  ! skipping {path.name}: no 'model' key", file=sys.stderr)
            continue
        model = str(rec["model"])
        if model.startswith("_"):  # dev/smoke run, not a leaderboard entry
            continue
        key = (str(rec.get("track", "")), str(rec.get("device", "")))
        runs.setdefault(model, {})[key] = rec
    return runs


def load_vram_mb(model: str):
    """Peak VRAM in MiB from results/<model>.vram.txt, or None."""
    path = RESULTS_DIR / f"{model}.vram.txt"
    if not path.exists():
        return None
    for token in path.read_text().split():
        if token.startswith("peak_mib="):
            try:
                return int(token.split("=", 1)[1])
            except ValueError:
                return None
    return None


def load_install_failures(measured: set[str]) -> list[dict]:
    """A dashes-only row per results/<model>.install_failed.txt marker."""
    rows = []
    for path in sorted(RESULTS_DIR.glob("*.install_failed.txt")):
        model = path.name[: -len(".install_failed.txt")]
        if model.startswith("_") or model in measured:
            continue
        rows.append(
            {
                "model": model,
                "name": DISPLAY_NAMES.get(model, model),
                "note": "install failed on the benchmark box within the timebox "
                "(see benchmark/adapters/EXPECTED_FAILURES.md); recorded as an "
                "outcome, not a gap.",
                "photo_cer": None,
                "clean_cer": None,
                "word_f1": None,
                "gpu_sec": None,
                "cpu_sec": None,
                "vram_mb": None,
                "verdict": "install failed",
            }
        )
    return rows


def summarize(model: str, by_key: dict[tuple[str, str], dict]) -> dict:
    """Collapse a model's per-(track, device) records into one table row."""

    def pick(track: str) -> dict:
        return by_key.get((track, "cuda")) or by_key.get((track, "cpu")) or {}

    photo, clean = pick("photo"), pick("clean")
    gpu = (by_key.get(("photo", "cuda")) or {}).get("mean_sec_per_image")
    cpu = (by_key.get(("photo", "cpu")) or {}).get("mean_sec_per_image")

    vram = load_vram_mb(model)
    verdict = None
    for rec in by_key.values():
        vram = vram if vram is not None else rec.get("peak_vram_mb")
        verdict = verdict or rec.get("verdict")
    if not verdict:
        if isinstance(cpu, (int, float)):
            if cpu < CPU_FRIENDLY_MAX:
                verdict = "CPU-friendly"
            elif cpu <= CPU_USABLE_MAX:
                verdict = "GPU recommended"
            else:
                verdict = "GPU required"
        elif by_key:  # measured on GPU but no CPU probe survived
            verdict = "GPU required"

    return {
        "model": model,
        "name": DISPLAY_NAMES.get(model, model),
        "note": NOTES.get(model),
        "photo_cer": photo.get("cer"),
        "clean_cer": clean.get("cer"),
        "word_f1": photo.get("word_f1"),
        "gpu_sec": gpu,
        "cpu_sec": cpu,
        "vram_mb": vram,
        "verdict": verdict,
    }


def render_results_table(rows: list[dict]) -> list[str]:
    out = [
        "| Model | CER photo | CER clean | word-F1 | GPU s/img | CPU s/img | VRAM | Verdict |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]
    notes: list[tuple[str, str]] = []
    for r in rows:
        name = r["name"]
        if r["note"]:
            notes.append((name, r["note"]))
            name = f"{name}\\*"
        out.append(
            f"| {name} "
            f"| {fmt_pct(r['photo_cer'])} "
            f"| {fmt_pct(r['clean_cer'])} "
            f"| {fmt_pct(r['word_f1'])} "
            f"| {fmt_sec(r['gpu_sec'])} "
            f"| {fmt_sec(r['cpu_sec'])} "
            f"| {fmt_vram(r['vram_mb'])} "
            f"| {r['verdict'] or '—'} |"
        )
    for name, note in notes:
        out.append("")
        out.append(f"\\* {name}: {note}")
    return out


def render_excluded_table(excluded: list[dict]) -> list[str]:
    out = [
        "| Model | Why not benchmarked |",
        "| :--- | :--- |",
    ]
    for e in excluded:
        out.append(f"| {e['name']} | {e['reason']} |")
    return out


def render(rows: list[dict], excluded: list[dict]) -> str:
    out = ["## Receipt OCR benchmark", "", METHODOLOGY, ""]
    if rows:
        today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        out.append(
            f"Results (photo-track CER ascending; footnoted annex rows are "
            f"not comparable and listed after the full-page models; "
            f"rendered {today}):"
        )
        out.append("")
        out.extend(render_results_table(rows))
    else:
        out.append(
            "Measurements are pending — the results table will appear here "
            "after the first run."
        )
    if excluded:
        out += ["", "### Not benchmarked", ""]
        out.extend(render_excluded_table(excluded))
    out += ["", REPRODUCE]
    return "\n".join(out) + "\n"


def main() -> int:
    excluded = []
    if EXCLUDED.exists():
        excluded = yaml.safe_load(EXCLUDED.read_text()) or []
        for e in excluded:
            if "name" not in e or "reason" not in e:
                print(f"excluded.yaml entry missing name/reason: {e}", file=sys.stderr)
                return 1

    runs = load_runs()
    rows = [summarize(m, by_key) for m, by_key in runs.items()]
    rows += load_install_failures(measured=set(runs))
    # Photo-track CER ascending. Annex rows (NOTES) are not comparable to the
    # full-page rows, so they sort after them regardless of CER; rows without
    # a CER sink to the bottom.
    rows.sort(
        key=lambda r: (
            not isinstance(r["photo_cer"], (int, float)),
            r["model"] in NOTES,
            r["photo_cer"] or 0,
            r["name"].lower(),
        )
    )
    section = render(rows, excluded)

    readme = README.read_text()
    if START not in readme or END not in readme:
        print(f"Markers {START} / {END} not found in README.md", file=sys.stderr)
        return 1

    pre, post = readme.split(START)[0], readme.split(END)[1]
    README.write_text(f"{pre}{START}\n\n{section}\n{END}{post}")
    print(
        f"Wrote {README.relative_to(ROOT)} "
        f"({len(rows)} model(s), {len(excluded)} excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
