#!/usr/bin/env python3
"""GLM-OCR (zai-org/GLM-OCR) adapter for the receipts benchmark.

Small but SOTA (~1.3B actual params). Native transformers support:
GlmOcrForConditionalGeneration (if the import fails, install.sh falls back to
transformers from source -- the model landed on main first). Prompt for plain
full-page text is 'Text Recognition:' (the model also has formula/table/KIE
task prompts -- wrong for this track). The full GLM-OCR repo pipeline bundles
PP-DocLayoutV3, but single-image transformers use does NOT need it. CPU
inference is feasible (small model): float32 on cpu.
"""
import argparse
import io
import json
import sys
import time

MID = "zai-org/GLM-OCR"


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
    from transformers import AutoProcessor, GlmOcrForConditionalGeneration

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    proc = AutoProcessor.from_pretrained(MID)
    dtype = "bfloat16" if args.device == "cuda" else "float32"  # cpu = float32
    model = GlmOcrForConditionalGeneration.from_pretrained(
        MID, torch_dtype=dtype, device_map=args.device)

    def recognize(img):
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Text Recognition:"}]}]  # plain-text task prompt
        inputs = proc.apply_chat_template(messages, tokenize=True,
                                          add_generation_prompt=True,
                                          return_dict=True,
                                          return_tensors="pt").to(model.device)
        gen = model.generate(**inputs, max_new_tokens=4096, do_sample=False)
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
