#!/usr/bin/env bash
# Quiet-window LongMemEval-S matrix runner.
#
# Runs a sequential set of retrieval configurations through
# scripts/longmemeval_bench.py, each with its own store + JSON + log, then
# writes a summary.tsv. Designed for the post-improvement recall pass:
#
#   scripts/eval_matrix.sh --suite smoke --questions 10     # validate tooling
#   scripts/eval_matrix.sh --suite fast   --questions 50    # episodic family
#   scripts/eval_matrix.sh --suite full   --questions 50    # + bm25/hybrid
#   scripts/eval_matrix.sh --suite sweep  --questions 50    # rerank params
#
# The load gate refuses to start when 1-minute loadavg exceeds
# --load-factor (default 2.0) x CPUs, so numbers are only produced in a
# genuinely quiet window. Every config's JSON records loadavg start/end and
# the observed recall_mode counts (harness >= 2026-09-13).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${WM_BINARY:-$ROOT/target/debug/wm}"
DS="${WM_DATASET:-$ROOT/benchmarks/data/longmemeval_s/longmemeval_s_50q_canonical.json}"
EMBED_ENDPOINT="${WM_EMBEDDER_ENDPOINT:-http://127.0.0.1:18899/v1/embeddings}"
EMBED_MODEL="${WM_EMBEDDER_MODEL:-bge-small}"
EMBED_DIM="${WM_EMBEDDER_DIM:-384}"
EMBED_TIMEOUT="${WM_EMBEDDER_TIMEOUT_MS:-15000}"
EMBED_BASE="${EMBED_ENDPOINT%/v1/embeddings}"

QUESTIONS=50
SUITE=fast
OUT=""
ONLY=""
KEEP_STORES=0
SKIP_LOAD_CHECK=0
LOAD_FACTOR=2.0

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --questions) QUESTIONS="$2"; shift 2 ;;
        --suite) SUITE="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --only) ONLY="$2"; shift 2 ;;
        --keep-stores) KEEP_STORES=1; shift ;;
        --skip-load-check) SKIP_LOAD_CHECK=1; shift ;;
        --load-factor) LOAD_FACTOR="$2"; shift 2 ;;
        -h|--help) usage 0 ;;
        *) echo "unknown argument: $1" >&2; usage 1 ;;
    esac
done

CPU="$(nproc)"
read -r LOAD1 _ < /proc/loadavg
busy() { awk -v l="$1" -v c="$CPU" -v f="$LOAD_FACTOR" 'BEGIN { exit !(l > f * c) }'; }

if [ "$SKIP_LOAD_CHECK" -eq 0 ] && busy "$LOAD1"; then
    echo "ABORT: loadavg 1m=$LOAD1 > ${LOAD_FACTOR}x${CPU} CPUs — wait for a quiet window (or --skip-load-check)" >&2
    exit 3
fi

OUT="${OUT:-$ROOT/benchmarks/results/matrix-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT/stores"

EMBED_OK=0
if curl -sf -m 3 "$EMBED_BASE/health" >/dev/null 2>&1; then
    EMBED_OK=1
fi
echo "matrix: suite=$SUITE questions=$QUESTIONS cpus=$CPU loadavg=$(echo "$LOAD1" | cut -d. -f1) embedder=$([ "$EMBED_OK" -eq 1 ] && echo up || echo DOWN)"
echo "output: $OUT"

# label|route|env-profile|flags
CONFIGS=()
add() { CONFIGS+=("$1|$2|$3|$4"); }

case "$SUITE" in
    smoke)
        add episodic-baseline  memory.episodic_search none                  ""
        add episodic-rerank07  memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7"
        add hybrid-baseline    memory.search        embedder                ""
        ;;
    fast)
        add episodic-baseline  memory.episodic_search none                  ""
        add episodic-tuned     memory.episodic_search none                  "--keywords --contextual --composites"
        add episodic-rerank07  memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7"
        ;;
    full)
        add episodic-baseline  memory.episodic_search none                  ""
        add episodic-tuned     memory.episodic_search none                  "--keywords --contextual --composites"
        add episodic-rerank07  memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7"
        add bm25-baseline      memory.search        embedder-bm25only       ""
        add hybrid-baseline    memory.search        embedder                ""
        ;;
    sweep)
        add rerank-alpha05     memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.5"
        add rerank-alpha07     memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7"
        add rerank-alpha09     memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.9"
        add rerank-cand200     memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7 --candidate-limit 200"
        add rerank-cand500     memory.episodic_search embedder-rerankonly   "--rerank --rerank-alpha 0.7 --candidate-limit 500"
        ;;
    *) echo "unknown suite: $SUITE" >&2; exit 1 ;;
esac

