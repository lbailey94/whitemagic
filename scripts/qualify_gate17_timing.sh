#!/usr/bin/env bash
# Gate17 full-recall timing protocol v1; preserve every completed run.
set -euo pipefail

log_path="${1:-benchmark-results/gate17-timing.log}"
mkdir -p "$(dirname "$log_path")"
if ! (set -o noclobber; : > "$log_path") 2>/dev/null; then
  echo "Refusing to overwrite timing evidence: $log_path" >&2
  exit 1
fi

GATE17_SOURCE_REVISION="$(git rev-parse HEAD)"
GATE17_TEST_SHA256="$(shasum -a 256 crates/wm-gen3-core/tests/gate17_spreading_activation.rs | awk '{print $1}')"
GATE17_OPS_SHA256="$(shasum -a 256 crates/wm-gen3-core/src/ops.rs | awk '{print $1}')"
if ! [[ "$GATE17_SOURCE_REVISION" =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ ]] \
  || ! [[ "$GATE17_TEST_SHA256" =~ ^[0-9a-f]{64}$ ]] \
  || ! [[ "$GATE17_OPS_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
  echo "Could not bind timing qualification to valid source identities" >&2
  exit 1
fi
export GATE17_SOURCE_REVISION GATE17_TEST_SHA256 GATE17_OPS_SHA256

cargo test --locked -p wm-gen3-core --features operator --release \
  --test gate17_spreading_activation test_gate17_release_recall_latency \
  -- --exact --ignored --test-threads=1 --nocapture --color never 2>&1 | tee -a "$log_path"

running="$(awk '$0 == "running 1 test" { n++ } END { print n+0 }' "$log_path")"
named="$(awk '/^test test_gate17_release_recall_latency [.][.][.]/ { n++ } END { print n+0 }' "$log_path")"
passed="$(awk '/^test result: ok[.] 1 passed; 0 failed; 0 ignored;/ { n++ } END { print n+0 }' "$log_path")"
records="$(awk '/^GATE17_TIMING_JSON=/ { n++ } END { print n+0 }' "$log_path")"
if [ "$running" != 1 ] || [ "$named" != 1 ] || [ "$passed" != 1 ] || [ "$records" != 1 ]; then
  echo "Expected exactly one passing Gate17 timing test and one timing record; got running=$running named=$named passed=$passed records=$records" >&2
  exit 1
fi
sed -n 's/^GATE17_TIMING_JSON=//p' "$log_path" | jq -e \
  --arg revision "$GATE17_SOURCE_REVISION" \
  --arg test_sha256 "$GATE17_TEST_SHA256" \
  --arg ops_sha256 "$GATE17_OPS_SHA256" '
    .protocol == "gate17-full-recall-v1" and .profile == "release"
    and .source_revision == $revision and .test_sha256 == $test_sha256
    and .ops_sha256 == $ops_sha256 and .budget_ns == 5000000
    and (.samples_ns | length) == 9
    and all(.samples_ns[]; type == "number" and . >= 0 and . < 5000000)
  ' >/dev/null
