#!/usr/bin/env python3
"""Score OCR predictions against the synthetic-receipts-ocr eval shard.

Usage:
    python3 score.py --preds preds.jsonl --parquet eval-0000.parquet \
        --model tesseract --track photo [--device cuda] [--out results/tesseract.photo.json]

Input preds.jsonl: one JSON object per line, {"id": ..., "text": ..., "sec": ...}.
Ground truth comes from the parquet's `full_text` column, joined on `id`.

Text normalization "v1" (applied identically to prediction and ground truth):
    1. Unicode NFC
    2. uppercase
    3. per line: runs of spaces/tabs collapsed to one space, line stripped
    4. empty lines dropped
    5. lines joined with a single newline

Metrics (all micro-averaged over the scored rows):
    cer               primary: character error rate with newlines treated as
                      spaces, so reading-order-preserving models are not
                      penalized for line-break placement
    cer_newline_kept  secondary: same but newlines kept as characters
    wer               word error rate over whitespace-split tokens
    word_f1 / word_precision / word_recall
                      order-independent bag-of-words (multiset) overlap
    per_locale_cer    primary cer split by the parquet's `locale` column
    mean_sec_per_image  mean of the per-image `sec` field in preds.jsonl

Dependencies: stdlib + pyarrow (only imported when reading the parquet).
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

NORMALIZATION_VERSION = "v1"

_WS_RUN = re.compile(r"[ \t]+")


def normalize(text):
    """Apply normalization v1 (see module docstring) to a string."""
    if text is None:
        text = ""
    text = unicodedata.normalize("NFC", text)
    text = text.upper()
    lines = []
    for line in text.splitlines():
        line = _WS_RUN.sub(" ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def newline_as_space(normalized_text):
    """Variant used for the primary CER: newlines become single spaces."""
    return normalized_text.replace("\n", " ")


def levenshtein(a, b):
    """Plain edit distance between two sequences (str or list of tokens).

    O(len(a)*len(b)) time, two-row memory. Common prefix/suffix are stripped
    first, which is a large win on near-identical texts.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # strip common prefix
    lo = 0
    hi = min(len(a), len(b))
    while lo < hi and a[lo] == b[lo]:
        lo += 1
    a, b = a[lo:], b[lo:]
    # strip common suffix
    k = 0
    m = min(len(a), len(b))
    while k < m and a[len(a) - 1 - k] == b[len(b) - 1 - k]:
        k += 1
    if k:
        a, b = a[: len(a) - k], b[: len(b) - k]
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(b) > len(a):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def _ratio(num, den):
    return (num / den) if den else 0.0


def score_rows(rows):
    """Compute all metrics for a list of rows.

    Each row is a dict with keys: id, pred (raw predicted text), ref (raw
    ground-truth text), locale, sec. Returns a metrics dict; every rate is
    micro-averaged (summed numerators / summed denominators).
    """
    d_space = 0          # char edits, newline-as-space variant (primary)
    n_space = 0          # ref chars, newline-as-space variant
    d_nl = 0             # char edits, newline-kept variant
    n_nl = 0             # ref chars, newline-kept variant
    d_word = 0           # word edits
    n_word = 0           # ref words
    tp = 0               # bag-of-words true positives
    n_pred_words = 0
    sec_sum = 0.0
    n_empty = 0
    loc_d = {}           # locale -> char edits (primary variant)
    loc_n = {}           # locale -> ref chars (primary variant)
    loc_rows = {}        # locale -> row count

    for row in rows:
        pred_n = normalize(row["pred"])
        ref_n = normalize(row["ref"])
        if not pred_n:
            n_empty += 1

        pred_s = newline_as_space(pred_n)
        ref_s = newline_as_space(ref_n)
        d = levenshtein(pred_s, ref_s)
        d_space += d
        n_space += len(ref_s)

        d_nl += levenshtein(pred_n, ref_n)
        n_nl += len(ref_n)

        pred_w = pred_n.split()
        ref_w = ref_n.split()
        d_word += levenshtein(pred_w, ref_w)
        n_word += len(ref_w)
        tp += sum((Counter(pred_w) & Counter(ref_w)).values())
        n_pred_words += len(pred_w)

        sec_sum += float(row.get("sec") or 0.0)

        loc = row.get("locale") or "unknown"
        loc_d[loc] = loc_d.get(loc, 0) + d
        loc_n[loc] = loc_n.get(loc, 0) + len(ref_s)
        loc_rows[loc] = loc_rows.get(loc, 0) + 1

    precision = _ratio(tp, n_pred_words)
    recall = _ratio(tp, n_word)
    f1 = _ratio(2 * precision * recall, precision + recall)

    n_rows = len(rows)
    return {
        "normalization_version": NORMALIZATION_VERSION,
        "n_rows": n_rows,
        "n_empty_preds": n_empty,
        "cer": _ratio(d_space, n_space),
        "cer_newline_kept": _ratio(d_nl, n_nl),
        "wer": _ratio(d_word, n_word),
        "word_f1": f1,
        "word_precision": precision,
        "word_recall": recall,
        "per_locale_cer": {loc: _ratio(loc_d[loc], loc_n[loc]) for loc in sorted(loc_d)},
        "per_locale_n": {loc: loc_rows[loc] for loc in sorted(loc_rows)},
        "mean_sec_per_image": _ratio(sec_sum, n_rows),
    }


def load_refs(parquet_path):
    """Read id -> (full_text, locale) from the eval parquet."""
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path, columns=["id", "full_text", "locale"])
    ids = table.column("id").to_pylist()
    texts = table.column("full_text").to_pylist()
    locales = table.column("locale").to_pylist()
    return {i: (t, l) for i, t, l in zip(ids, texts, locales)}


def load_preds(preds_path):
    """Read preds.jsonl; on duplicate ids the last line wins."""
    preds = {}
    order = []
    with open(preds_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError as e:
                raise SystemExit(f"{preds_path}:{lineno}: bad JSON line: {e}")
            if "id" not in obj:
                raise SystemExit(f"{preds_path}:{lineno}: missing 'id'")
            if obj["id"] not in preds:
                order.append(obj["id"])
            preds[obj["id"]] = obj
    return [preds[i] for i in order]


def _round_floats(obj, ndigits=6):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, ndigits) for v in obj]
    return obj


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preds", required=True, help="preds.jsonl from an adapter")
    ap.add_argument("--parquet", required=True, help="eval shard parquet")
    ap.add_argument("--model", required=True, help="adapter/model name")
    ap.add_argument("--track", required=True, choices=["photo", "clean"])
    ap.add_argument("--device", default=None, help="device the preds were made on")
    ap.add_argument("--out", default=None,
                    help="output json path (default: results/<model>.<track>.json)")
    args = ap.parse_args(argv)

    refs = load_refs(args.parquet)
    preds = load_preds(args.preds)
    if not preds:
        raise SystemExit(f"no predictions found in {args.preds}")

    rows = []
    for p in preds:
        if p["id"] not in refs:
            raise SystemExit(f"prediction id {p['id']!r} not found in {args.parquet}")
        ref_text, locale = refs[p["id"]]
        rows.append({
            "id": p["id"],
            "pred": p.get("text", ""),
            "ref": ref_text,
            "locale": locale,
            "sec": p.get("sec", 0.0),
        })

    metrics = score_rows(rows)
    result = {"model": args.model, "track": args.track}
    if args.device:
        result["device"] = args.device
    result.update(metrics)
    result = _round_floats(result)

    out = args.out
    if out is None:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "results", f"{args.model}.{args.track}.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=False)
        f.write("\n")

    print(json.dumps(result, indent=2))
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
