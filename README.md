<p align="center">
  <img src="assets/ocr-sota-hero.png" alt="OCR-SOTA hero image" width="680" />
</p>

# OCR-SOTA

A curated, automatically ranked list of open-source OCR engines, document
parsers, and vision-language models for text recognition.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

New OCR projects ship constantly. This repository tracks them in a single data
file ([`data/methods.yaml`](data/methods.yaml)) and generates the tables below
from the GitHub API. Star counts, last-commit dates, and licenses are fetched
automatically and are never edited by hand.

Within each category, projects are ranked by GitHub stars. The **Last commit**
column shows the most recent push date, so you can gauge how actively a project
is maintained. To add a project, see [CONTRIBUTING.md](CONTRIBUTING.md): it takes
one entry in the YAML file and a pull request.

## Methods

<!-- METHODS:START -->

18 projects, ranked by GitHub stars within each category. Star counts and last-commit dates are pulled from the GitHub API (last refreshed 2026-06-25).

### Engines & toolkits

| Project | Stars | Last commit | License | Languages | Description |
| :--- | ---: | :---: | :--- | :--- | :--- |
| [PaddleOCR](https://paddlepaddle.github.io/PaddleOCR/) | [83,788](https://github.com/PaddlePaddle/PaddleOCR/stargazers) | 2026-06-25 | Apache-2.0 | 100+ | Lightweight multilingual OCR toolkit with strong CJK, table, and layout support. |
| [Tesseract](https://tesseract-ocr.github.io/) | [74,933](https://github.com/tesseract-ocr/tesseract/stargazers) | 2026-06-22 | Apache-2.0 | 100+ | Classic LSTM-based engine that runs fully offline in about 10 MB; well suited to edge use. |
| [EasyOCR](https://github.com/JaidedAI/EasyOCR) | [29,669](https://github.com/JaidedAI/EasyOCR/stargazers) | 2025-12-05 | Apache-2.0 | 80+ | Ready-to-use PyTorch OCR with a simple API and 80+ languages out of the box. |
| [docTR](https://github.com/mindee/doctr) | [6,153](https://github.com/mindee/doctr/stargazers) | 2026-06-25 | Apache-2.0 | Multi | End-to-end text detection and recognition for documents, on TensorFlow and PyTorch. By Mindee. |
| [MMOCR](https://github.com/open-mmlab/mmocr) | [4,742](https://github.com/open-mmlab/mmocr/stargazers) | 2024-11-27 | Apache-2.0 | Multi | OpenMMLab research toolbox for text detection, recognition, and key information extraction. |

### Document & layout parsers

| Project | Stars | Last commit | License | Languages | Description |
| :--- | ---: | :---: | :--- | :--- | :--- |
| [Docling](https://github.com/docling-project/docling) | [62,134](https://github.com/docling-project/docling/stargazers) | 2026-06-25 | MIT | Multi | Parses PDFs, Office, and HTML into structured Markdown or JSON with layout, table, and OCR support. |
| [Marker](https://github.com/datalab-to/marker) | [36,389](https://github.com/datalab-to/marker/stargazers) | 2026-06-23 | GPL-3.0 | Multi | Converts PDFs, documents, and slides to clean Markdown or JSON, including tables and equations. |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | [33,965](https://github.com/ocrmypdf/OCRmyPDF/stargazers) | 2026-06-22 | MPL-2.0 | 100+ | Adds a searchable text layer to scanned PDFs using Tesseract, leaving the original image intact. |
| [Surya](https://github.com/datalab-to/surya) | [20,915](https://github.com/datalab-to/surya/stargazers) | 2026-06-13 | Apache-2.0 | 90+ | Document OCR with layout analysis, reading-order detection, and table recognition in 90+ languages. |
| [Donut](https://github.com/clovaai/donut) | [6,891](https://github.com/clovaai/donut/stargazers) | 2024-07-11 | MIT | Multi | OCR-free document understanding transformer that reads documents end-to-end with no text detector. ([paper](https://arxiv.org/abs/2111.15664)) |

### Vision-language OCR

| Project | Stars | Last commit | License | Languages | Description |
| :--- | ---: | :---: | :--- | :--- | :--- |
| [TrOCR (unilm)](https://github.com/microsoft/unilm/tree/master/trocr) | [22,153](https://github.com/microsoft/unilm/stargazers) | 2026-01-23 | MIT | English | Microsoft transformer-based OCR, part of the unilm repo; strong on printed and handwritten text. ([paper](https://arxiv.org/abs/2109.10282)) |
| [olmOCR](https://olmocr.allenai.org/) | [17,408](https://github.com/allenai/olmocr/stargazers) | 2026-03-25 | Apache-2.0 | Multi | AllenAI toolkit that linearizes PDFs for LLM training using a fine-tuned vision-language model. |
| [dots.ocr](https://github.com/rednote-hilab/dots.ocr) | [8,959](https://github.com/rednote-hilab/dots.ocr/stargazers) | 2026-03-24 | MIT | Multi | Multilingual document layout parsing (text, tables, formulas, reading order) in one vision-language model. |
| [GOT-OCR2.0](https://github.com/Ucas-HaoranWei/GOT-OCR2.0) | [8,145](https://github.com/Ucas-HaoranWei/GOT-OCR2.0/stargazers) | 2025-02-10 | — | Multi | Unified end-to-end model that reads text, tables, formulas, sheet music, and charts. ([paper](https://arxiv.org/abs/2409.01704)) |
| [Unlimited-OCR](https://github.com/baidu/Unlimited-OCR) | [7,417](https://github.com/baidu/Unlimited-OCR/stargazers) | 2026-06-24 | MIT | Multi | Baidu model for long-horizon parsing that reads very long documents in a single pass. |
| [GLM-OCR](https://github.com/zai-org/GLM-OCR) | [7,049](https://github.com/zai-org/GLM-OCR/stargazers) | 2026-04-21 | Apache-2.0 | Multi | Zhipu AI's GLM vision-language model for document parsing, including text, tables, and formulas. |

### Math & formula

| Project | Stars | Last commit | License | Languages | Description |
| :--- | ---: | :---: | :--- | :--- | :--- |
| [Pix2Text](https://github.com/breezedeus/Pix2Text) | [3,165](https://github.com/breezedeus/Pix2Text/stargazers) | 2026-02-07 | MIT | 80+ | Open-source Mathpix alternative that recognizes math, tables, and mixed text into LaTeX or Markdown. |

### Wrappers & pipelines

| Project | Stars | Last commit | License | Languages | Description |
| :--- | ---: | :---: | :--- | :--- | :--- |
| [MarkItDown](https://github.com/microsoft/markitdown) | [159,006](https://github.com/microsoft/markitdown/stargazers) | 2026-06-24 | MIT | Multi | Microsoft tool that converts Office documents, PDFs, and images to LLM-ready Markdown, with OCR for images. |

<!-- METHODS:END -->

## How it works

```
data/methods.yaml         # the only file you edit (source of truth)
scripts/update_readme.py  # fetches GitHub metrics and regenerates the tables above
.github/workflows/        # runs the script weekly and on every change to the data
```

The tables between the `METHODS` markers are generated. Edit the YAML, run the
script (or let CI do it), and the README updates itself.

```bash
pip install -r scripts/requirements.txt
python scripts/update_readme.py            # add GITHUB_TOKEN=... for higher rate limits
```

## License

This list and its tooling are released under the [MIT License](LICENSE). Each
listed project keeps its own license, shown in the tables above.
