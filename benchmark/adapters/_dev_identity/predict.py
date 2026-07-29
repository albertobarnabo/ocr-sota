#!/usr/bin/env python3
"""Dev adapter: predicts empty text for every row.

Exists only to smoke-test the benchmark pipeline (venv install -> predict ->
progress lines -> scoring). It follows the exact adapter contract every real
adapter implements:

    predict.py --parquet PATH --rows A:B --image-col image_photo|image_clean
               --out preds.jsonl --device cuda|cpu

One JSON line per row: {"id": ..., "text": ..., "sec": ...}. The model is
"loaded" once, no single bad image may crash the run (log + emit ""), and
"PROGRESS <done>/<total>" is printed to stdout every 10 images.
"""

import argparse
import json
import sys
import time


def iter_rows(parquet_path, image_col, row_a, row_b):
    """Yield (id, image_bytes) for global rows [row_a, row_b) without loading
    the whole shard into memory."""
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(parquet_path)
    idx = 0
    for batch in pf.iter_batches(columns=["id", image_col], batch_size=32):
        ids = batch.column("id").to_pylist()
        imgs = batch.column(image_col).to_pylist()
        for rid, img in zip(ids, imgs):
            if idx >= row_b:
                return
            if idx >= row_a:
                yield rid, img
            idx += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--rows", default="0:500", help="global row range A:B")
    ap.add_argument("--image-col", default="image_photo",
                    choices=["image_photo", "image_clean"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu", choices=["cuda", "cpu"])
    args = ap.parse_args()

    row_a, row_b = (int(x) for x in args.rows.split(":"))
    rows = list(iter_rows(args.parquet, args.image_col, row_a, row_b))
    total = len(rows)

    # A real adapter loads its model ONCE here, honoring args.device.

    done = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for rid, img in rows:
            t0 = time.perf_counter()
            try:
                # A real adapter decodes img (PNG/JPEG bytes) and runs OCR here.
                len(img)
                text = ""
            except Exception as exc:  # never let one bad image kill the run
                print(f"WARN {rid}: {type(exc).__name__}: {exc}", file=sys.stderr)
                text = ""
            sec = time.perf_counter() - t0
            out.write(json.dumps({"id": rid, "text": text, "sec": sec}) + "\n")
            done += 1
            if done % 10 == 0 or done == total:
                print(f"PROGRESS {done}/{total}", flush=True)


if __name__ == "__main__":
    main()
