#!/usr/bin/env python3
"""dots.ocr (rednote-hilab/dots.ocr) adapter for the receipts benchmark.

~3B VLM (1.7B LLM + vision), trust_remote_code custom modeling. We use the
verbatim prompt_ocr from dots_ocr/utils/prompts.py for PLAIN text -- the
headline prompt_layout_all_en instead emits JSON with bbox+category+text
(layout parse, wrong for the CER track). flash-attn is effectively required
(custom vision path), so CPU is unsupported: exit 42 = UNSUPPORTED_DEVICE.
Loading from the hub id avoids the local-dir-with-a-dot import gotcha.
"""
import argparse
import io
import json
import sys
import time

MID = "rednote-hilab/dots.ocr"
PROMPT_OCR = "Extract the text content from this image."  # verbatim prompt_ocr


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
        print("UNSUPPORTED_DEVICE: dots.ocr needs flash-attn on CUDA "
              "(custom vision path); no CPU support.", file=sys.stderr)
        sys.exit(42)

    import pyarrow.parquet as pq
    import torch
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor
    from qwen_vl_utils import process_vision_info

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    model = AutoModelForCausalLM.from_pretrained(
        MID, attn_implementation="flash_attention_2", torch_dtype=torch.bfloat16,
        device_map="cuda", trust_remote_code=True)
    proc = AutoProcessor.from_pretrained(MID, trust_remote_code=True)

    def recognize(img):
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": PROMPT_OCR}]}]
        text_in = proc.apply_chat_template(messages, tokenize=False,
                                           add_generation_prompt=True)
        imgs, _ = process_vision_info(messages)
        inputs = proc(text=[text_in], images=imgs, return_tensors="pt").to("cuda")
        gen = model.generate(**inputs, max_new_tokens=8192, do_sample=False)
        return proc.batch_decode([gen[0][inputs.input_ids.shape[1]:]],
                                 skip_special_tokens=True)[0]

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
