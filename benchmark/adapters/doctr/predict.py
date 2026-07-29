#!/usr/bin/env python3
"""docTR adapter for the receipts OCR benchmark.

ocr_predictor(pretrained=True) = default det db_resnet50 + rec crnn_vgg16_bn.
The predictor accepts a list of HxWx3 uint8 numpy arrays directly, so we skip
DocumentFile and feed the decoded parquet image. result.render() returns
plain text assembled block->line in reading order -- ideal for the
newline-as-space CER variant. Script-agnostic Latin recognizer (fine for
en/de/fr/it). assume_straight_pages=True by default (receipts are upright).
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
    from doctr.models import ocr_predictor

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    model = ocr_predictor(pretrained=True)
    if args.device == "cuda":
        model = model.cuda()  # auto-uses GPU once moved

    def recognize(img):
        result = model([np.asarray(img)])
        return result.render()

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
