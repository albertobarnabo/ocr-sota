#!/usr/bin/env python3
"""Pix2Text adapter for the receipts OCR benchmark.

For the transcription benchmark we use recognize_text() ONLY: it returns a
plain string (accepts path / PIL / numpy). The heavier recognize_page()
document->Markdown path adds layout+formula detection -- overkill and slower
for flat receipts, and it can inject LaTeX for anything formula-like, which
would wreck CER. device='cpu' is supported.
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

    import pyarrow.parquet as pq
    from PIL import Image
    from pix2text import Pix2Text

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    p2t = Pix2Text.from_config(device=args.device)

    def recognize(img):
        text = p2t.recognize_text(img)  # PURE OCR text (str)
        return text if isinstance(text, str) else str(text)

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
