#!/usr/bin/env python3
"""Unlimited-OCR (baidu/Unlimited-OCR) adapter for the receipts benchmark.

~3.34B, DeepSeek-OCR-derived. Uses a BESPOKE model.infer() API, NOT standard
generate(), and infer() wants an image FILE path -- each row is written to a
temp PNG first (untimed; only the infer() call is timed). Documented prompts:
'<image>document parsing.' (layout/markdown parse) and '<image>Multi page
parsing.'; 'document parsing.' is the closest documented mode for plain
transcription (output is markdown-ish). SPEC CAVEAT baked in: infer()
defaults to save_results=True writing to output_path; some builds may only
write to disk instead of returning the string, so we try the returned value
first and fall back to reading the written file. GPU-required: cpu exits 42.
"""
import argparse
import io
import json
import os
import sys
import tempfile
import time

MID = "baidu/Unlimited-OCR"
PROMPT = "<image>document parsing."


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

    if args.device == "cpu":
        print("UNSUPPORTED_DEVICE: Unlimited-OCR needs flash-attn on CUDA "
              "(DeepSeek-OCR-derived multi-crop pipeline).", file=sys.stderr)
        sys.exit(42)

    import pyarrow.parquet as pq
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    tok = AutoTokenizer.from_pretrained(MID, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        MID, trust_remote_code=True, use_safetensors=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2").eval().cuda()

    workdir = tempfile.mkdtemp(prefix="unlimited_ocr_")
    img_path = os.path.join(workdir, "row.png")
    res_dir = os.path.join(workdir, "results")
    os.makedirs(res_dir, exist_ok=True)

    def recognize_path(path):
        res = model.infer(tok, prompt=PROMPT, image_file=path,
                          base_size=1024, image_size=640, crop_mode=True,
                          max_length=32768, save_results=False)
        if isinstance(res, str) and res.strip():
            return res
        # Fallback for builds whose infer() only writes to disk.
        for f in os.listdir(res_dir):
            os.remove(os.path.join(res_dir, f))
        model.infer(tok, prompt=PROMPT, image_file=path,
                    base_size=1024, image_size=640, crop_mode=True,
                    max_length=32768, output_path=res_dir, save_results=True)
        texts = []
        for f in sorted(os.listdir(res_dir)):
            if f.endswith((".txt", ".md", ".mmd")):
                with open(os.path.join(res_dir, f), encoding="utf-8") as fh:
                    texts.append(fh.read())
        return "\n".join(texts)

    def save_png(blob):
        Image.open(io.BytesIO(blob)).convert("RGB").save(img_path)
        return img_path

    try:
        recognize_path(save_png(blobs[0]))  # warmup, untimed
    except Exception as e:
        print(f"WARN warmup: {type(e).__name__}: {e}", file=sys.stderr)

    done = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for rid, blob in zip(ids, blobs):
            try:
                path = save_png(blob)  # untimed: file prep, not the model
            except Exception as e:
                print(f"WARN {rid}: decode: {type(e).__name__}: {e}", file=sys.stderr)
                out.write(json.dumps({"id": rid, "text": "", "sec": 0.0}) + "\n")
                done += 1
                continue
            t0 = time.perf_counter()
            try:
                text = recognize_path(path)
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
