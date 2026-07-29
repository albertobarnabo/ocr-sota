#!/usr/bin/env bash
# Throwaway dev adapter used to smoke-test the runner + scorer pipeline.
# Its only dependency is pyarrow (to read row ids from the parquet).
# Idempotent: safe to re-run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet pyarrow
echo "install ok: $(.venv/bin/python -c 'import pyarrow; print("pyarrow", pyarrow.__version__)')"
