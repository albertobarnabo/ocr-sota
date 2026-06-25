# Contributing to OCR-SOTA

Thanks for helping keep this list current! Adding an OCR method takes **one YAML
block and a pull request** — you never touch the README tables, they regenerate
themselves from live GitHub data.

## Add your favourite OCR in 4 steps

1. **Fork & clone** this repo.
2. **Add an entry** to [`data/methods.yaml`](data/methods.yaml). Copy the template
   below and fill it in. Keep it roughly alphabetical within its category.
3. **(Optional) Preview locally** so you can see your row in the table:
   ```bash
   pip install -r scripts/requirements.txt
   python scripts/update_readme.py        # set GITHUB_TOKEN=... to avoid rate limits
   ```
   This rewrites the tables in `README.md`. You don't *have* to run it — CI does
   it on merge — but it's a nice sanity check.
4. **Open a pull request.** Done.

## Entry template

```yaml
- name: Your OCR Name
  repo: owner/repository          # GitHub "owner/name"; drives stars and last commit
  category: "Engines & toolkits"  # must match one of the categories below
  description: One factual sentence on what it does
  languages: "100+"               # optional: e.g. "English", "80+", "Multi"
  homepage: https://example.com   # optional: docs/site (defaults to the repo)
  paper: https://arxiv.org/abs/…  # optional: rendered as a "(paper)" link
  # license is auto-filled from GitHub; only set it to override
```

### Field rules

| Field         | Required | Notes |
| ------------- | :------: | ----- |
| `name`        | ✅ | Display name. |
| `repo`        | ✅ | `owner/name` on GitHub. Must be a **real, public** repo; stars and last-commit date are fetched from it. |
| `category`    | ✅ | One of the categories below (or propose a new one — see [Adding a category](#adding-a-category)). |
| `description` | ✅ | One line, ~120 chars max, factual, no marketing fluff. |
| `languages`   | ⬜ | Languages supported, e.g. `"100+"`. |
| `homepage`    | ⬜ | Docs or project site. |
| `paper`       | ⬜ | arXiv / paper link. |
| `license`     | ⬜ | Auto-filled from GitHub; only set to override. |

## Categories

Methods are grouped by what they do, not by who made them. Use one of these
exact category strings:

- **Engines & toolkits**: general-purpose OCR engines and SDKs (detection plus recognition).
- **Document & layout parsers**: turn whole PDFs or documents into structured text, tables, and Markdown.
- **Vision-language OCR**: vision-language models that read documents end-to-end.
- **Math & formula**: specialised at equations, tables, and scientific notation.
- **Wrappers & pipelines**: tools built on top of an engine (APIs, glue, post-processing).

### Adding a category

If nothing fits, add your new category string to **both**:
1. the `category:` field of your entry in `data/methods.yaml`, and
2. the `CATEGORY_ORDER` list in [`scripts/update_readme.py`](scripts/update_readme.py)
   (controls display order; unlisted categories are appended alphabetically).

## Acceptance criteria

To keep the list useful, an entry should:

- ✅ Point to a **public GitHub repo** that actually does OCR (engine, parser, or VLM).
- ✅ Be **maintained or historically significant** — brand-new repos are welcome, but
  abandoned forks of existing entries are not.
- ✅ Have a **clear, honest one-line description**. No superlatives you can't back up.
- ✅ **Not duplicate** an existing entry (check first).

Closed-source/commercial-only products generally don't belong here — this list is
for open repos people can read and run. A commercial tool with a substantial OSS
repo is fine; link the repo.

## What you *don't* do

- ❌ Don't edit the tables in `README.md` by hand — they're generated and your
  changes will be overwritten.
- ❌ Don't add star counts, badges or "last updated" text manually — the script
  fetches all of that live.

Questions or a borderline case? Open an issue and let's discuss. 🙌
