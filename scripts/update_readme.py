#!/usr/bin/env python3
"""Regenerate the OCR-SOTA showcase tables in README.md from data/methods.yaml.

For every method listed in ``data/methods.yaml`` this fetches live metrics from
the GitHub API (stars, last-push activity, license), groups the methods by
category, sorts each group by star count, and rewrites the block between the
``<!-- METHODS:START -->`` and ``<!-- METHODS:END -->`` markers in README.md.

Usage:
    python scripts/update_readme.py
    GITHUB_TOKEN=ghp_xxx python scripts/update_readme.py   # higher rate limit

The GitHub Action in .github/workflows/update-stars.yml runs this on a schedule
so the leaderboard stays fresh without anyone counting stars by hand.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# Use certifi's CA bundle when available so HTTPS works on systems (notably
# macOS) where Python isn't wired to the system trust store. Falls back to the
# default context everywhere else.
try:
    import certifi

    _SSL_CTX: ssl.SSLContext | None = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "methods.yaml"
README = ROOT / "README.md"

START = "<!-- METHODS:START -->"
END = "<!-- METHODS:END -->"

# Display order for categories. Anything not listed is appended alphabetically.
CATEGORY_ORDER = [
    "Engines & toolkits",
    "Document & layout parsers",
    "Vision-language OCR",
    "Math & formula",
    "Wrappers & pipelines",
]


def gh_get(repo: str) -> dict:
    """Fetch a repo's metadata from the GitHub REST API."""
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ocr-sota-updater",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return json.load(resp)


def last_commit(pushed_at: str) -> str:
    """ISO date (YYYY-MM-DD) of the last push, or an em dash if unknown."""
    return pushed_at[:10] if pushed_at else "—"


def enrich(entry: dict) -> dict:
    """Attach live GitHub metrics to a method entry (in place)."""
    repo = entry["repo"]
    try:
        meta = gh_get(repo)
        entry["stars"] = meta.get("stargazers_count", 0)
        entry["pushed_at"] = meta.get("pushed_at", "")
        lic = (meta.get("license") or {}).get("spdx_id")
        if not entry.get("license"):
            entry["license"] = lic if lic and lic != "NOASSERTION" else "—"
        if not entry.get("description"):
            entry["description"] = meta.get("description", "") or ""
        entry["ok"] = True
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        print(f"  ! {repo}: {exc}", file=sys.stderr)
        entry.setdefault("stars", 0)
        entry.setdefault("pushed_at", "")
        entry.setdefault("license", "—")
        entry["ok"] = False
    return entry


def fmt_stars(n: int) -> str:
    """Right-aligned, comma-grouped star count, e.g. 83,781."""
    return f"{n:,}"


def render(methods: list[dict]) -> str:
    by_cat: dict[str, list[dict]] = {}
    for m in methods:
        by_cat.setdefault(m.get("category", "Uncategorized"), []).append(m)

    cats = [c for c in CATEGORY_ORDER if c in by_cat]
    cats += sorted(c for c in by_cat if c not in CATEGORY_ORDER)

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out = [
        f"{len(methods)} projects, ranked by GitHub stars within each category. "
        f"Star counts and last-commit dates are pulled from the GitHub API "
        f"(last refreshed {today})."
    ]

    for cat in cats:
        rows = sorted(by_cat[cat], key=lambda m: m.get("stars", 0), reverse=True)
        out.append(f"\n### {cat}\n")
        out.append("| Project | Stars | Last commit | License | Languages | Description |")
        out.append("| :--- | ---: | :---: | :--- | :--- | :--- |")
        for m in rows:
            link = m.get("homepage") or f"https://github.com/{m['repo']}"
            name = f"[{m['name']}]({link})"
            desc = str(m.get("description", "")).strip()
            if m.get("paper"):
                desc = f"{desc} ([paper]({m['paper']}))"
            stars = f"[{fmt_stars(m.get('stars', 0))}](https://github.com/{m['repo']}/stargazers)"
            out.append(
                f"| {name} | {stars} | {last_commit(m.get('pushed_at', ''))} "
                f"| {m.get('license', '—')} | {m.get('languages', '—')} | {desc} |"
            )
    return "\n".join(out) + "\n"


def main() -> int:
    methods = yaml.safe_load(DATA.read_text())
    if not isinstance(methods, list) or not methods:
        print("data/methods.yaml must be a non-empty YAML list", file=sys.stderr)
        return 1

    print(f"Fetching GitHub metrics for {len(methods)} methods…")
    for m in methods:
        if "name" not in m or "repo" not in m:
            print(f"  ! entry missing name/repo: {m}", file=sys.stderr)
            return 1
        enrich(m)
        flag = "" if m.get("ok") else "  (fetch failed)"
        print(f"  ✓ {m['name']:18} ⭐ {m.get('stars', 0)}{flag}")

    # Refuse to write a degraded README: a partial fetch (e.g. GitHub rate limit)
    # would zero out stars/license for the failed rows and clobber good data.
    failed = [m["name"] for m in methods if not m.get("ok")]
    if failed:
        print(
            f"\nAborting: {len(failed)} repo(s) failed to fetch "
            f"({', '.join(failed)}).\n"
            "README left unchanged. Likely the GitHub rate limit — re-run with a "
            "token:\n    GITHUB_TOKEN=$(gh auth token) python scripts/update_readme.py",
            file=sys.stderr,
        )
        return 1

    table = render(methods)
    readme = README.read_text()
    if START not in readme or END not in readme:
        print(f"Markers {START} / {END} not found in README.md", file=sys.stderr)
        return 1

    pre, post = readme.split(START)[0], readme.split(END)[1]
    README.write_text(f"{pre}{START}\n\n{table}\n{END}{post}")
    print(f"\nWrote {README.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
