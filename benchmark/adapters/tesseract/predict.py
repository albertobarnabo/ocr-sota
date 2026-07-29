#!/usr/bin/env python3
"""Tesseract 5 adapter (via pytesseract) for the receipts OCR benchmark.

CPU-only engine: there is no GPU code path, ever, so this is the
CPU-friendliness baseline. --device is accepted for contract uniformity and
ignored. lang='eng' alone is the fair single-config choice over the mixed
Latin-script locales (multi-lang 'eng+deu+ita+fra' slows it and can hurt
accuracy). --psm 6 ("assume a single uniform block of text") tends to beat
the default --psm 3 on receipts. image_to_string preserves newlines (good
for the newline-as-space CER variant).
"""
import argparse
import io
import json
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--rows", required=True, help="half-open row range A:B")
    ap.add_argument("--image-col", default="image_photo",
                    choices=["image_photo", "image_clean"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu", choices=["cuda", "cpu"])  # ignored: CPU-only engine
    args = ap.parse_args()
    a, b = (int(x) for x in args.rows.split(":"))

    import pyarrow.parquet as pq
    import pytesseract
    from PIL import Image

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    CONFIG = "--oem 3 --psm 6"

    def recognize(img):
        return pytesseract.image_to_string(img, lang="eng", config=CONFIG)

    # One warmup inference on row A, excluded from timing.
    try:
        recognize(Image.open(io.BytesIO(blobs[0])).convert("RGB"))
    except Exception as e:
        print(f"WARN warmup: {type(e).__name__}: {e}", file=sys.stderr)

    done = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for rid, blob in zip(ids, blobs):
            try:
                img = Image.open(io.BytesIO(blob)).convert("RGB")
            except Exception as e:
                print(f"WARN {rid}: decode: {type(e).__name__}: {e}", file=sys.stderr)
                out.write(json.dumps({"id": rid, "text": "", "sec": 0.0}) + "\n")
                done += 1
                continue
            t0 = time.perf_counter()
            try:
                text = recognize(img)
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
