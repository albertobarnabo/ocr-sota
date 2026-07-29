#!/usr/bin/env python3
"""TrOCR annex adapter -- RECOGNITION-ONLY track, not comparable to full-page rows.

TrOCR (microsoft/trocr-base-printed) is a LINE-LEVEL model with NO detector:
a full receipt yields garbage. This annex therefore measures recognition in
isolation on ground-truth line regions. Line MEMBERSHIP always comes from the
clean word boxes (`words`, axis-aligned -- grouping the homography-warped
`words_photo` boxes directly is geometrically ill-posed, see group_lines);
crop COORDINATES come from the boxes matching the rendered image (words_photo
for image_photo, words for image_clean; the two are parallel arrays, verified
over the full eval shard). Each line region is cropped with a 4px margin,
recognized, and line texts are reassembled in reading order. Line crops are
BATCHED per generate() call (autoregressive decode is slow, esp. on CPU).
Do NOT use device_map='auto'. Printed variants are English-only, so DE/IT/FR
locales are expected to degrade -- that is part of the recorded result.

Scoring caveat (documented in the results footnote): full_text contains dash
separator rules that are not word boxes, so no line-crop pipeline can emit
them; they are ~27% of reference characters, a fixed CER floor for this row.
"""
import argparse
import io
import json
import sys
import time

MODEL = "microsoft/trocr-base-printed"
MARGIN = 4
BATCH = 16


def group_lines(words):
    """Group word boxes into lines; sort each line's words by x.

    MUST be fed the CLEAN (axis-aligned) boxes: on the photo track the
    homography tilt makes warped y-intervals of the same visual line stop
    overlapping across the receipt width while adjacent lines start to,
    so no threshold on the warped boxes groups correctly (verified on the
    eval shard: a union-interval merge corrupts ~44% of photo receipts).
    Grouping on clean geometry reproduces the ground-truth line structure
    on all 500 benchmark rows; the caller then crops via the parallel
    warped boxes. Single-link: words join when their y-intervals overlap
    by more than half the smaller height.
    """
    n = len(words)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            a, b = words[i], words[j]
            overlap = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            if overlap > 0.5 * min(a["y1"] - a["y0"], b["y1"] - b["y0"]):
                parent[find(i)] = find(j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    lines = []
    for idxs in groups.values():
        idxs.sort(key=lambda i: words[i]["x0"])
        lines.append(idxs)
    lines.sort(key=lambda idxs: sum(
        (words[i]["y0"] + words[i]["y1"]) / 2.0 for i in idxs) / len(idxs))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--rows", required=True, help="half-open row range A:B")
    ap.add_argument("--image-col", default="image_photo",
                    choices=["image_photo", "image_clean"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    args = ap.parse_args()
    a, b = (int(x) for x in args.rows.split(":"))

    import pyarrow.parquet as pq
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    # Crop boxes must match the rendered image (words_photo carries the
    # homography-warped coordinates for image_photo); line membership is
    # always decided on the clean `words` geometry.
    crop_col = "words_photo" if args.image_col == "image_photo" else "words"
    cols = ["id", args.image_col, "words"]
    if crop_col != "words":
        cols.append(crop_col)
    table = pq.read_table(args.parquet, columns=cols).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    clean_jsons = table.column("words").to_pylist()
    crop_jsons = table.column(crop_col).to_pylist()
    total = len(ids)

    proc = TrOCRProcessor.from_pretrained(MODEL)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL).to(args.device).eval()

    def recognize(img, clean_words, crop_words):
        if len(clean_words) != len(crop_words):  # parallel-array safety net
            clean_words = crop_words
        lines = group_lines(clean_words)
        if not lines:
            return ""
        crops = []
        for idxs in lines:
            ws = [crop_words[i] for i in idxs]
            x0 = min(w["x0"] for w in ws) - MARGIN
            x1 = max(w["x1"] for w in ws) + MARGIN
            y0 = min(w["y0"] for w in ws) - MARGIN
            y1 = max(w["y1"] for w in ws) + MARGIN
            # Clamp into the image and force >=1px extent so a degenerate box
            # can never produce an inverted crop (PIL raises on those).
            left = max(0, min(int(x0), img.width - 1))
            top = max(0, min(int(y0), img.height - 1))
            right = min(img.width, max(int(x1) + 1, left + 1))
            bottom = min(img.height, max(int(y1) + 1, top + 1))
            crops.append(img.crop((left, top, right, bottom)))
        texts = []
        for i in range(0, len(crops), BATCH):
            pv = proc(images=crops[i:i + BATCH], return_tensors="pt").pixel_values.to(args.device)
            gen = model.generate(pv, max_new_tokens=64)
            texts.extend(proc.batch_decode(gen, skip_special_tokens=True))
        return "\n".join(t.strip() for t in texts)  # reassembled in reading order

    try:  # warmup on row A, untimed
        recognize(Image.open(io.BytesIO(blobs[0])).convert("RGB"),
                  json.loads(clean_jsons[0]), json.loads(crop_jsons[0]))
    except Exception as e:
        print(f"WARN warmup: {type(e).__name__}: {e}", file=sys.stderr)

    done = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for rid, blob, cj, wj in zip(ids, blobs, clean_jsons, crop_jsons):
            try:
                img = Image.open(io.BytesIO(blob)).convert("RGB")
                clean_words = json.loads(cj)
                crop_words = json.loads(wj)
            except Exception as e:
                print(f"WARN {rid}: decode: {type(e).__name__}: {e}", file=sys.stderr)
                out.write(json.dumps({"id": rid, "text": "", "sec": 0.0}) + "\n")
                done += 1
                continue
            t0 = time.perf_counter()
            try:
                text = recognize(img, clean_words, crop_words)
            except Exception as e:
                print(f"WARN {rid}: {type(e).__name__}: {e}", file=sys.stderr)
                text = ""
            sec = time.perf_counter() - t0
            out.write(json.dumps({"id": rid, "text": text, "sec": round(sec, 4)},
                                 ensure_ascii=False) + "\n")
            done += 1
            if done % 10 == 0 or done == total:
                print(f"PROGRESS {done}/{total}", flush=True)


if __name__ == "__main__":
    main()
