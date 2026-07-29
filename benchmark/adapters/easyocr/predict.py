#!/usr/bin/env python3
"""EasyOCR adapter for the receipts OCR benchmark.

Reader(langs, gpu=...) downloads a CRAFT detector (~79 MB) + a Latin
recognizer (latin_g2, ~30 MB) to ~/.EasyOCR on first use. Only mutually
compatible scripts may share a reader -- en/de/fr/it are all Latin, so one
reader covers every dataset locale. detail=0 returns just the strings.
paragraph=True can REORDER text, so for receipts we use paragraph=False and
rely on EasyOCR's top-to-bottom ordering.
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
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    args = ap.parse_args()
    a, b = (int(x) for x in args.rows.split(":"))

    import easyocr
    import numpy as np
    import pyarrow.parquet as pq
    from PIL import Image

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    reader = easyocr.Reader(["en", "de", "fr", "it"], gpu=(args.device == "cuda"))

    def recognize(img):
        lines = reader.readtext(np.asarray(img), detail=0, paragraph=False)
        return "\n".join(lines)

    try:
        recognize(Image.open(io.BytesIO(blobs[0])).convert("RGB"))  # warmup, untimed
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
