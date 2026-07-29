#!/usr/bin/env python3
"""olmOCR-2 (allenai/olmOCR-2-7B-1025) adapter for the receipts benchmark.

Qwen2.5-VL-7B fine-tune, confirmed to run on single images outside the PDF
pipeline. Weights load from the olmOCR repo but the PROCESSOR loads from the
Qwen base (the official example does exactly this). Images are resized so the
longest side = 1288 px (olmOCR's expected input). CER-critical caveat baked
in below: output is markdown WITH A YAML FRONT-MATTER block that MUST be
stripped or CER is wrecked. Official example uses temp=0.1; we use greedy
decoding for a deterministic benchmark. 7B => GPU-required: cpu exits 42.
"""
import argparse
import io
import json
import sys
import time

MID = "allenai/olmOCR-2-7B-1025"
PROC_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
# Verbatim build_no_anchoring_v4_yaml_prompt() text (avoids the olmocr package):
PROMPT = ("Attached is one page of a document that you must process. Just return the plain text "
          "representation of this document as if you were reading it naturally. Convert equations to "
          "LateX and tables to HTML.\nIf there are any figures or charts, label them with the following "
          "markdown syntax ![Alt text describing the contents of the figure]"
          "(page_startx_starty_width_height.png)\nReturn your output as markdown, with a front matter "
          "section on top specifying values for the primary_language, is_rotation_valid, "
          "rotation_correction, is_table, and is_diagram parameters.")


def strip_front_matter(raw):
    # Output starts with a '---' ... '---' YAML block; return only the body.
    if raw.lstrip().startswith("---"):
        parts = raw.lstrip().split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return raw


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
        print("UNSUPPORTED_DEVICE: olmOCR-2 is a 7B VLM; CPU inference is "
              "not feasible for this benchmark.", file=sys.stderr)
        sys.exit(42)

    import pyarrow.parquet as pq
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    table = pq.read_table(args.parquet, columns=["id", args.image_col]).slice(a, b - a)
    ids = table.column("id").to_pylist()
    blobs = table.column(args.image_col).to_pylist()
    total = len(ids)

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MID, torch_dtype=torch.bfloat16, device_map="cuda").eval()
    proc = AutoProcessor.from_pretrained(PROC_ID)

    def recognize(img):
        img = img.copy()
        img.thumbnail((1288, 1288))  # olmOCR expects longest dimension = 1288 px
        messages = [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image", "image": img}]}]
        text_in = proc.apply_chat_template(messages, tokenize=False,
                                           add_generation_prompt=True)
        inputs = proc(text=[text_in], images=[img], return_tensors="pt").to(model.device)
        gen = model.generate(**inputs, do_sample=False, max_new_tokens=4096)
        raw = proc.tokenizer.batch_decode(gen[:, inputs.input_ids.shape[1]:],
                                          skip_special_tokens=True)[0]
        return strip_front_matter(raw)

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
