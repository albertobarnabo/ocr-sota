#!/usr/bin/env bash
# Run one OCR adapter on one track and score it.
#
#   bash run_model.sh <adapter> <track> [--device cuda|cpu] [--rows A:B] [--parquet PATH]
#
#   track     photo -> image_photo column   |   clean -> image_clean column
#   defaults  --device cuda   --rows 0:500   --parquet <repo>/data/eval-0000.parquet
#
# Output:
#   preds/<adapter>.<track>[.cpu].jsonl     raw predictions
#   logs/<adapter>.<track>[.cpu].log        full run log
#   results/<adapter>.<track>[.cpu].json    metrics (via score.py)
# The .cpu suffix keeps CPU probes from clobbering the headline cuda runs.
#
# Resume-safe: if the preds file already holds exactly (B-A) lines, prediction
# is skipped and the file is just re-scored. Incomplete preds files restart.
#
# If ~/.claude/progress/progress exists and is executable, PROGRESS lines from
# predict.py are forwarded to it so a local status bar can render the run.
#
# Scoring interpreter: $OCR_BENCH_PYTHON if set, else benchmark/.venv/bin/python
# if present (created by vast/setup.sh), else python3. It must have pyarrow.
set -uo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "run_model.sh: $*" >&2; exit 1; }

[ $# -ge 2 ] || die "usage: bash run_model.sh <adapter> <track> [--device cuda|cpu] [--rows A:B] [--parquet PATH]"
ADAPTER="$1"; TRACK="$2"; shift 2

DEVICE="cuda"
ROWS="0:500"
PARQUET="$BENCH/../data/eval-0000.parquet"
while [ $# -gt 0 ]; do
  case "$1" in
    --device)  DEVICE="${2:?}";  shift 2 ;;
    --rows)    ROWS="${2:?}";    shift 2 ;;
    --parquet) PARQUET="${2:?}"; shift 2 ;;
    *) die "unknown flag: $1" ;;
  esac
done

case "$TRACK" in
  photo) IMAGE_COL="image_photo" ;;
  clean) IMAGE_COL="image_clean" ;;
  *) die "track must be photo or clean, got: $TRACK" ;;
esac
case "$DEVICE" in cuda|cpu) ;; *) die "device must be cuda or cpu, got: $DEVICE" ;; esac
[ -f "$PARQUET" ] || die "parquet not found: $PARQUET (run vast/setup.sh or pass --parquet)"

ROW_A="${ROWS%%:*}"; ROW_B="${ROWS##*:}"
case "$ROW_A" in ''|*[!0-9]*) die "rows must be A:B, got: $ROWS" ;; esac
case "$ROW_B" in ''|*[!0-9]*) die "rows must be A:B, got: $ROWS" ;; esac
TOTAL=$((ROW_B - ROW_A))
[ "$TOTAL" -gt 0 ] || die "empty row range: $ROWS"

ADIR="$BENCH/adapters/$ADAPTER"
[ -d "$ADIR" ] || die "no adapter directory: $ADIR"

NAME="$ADAPTER.$TRACK"
[ "$DEVICE" = "cpu" ] && NAME="$NAME.cpu"
mkdir -p "$BENCH/preds" "$BENCH/logs" "$BENCH/results"
PREDS="$BENCH/preds/$NAME.jsonl"
LOG="$BENCH/logs/$NAME.log"

SCORE_PY="${OCR_BENCH_PYTHON:-}"
if [ -z "$SCORE_PY" ] && [ -x "$BENCH/.venv/bin/python" ]; then SCORE_PY="$BENCH/.venv/bin/python"; fi
[ -z "$SCORE_PY" ] && SCORE_PY="python3"

# ---------------------------------------------------------------- 1. install
if [ ! -x "$ADIR/.venv/bin/python" ]; then
  echo "[$NAME] creating adapter venv via install.sh (log: $LOG)"
  ( cd "$ADIR" && bash install.sh ) >> "$LOG" 2>&1 || die "install.sh failed (see $LOG)"
  [ -x "$ADIR/.venv/bin/python" ] || die "install.sh finished but $ADIR/.venv/bin/python is missing"
fi

# ---------------------------------------------------------------- 2. predict
HAVE=0
[ -f "$PREDS" ] && HAVE="$(wc -l < "$PREDS" | tr -d '[:space:]')"
if [ "$HAVE" -eq "$TOTAL" ]; then
  echo "[$NAME] preds already complete ($HAVE/$TOTAL lines), skipping prediction"
else
  if [ "$HAVE" -gt 0 ]; then
    echo "[$NAME] incomplete preds file ($HAVE/$TOTAL lines), restarting prediction"
    rm -f "$PREDS"
  fi
  PROGRESS_BIN="$HOME/.claude/progress/progress"
  PJOB="ocr-$ADAPTER"
  echo "[$NAME] predicting rows $ROWS on $DEVICE (log: $LOG)"
  "$ADIR/.venv/bin/python" "$ADIR/predict.py" \
      --parquet "$PARQUET" --rows "$ROWS" --image-col "$IMAGE_COL" \
      --out "$PREDS" --device "$DEVICE" 2>&1 | while IFS= read -r line; do
    printf '%s\n' "$line"
    printf '%s\n' "$line" >> "$LOG"
    if [ -x "$PROGRESS_BIN" ]; then
      case "$line" in
        PROGRESS\ *)
          rest="${line#PROGRESS }"
          done_n="${rest%%/*}"; total_n="${rest##*/}"
          if [ -n "$done_n" ] && [ -n "$total_n" ]; then
            case "$done_n$total_n" in
              *[!0-9]*) ;;
              *) "$PROGRESS_BIN" set "$PJOB" "$done_n" "$total_n" "$ADAPTER $TRACK" >/dev/null 2>&1 || true ;;
            esac
          fi
          ;;
      esac
    fi
  done
  RC="${PIPESTATUS[0]}"
  if [ -x "$PROGRESS_BIN" ]; then "$PROGRESS_BIN" done "$PJOB" >/dev/null 2>&1 || true; fi
  [ "$RC" -eq 0 ] || die "predict.py exited with $RC (see $LOG)"
  GOT=0
  [ -f "$PREDS" ] && GOT="$(wc -l < "$PREDS" | tr -d '[:space:]')"
  [ "$GOT" -eq "$TOTAL" ] || die "expected $TOTAL pred lines, got $GOT (see $LOG)"
fi

# ------------------------------------------------------------------ 3. score
OUT="$BENCH/results/$NAME.json"
echo "[$NAME] scoring -> $OUT"
"$SCORE_PY" "$BENCH/score.py" \
    --preds "$PREDS" --parquet "$PARQUET" \
    --model "$ADAPTER" --track "$TRACK" --device "$DEVICE" --out "$OUT" \
    2>> "$LOG" | tee -a "$LOG"
RC="${PIPESTATUS[0]}"
[ "$RC" -eq 0 ] || die "score.py exited with $RC (see $LOG)"
echo "[$NAME] done"