SUMMARY="$OUT/summary.tsv"
printf 'label\troute\tflags\tR@1\tR@5\tR@10\tMRR\tcand_pres\telapsed_s\trecall_modes\n' > "$SUMMARY"

for cfg in "${CONFIGS[@]}"; do
    IFS='|' read -r label route profile flags <<< "$cfg"
    if [ -n "$ONLY" ] && [[ ",$ONLY," != *",$label,"* ]]; then continue; fi

    case "$profile" in
        embedder*)
            if [ "$EMBED_OK" -ne 1 ]; then
                echo "SKIP $label (embedder not reachable at $EMBED_BASE)" | tee -a "$SUMMARY"
                continue
            fi
            ;;
    esac

    ENV_CMD=(env
        -u WM_EMBEDDER_ENDPOINT -u WM_EMBEDDER_MODEL -u WM_EMBEDDER_DIM -u WM_EMBEDDER_TIMEOUT_MS
        -u WM_EPISODIC_RERANK_ONLY
        -u WM_RECALL_BM25_WEIGHT -u WM_RECALL_VECTOR_WEIGHT -u WM_RECALL_IMPORTANCE_WEIGHT)
    case "$profile" in
        none) : ;;
        embedder)
            ENV_CMD+=(WM_EMBEDDER_ENDPOINT="$EMBED_ENDPOINT" WM_EMBEDDER_MODEL="$EMBED_MODEL"
                      WM_EMBEDDER_DIM="$EMBED_DIM" WM_EMBEDDER_TIMEOUT_MS="$EMBED_TIMEOUT")
            ;;
        embedder-rerankonly)
            ENV_CMD+=(WM_EMBEDDER_ENDPOINT="$EMBED_ENDPOINT" WM_EMBEDDER_MODEL="$EMBED_MODEL"
                      WM_EMBEDDER_DIM="$EMBED_DIM" WM_EMBEDDER_TIMEOUT_MS="$EMBED_TIMEOUT"
                      WM_EPISODIC_RERANK_ONLY=1)
            ;;
        embedder-bm25only)
            ENV_CMD+=(WM_EMBEDDER_ENDPOINT="$EMBED_ENDPOINT" WM_EMBEDDER_MODEL="$EMBED_MODEL"
                      WM_EMBEDDER_DIM="$EMBED_DIM" WM_EMBEDDER_TIMEOUT_MS="$EMBED_TIMEOUT"
                      WM_RECALL_BM25_WEIGHT=1 WM_RECALL_VECTOR_WEIGHT=0 WM_RECALL_IMPORTANCE_WEIGHT=0)
            ;;
        *) echo "unknown env profile: $profile" >&2; exit 1 ;;
    esac

    JSON="$OUT/$label.json"
    LOG="$OUT/$label.log"
    rm -rf "$OUT/stores/$label"
    echo "=== $label ($route ${flags:-defaults}) start $(date '+%H:%M:%S') loadavg $(cut -d' ' -f1-3 /proc/loadavg)"

    set +e
    # shellcheck disable=SC2086  # flags is a trusted, space-separated flag list
    "${ENV_CMD[@]}" python3 "$ROOT/scripts/longmemeval_bench.py" \
        --binary "$BIN" --dataset "$DS" --max-questions "$QUESTIONS" \
        --persistent --store "$OUT/stores/$label" --output "$JSON" --per-case \
        --route "$route" $flags >"$LOG" 2>&1
    rc=$?
    set -e

    if [ $rc -ne 0 ] || [ ! -s "$JSON" ]; then
        echo "FAILED $label (rc=$rc) — see $LOG"
        printf '%s\t%s\t%s\tFAILED(rc=%s)\n' "$label" "$route" "${flags:-defaults}" "$rc" >> "$SUMMARY"
        continue
    fi

    python3 - "$JSON" "$label" "$route" "${flags:-defaults}" "$SUMMARY" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
r = data["recall"]
modes = ",".join(f"{k}:{v}" for k, v in sorted(data.get("search_modes", {}).items()))
row = [
    sys.argv[2], sys.argv[3], sys.argv[4],
    f"{r['recall_at_1']:.4f}", f"{r['recall_at_5']:.4f}", f"{r['recall_at_10']:.4f}",
    f"{r['mrr']:.4f}", f"{r['candidate_presence']:.4f}",
    str(data.get("total_elapsed_s", "?")), modes or "-",
]
open(sys.argv[5], "a", encoding="utf-8").write("\t".join(row) + "\n")
PY
    echo "  done: $(tail -1 "$SUMMARY")"
done

if [ "$KEEP_STORES" -eq 0 ]; then
    rm -rf "$OUT/stores"
fi
echo "matrix complete: $OUT"
if command -v column >/dev/null 2>&1; then column -t -s $'\t' "$SUMMARY"; else cat "$SUMMARY"; fi
