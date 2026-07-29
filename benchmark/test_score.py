#!/usr/bin/env python3
"""Unit tests for score.py. Run: python3 test_score.py  (stdlib only, no pyarrow needed)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from score import levenshtein, newline_as_space, normalize, score_rows


def approx(a, b, eps=1e-9):
    return abs(a - b) < eps


def row(pred, ref, locale="US", sec=0.0):
    return {"id": "x", "pred": pred, "ref": ref, "locale": locale, "sec": sec}


# ---------------------------------------------------------------- levenshtein
assert levenshtein("", "") == 0
assert levenshtein("ABC", "") == 3
assert levenshtein("", "ABC") == 3
assert levenshtein("ABC", "ABC") == 0
assert levenshtein("KITTEN", "SITTING") == 3
assert levenshtein("FLAW", "LAWN") == 2
assert levenshtein("ABA", "ABBA") == 1          # exercises prefix+suffix trim
assert levenshtein("AA", "AAA") == 1
assert levenshtein(["A", "B"], ["B"]) == 1      # works on token lists too
assert levenshtein(["THE", "CAT"], ["THE", "CAT", "SAT"]) == 1

# -------------------------------------------------------------- normalization
# mixed case + double spaces + tab + NFC (e + combining acute -> E-acute)
# + empty-line dropping + per-line strip
raw = "Café  au\tLait\n\n   x  "
assert normalize(raw) == "CAFÉ AU LAIT\nX"
assert normalize("a\r\nb\rc") == "A\nB\nC"       # CRLF / CR handled as line breaks
assert normalize("") == ""
assert normalize(None) == ""
assert newline_as_space("A\nB") == "A B"

# ------------------------------------------------- CER tiny case 1: basic sub
m = score_rows([row("AXC", "ABC")])
assert approx(m["cer"], 1 / 3), m["cer"]                 # 1 edit / 3 ref chars
assert approx(m["cer_newline_kept"], 1 / 3)
assert approx(m["wer"], 1.0)                              # AXC vs ABC: 1 sub / 1 word
assert approx(m["word_f1"], 0.0)
assert m["n_rows"] == 1 and m["n_empty_preds"] == 0

# ---------------- CER tiny case 2: newline placement forgiven by primary CER
# Same characters, different line-break position: primary CER (newline-as-
# space) must be 0, while the newline-kept variant sees 2 substitutions.
m = score_rows([row("HELLO\nWORLD FOO", "HELLO WORLD\nFOO")])
assert approx(m["cer"], 0.0), m["cer"]
assert approx(m["cer_newline_kept"], 2 / 15), m["cer_newline_kept"]
assert approx(m["wer"], 0.0)                              # tokens identical
assert approx(m["word_f1"], 1.0)

# --------------------------- CER tiny case 3: empty prediction scores CER 1.0
m = score_rows([row("", "AB\nCD")])
assert approx(m["cer"], 1.0), m["cer"]                    # 5 edits / 5 ref chars ("AB CD")
assert approx(m["wer"], 1.0)
assert approx(m["word_f1"], 0.0)
assert m["n_empty_preds"] == 1

# ------------------------------------------------------------ word-F1 by hand
# ref bag {A:1, B:2, C:1}, pred bag {B:1, C:1, D:1} -> overlap 2
# precision 2/3, recall 2/4, F1 = 2*(2/3)*(1/2) / ((2/3)+(1/2)) = 4/7
m = score_rows([row("B C D", "A B B C")])
assert approx(m["word_precision"], 2 / 3)
assert approx(m["word_recall"], 1 / 2)
assert approx(m["word_f1"], 4 / 7), m["word_f1"]

# ------------------------------------------- WER by hand (one dropped word)
m = score_rows([row("THE CAT", "THE CAT SAT")])
assert approx(m["wer"], 1 / 3), m["wer"]

# ----------------------- normalization applied to BOTH prediction and truth
m = score_rows([row("  aBc  ", "ABC")])
assert approx(m["cer"], 0.0)

# ------------------------------------- micro aggregation across several rows
# row 1: 1 edit / 3 chars, row 2: 0 edits / 3 chars -> micro CER 1/6
m = score_rows([row("AXC", "ABC", locale="US", sec=2.0),
                row("ABC", "ABC", locale="DE", sec=4.0)])
assert approx(m["cer"], 1 / 6), m["cer"]
assert approx(m["per_locale_cer"]["US"], 1 / 3)
assert approx(m["per_locale_cer"]["DE"], 0.0)
assert m["per_locale_n"] == {"DE": 1, "US": 1}
assert approx(m["mean_sec_per_image"], 3.0)
assert m["normalization_version"] == "v1"

print("all tests passed")
