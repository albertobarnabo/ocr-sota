<p align="center">
  <img src="assets/ocr-sota-hero.png" alt="OCR-SOTA hero image" width="680" />
</p>

# OCR-SOTA

> A living, auto-ranked list of the OCR engines, document parsers and VLM-based
> models that ship faster than anyone can keep up with.

New OCR projects appear almost every week. This repo tracks the good ones in a
single YAML file ([`data/methods.yaml`](data/methods.yaml)) and **regenerates the
ranked tables below from live GitHub data** — star counts, activity and license
are never hand-edited, so the leaderboard is always honest.

- ⭐ **Stars** — popularity, pulled live from the GitHub API
- 🟢🟡🔴 **Activity** — days since the last push (🟢 ≤90d · 🟡 ≤365d · 🔴 stale)
- 🧭 **Grouped by what they actually do** — engines, document parsers, VLM-based, math
- 📄 — links to the model's paper where there is one

Want to add your favourite? See **[CONTRIBUTING.md](CONTRIBUTING.md)** — it's one
YAML block and a pull request.

## The list

<!-- METHODS:START -->

_18 methods tracked · auto-updated 2026-06-25 13:12 UTC_

### 🏗️ Engines & Toolkits

| Project | ⭐ Stars | Activity | License | Languages | What it is |
| --- | ---: | --- | --- | --- | --- |
| **[PaddleOCR](https://paddlepaddle.github.io/PaddleOCR/)** | [83.8k](https://github.com/PaddlePaddle/PaddleOCR/stargazers) | 🟢 0d | Apache-2.0 | 100+ | Lightweight multilingual toolkit; strong CJK, tables and layout; the most-starred OCR repo |
| **[Tesseract](https://tesseract-ocr.github.io/)** | [74.9k](https://github.com/tesseract-ocr/tesseract/stargazers) | 🟢 2d | Apache-2.0 | 100+ | The classic LSTM engine — battle-tested, runs offline in ~10MB, ideal for edge and embedded |
| **[EasyOCR](https://github.com/JaidedAI/EasyOCR)** | [29.7k](https://github.com/JaidedAI/EasyOCR/stargazers) | 🟡 202d | Apache-2.0 | 80+ | Ready-to-use PyTorch OCR with a one-line API and 80+ languages out of the box |
| **[docTR](https://github.com/mindee/doctr)** | [6.2k](https://github.com/mindee/doctr/stargazers) | 🟢 0d | Apache-2.0 | English, French, + | End-to-end document text detection + recognition on TensorFlow/PyTorch by Mindee |
| **[MMOCR](https://github.com/open-mmlab/mmocr)** | [4.7k](https://github.com/open-mmlab/mmocr/stargazers) | 🔴 575d | Apache-2.0 | Multi | OpenMMLab research toolbox — detection, recognition and KIE with many SOTA model implementations |

### 📄 Document & Layout Parsers

| Project | ⭐ Stars | Activity | License | Languages | What it is |
| --- | ---: | --- | --- | --- | --- |
| **[Docling](https://github.com/docling-project/docling)** | [62.1k](https://github.com/docling-project/docling/stargazers) | 🟢 0d | MIT | Multi | Parses PDFs, Office and HTML into structured Markdown/JSON with layout, tables and OCR for gen-AI pipelines |
| **[Marker](https://github.com/datalab-to/marker)** | [36.4k](https://github.com/datalab-to/marker/stargazers) | 🟢 2d | GPL-3.0 | Multi | Converts PDFs, docs and slides to clean Markdown/JSON with tables, equations and code blocks |
| **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** | [34.0k](https://github.com/ocrmypdf/OCRmyPDF/stargazers) | 🟢 2d | MPL-2.0 | 100+ | Adds a searchable text layer to scanned PDFs (Tesseract under the hood) without touching the image |
| **[Surya](https://github.com/datalab-to/surya)** | [20.9k](https://github.com/datalab-to/surya/stargazers) | 🟢 12d | Apache-2.0 | 90+ | Document OCR, layout analysis, reading-order and table recognition across 90+ languages |
| **[Donut](https://github.com/clovaai/donut)** · [📄](https://arxiv.org/abs/2111.15664) | [6.9k](https://github.com/clovaai/donut/stargazers) | 🔴 713d | MIT | Multi | OCR-free document understanding transformer — reads documents end-to-end without a text detector |

### 🧠 VLM / LLM-based OCR

| Project | ⭐ Stars | Activity | License | Languages | What it is |
| --- | ---: | --- | --- | --- | --- |
| **[TrOCR (unilm)](https://github.com/microsoft/unilm/tree/master/trocr)** · [📄](https://arxiv.org/abs/2109.10282) | [22.2k](https://github.com/microsoft/unilm/stargazers) | 🟡 153d | MIT | English, + | Microsoft transformer-based OCR (lives in the unilm repo); strong printed + handwritten recognition |
| **[olmOCR](https://olmocr.allenai.org/)** | [17.4k](https://github.com/allenai/olmocr/stargazers) | 🟡 91d | Apache-2.0 | Multi | AllenAI toolkit that linearizes PDFs for LLM training using a fine-tuned vision-language model |
| **[dots.ocr](https://github.com/rednote-hilab/dots.ocr)** | [9.0k](https://github.com/rednote-hilab/dots.ocr/stargazers) | 🟡 92d | MIT | Multi | Multilingual document layout parsing (text, tables, formulas, reading order) in a single vision-language model |
| **[GOT-OCR2.0](https://github.com/Ucas-HaoranWei/GOT-OCR2.0)** · [📄](https://arxiv.org/abs/2409.01704) | [8.1k](https://github.com/Ucas-HaoranWei/GOT-OCR2.0/stargazers) | 🔴 500d | — | Multi | Unified end-to-end model that OCRs text, tables, formulas, sheet music and charts |
| **[Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)** | [7.3k](https://github.com/baidu/Unlimited-OCR/stargazers) | 🟢 1d | MIT | Multi | Baidu's one-shot model for long-horizon parsing — reads very long documents end-to-end in a single pass |
| **[GLM-OCR](https://github.com/zai-org/GLM-OCR)** | [7.0k](https://github.com/zai-org/GLM-OCR/stargazers) | 🟢 65d | Apache-2.0 | Multi | Zhipu AI's GLM vision-language OCR model for document parsing — text, tables and formulas |

### 🔢 Math & Formula

| Project | ⭐ Stars | Activity | License | Languages | What it is |
| --- | ---: | --- | --- | --- | --- |
| **[Pix2Text](https://github.com/breezedeus/Pix2Text)** | [3.2k](https://github.com/breezedeus/Pix2Text/stargazers) | 🟡 138d | MIT | 80+ | Free Mathpix alternative — recognizes math formulas, tables and mixed text into LaTeX/Markdown |

### 🧩 Wrappers & Pipelines

| Project | ⭐ Stars | Activity | License | Languages | What it is |
| --- | ---: | --- | --- | --- | --- |
| **[MarkItDown](https://github.com/microsoft/markitdown)** | [159.0k](https://github.com/microsoft/markitdown/stargazers) | 🟢 0d | MIT | Multi | Microsoft tool that converts Office docs, PDFs and images to LLM-ready Markdown (OCR for images) |

<!-- METHODS:END -->

## How it works

```
data/methods.yaml         # the only file you edit — the source of truth
scripts/update_readme.py  # fetches GitHub metrics, regenerates the tables above
.github/workflows/        # runs the script weekly + on every change to the data
```

The tables between the `METHODS` markers are **generated**. Edit the YAML, run
the script (or let CI do it), and the README updates itself.

```bash
pip install -r scripts/requirements.txt
python scripts/update_readme.py            # add GITHUB_TOKEN=... for higher rate limits
```

## License

This list and its tooling are released under the [MIT License](LICENSE) — fully
open source. Each listed project keeps its own license, shown in the tables above.
