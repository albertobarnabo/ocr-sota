#!/usr/bin/env python3
"""GOT-OCR 2.0 (stepfun-ai/GOT-OCR-2.0-hf) adapter for the receipts benchmark.

580M-param encoder-decoder (NOT a chat VLM). There is NO OCR prompt: the
'task' is set via processor kwargs and plain transcription is the default --
do NOT pass format=True (that emits markdown/LaTeX, wrong for this CER
track). GOTCHA baked in below: stop_strings REQUIRES tokenizer=proc.tokenizer
in generate() or it errors. Native 1024x1024 input. CPU inference works
(tiny model) but autoregressive decode of long receipts may exceed the
2 s/receipt CPU-friendly threshold -- that is what the CPU probe measures.
"""
import argparse
import io
import json
import sys
import time

MID = "stepfun-ai/GOT-OCR-2.0-hf"


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
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    # cpu = float32 (bf16 matmuls are slow/poorly supported on many CPUs)
    dtype = torch.bfloat16 if args.device == "cuda" else torch.float32
    model = AutoModelForImageTextToText.from_pretrained(
        MID, torch_dtype=dtype, device_map=args.device)
    proc = AutoProcessor.from_pretrained(MID, use_fast=True)

    def recognize(img):
        inputs = proc(img, return_tensors="pt").to(model.device)
        gen = model.generate(**inputs, do_sample=False, tokenizer=proc.tokenizer,
                             stop_strings="<|im_end|>", max_new_tokens=4096)
        return proc.decode(gen[0, inputs["input_ids"].shape[1]:],
                           skip_special_tokens=True)

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
