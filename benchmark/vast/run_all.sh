#!/usr/bin/env bash
# Run the full roster on this box. Per adapter:
#   1. install (timeboxed; a failed or hung install is itself a recorded result)
#   2. GPU runs: track photo (0:500) then track clean (0:500), --device cuda,
#      with peak VRAM polled from nvidia-smi into results/<model>.vram.txt
#   3. CPU probe: track photo (CPU_ROWS), --device cpu, timeboxed
# Per-model failures are logged and SKIPPED, never fatal. Designed to run
# inside tmux:  tmux new -s bench 'bash benchmark/vast/run_all.sh'
#
# Overridable env: ROSTER, INSTALL_TIMEOUT, GPU_TIMEOUT, CPU_TIMEOUT.
set -uo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Roster order is cost-ordered, not alphabetical: cheap engines first so a run
# cut short by budget still yields a usable table, heavyweight VLMs last, and
# mmocr dead last because its install is expected to fail (EXPECTED_FAILURES.md)
# and a failing install costs INSTALL_TIMEOUT of rented time to discover.
ROSTER="${ROSTER:-tesseract easyocr doctr paddleocr pix2text surya trocr_lines got_ocr2 glm_ocr dots_ocr unlimited_ocr olmocr mmocr}"
INSTALL_TIMEOUT="${INSTALL_TIMEOUT:-1800}"   # 30 min per install
# 500 images at 5 s/img is 42 min; anything past 90 min is a hang, and on a
# prepaid budget one stuck run must not silently drain the balance.
GPU_TIMEOUT="${GPU_TIMEOUT:-5400}"           # 90 min per GPU run of 500 images
# The CPU probe only has to place a model against the 2 s and 60 s/receipt
# verdict thresholds - an order of magnitude apart, so 10 images decide it.
# 50 images x a slow VLM was up to 45 min of rented time per model to learn
# something 10 images already prove.
CPU_ROWS="${CPU_ROWS:-0:10}"
CPU_TIMEOUT="${CPU_TIMEOUT:-900}"            # 15 min: 10 images past this is GPU-required by definition

mkdir -p "$BENCH/results" "$BENCH/logs"
SUMMARY="$BENCH/results/run_all.summary.txt"
: > "$SUMMARY"

note() { echo "$*" | tee -a "$SUMMARY"; }

HAVE_GPU=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  HAVE_GPU=1
fi

VRAM_PID=""
start_vram_poll() {  # $1 = model; samples nvidia-smi every 2 s until killed
  [ "$HAVE_GPU" = 1 ] || return 0
  local out="$BENCH/results/$1.vram.txt"
  (
    peak=0
    base="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '[:space:]')"
    case "$base" in ''|*[!0-9]*) base=0 ;; esac
    while :; do
      cur="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '[:space:]')" || break
      case "$cur" in ''|*[!0-9]*) cur=0 ;; esac
      [ "$cur" -gt "$peak" ] && peak="$cur"
      printf 'peak_mib=%s baseline_mib=%s\n' "$peak" "$base" > "$out"
      sleep 2
    done
  ) &
  VRAM_PID=$!
}
stop_vram_poll() {
  if [ -n "$VRAM_PID" ]; then
    kill "$VRAM_PID" 2>/dev/null
    wait "$VRAM_PID" 2>/dev/null
    VRAM_PID=""
  fi
}
trap 'stop_vram_poll' EXIT

START_TS=$(date +%s)
for MODEL in $ROSTER; do
  echo
  echo "================ $MODEL ================"
  ADIR="$BENCH/adapters/$MODEL"
  if [ ! -d "$ADIR" ]; then
    note "$MODEL: SKIPPED (no adapter directory)"
    continue
  fi

  # ---- install (timeboxed; failure recorded, not fatal) ----
  if [ ! -x "$ADIR/.venv/bin/python" ]; then
    echo "[$MODEL] installing (timeout ${INSTALL_TIMEOUT}s, log: logs/$MODEL.install.log)"
    if timeout "$INSTALL_TIMEOUT" bash "$ADIR/install.sh" > "$BENCH/logs/$MODEL.install.log" 2>&1 \
        && [ -x "$ADIR/.venv/bin/python" ]; then
      echo "[$MODEL] install ok"
    else
      note "$MODEL: INSTALL FAILED or timed out - all runs SKIPPED (logs/$MODEL.install.log)"
      { echo "install failed or timed out after ${INSTALL_TIMEOUT}s; last log lines:";
        tail -25 "$BENCH/logs/$MODEL.install.log" 2>/dev/null; } \
        > "$BENCH/results/$MODEL.install_failed.txt"
      # Remove the partial venv: leaving it would make every rerun skip the
      # install and fail later at predict time with a misleading error.
      rm -rf "$ADIR/.venv"
      continue
    fi
  fi
  # Venv present means the install succeeded (partial venvs are removed
  # above): drop any stale failure marker from an earlier attempt.
  rm -f "$BENCH/results/$MODEL.install_failed.txt"

  # ---- GPU runs with VRAM polling ----
  if [ "$HAVE_GPU" = 1 ]; then
    start_vram_poll "$MODEL"
    for TRACK in photo clean; do
      if timeout "$GPU_TIMEOUT" bash "$BENCH/run_model.sh" "$MODEL" "$TRACK" --device cuda --rows 0:500; then
        note "$MODEL $TRACK cuda: OK"
      else
        note "$MODEL $TRACK cuda: FAILED or timed out (logs/$MODEL.$TRACK.log)"
      fi
    done
    stop_vram_poll
  else
    note "$MODEL: no GPU on this box - cuda runs SKIPPED"
  fi

  # ---- CPU probe (timeboxed; a timeout is itself the 'GPU required' verdict) ----
  if timeout "$CPU_TIMEOUT" bash "$BENCH/run_model.sh" "$MODEL" photo --device cpu --rows "$CPU_ROWS"; then
    note "$MODEL cpu probe: OK"
  else
    note "$MODEL cpu probe: FAILED or timed out after ${CPU_TIMEOUT}s (logs/$MODEL.photo.cpu.log)"
  fi
done

echo
echo "================ SUMMARY ($((($(date +%s) - START_TS) / 60)) min total) ================"
cat "$SUMMARY"
echo

PYBIN="$BENCH/.venv/bin/python"
[ -x "$PYBIN" ] || PYBIN=python3
"$PYBIN" - "$BENCH/results" <<'PY' || true
import json, os, sys

rd = sys.argv[1]
rows = []
for fn in sorted(os.listdir(rd)):
    if not fn.endswith(".json"):
        continue
    try:
        with open(os.path.join(rd, fn)) as f:
            r = json.load(f)
    except Exception:
        continue
    rows.append((fn, r.get("cer"), r.get("wer"), r.get("word_f1"),
                 r.get("mean_sec_per_image"), r.get("n_rows")))
if rows:
    def cell(v, fmt="{:>9.4f}"):
        return fmt.format(v) if isinstance(v, (int, float)) else "{:>9}".format("-")
    print(f"{'results file':42} {'CER':>9} {'WER':>9} {'wordF1':>9} {'s/img':>9} {'rows':>5}")
    for fn, cer, wer, f1, sec, n in rows:
        print(f"{fn:42} {cell(cer)} {cell(wer)} {cell(f1)} {cell(sec)} {n or '-':>5}")
PY
