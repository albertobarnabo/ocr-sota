#!/usr/bin/env python3
"""PaddleOCR 3.x adapter for the receipts OCR benchmark.

MAJOR API churn 2.x -> 3.x: the old reader.ocr(img, cls=True) call, the
[[box,(text,score)],...] return shape and use_angle_cls are all GONE.
3.x: PaddleOCR(...).predict(img) returns result objects exposing
rec_texts / rec_scores / rec_polys / rec_boxes (dict-style access).
use_textline_orientation replaces the old use_angle_cls.

'lang' selects the recognition model and is fixed per instance. The spec
allows one instance per locale OR the Latin model across all; we use
lang='latin' as the single fair config for the mixed US/UK/DE/IT/FR set
(covers de/it/fr accents that 'en' lacks). Default pulls PP-OCRv5 mobile
det+rec+cls on first use (auto-download).
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

    import numpy as np
    import pyarrow.parquet as pq
    from PIL import Image
    from paddleocr import PaddleOCR

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    ocr = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_textline_orientation=True, lang="latin",
                    device="gpu" if args.device == "cuda" else "cpu")

    def recognize(img):
        result = ocr.predict(np.asarray(img))  # accepts HxWx3 uint8 numpy
        if not result:
            return ""
        res = result[0]
        return "\n".join(res["rec_texts"])

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
