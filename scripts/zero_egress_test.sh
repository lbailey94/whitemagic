#!/usr/bin/env bash
# zero_egress_test.sh — Q37: the zero-egress proof.
#
# "Zero cloud, zero telemetry" stops being a claim and becomes a test:
# run `wm serve` + a real create + recall inside a network namespace with
# NO interfaces except a down loopback — if the product works there, it
# cannot have phoned home. The proof is the passing run itself; CI (the
# release lane) wires this into the workflow and publishes the artifact.
#
# Requirements: Linux user namespaces (kernel.unprivileged_userns_clone=1
# or root), wm binary on PATH. No root needed with -r (map root).
#
# Exit 0 = proof holds. Any failure exits 1 and prints why.
set -u
WM="${WM:-$HOME/.local/bin/wm}"
STORE="$(mktemp -d /tmp/wm-zero-egress.XXXXXX)"
trap 'rm -rf "$STORE"' EXIT

[ -x "$WM" ] || { echo "FAIL: wm binary not at $WM"; exit 1; }

# The proof environment: user + network namespace, loopback stays DOWN
# (not even localhost TCP exists — SSE transports must not be needed for
# the product's core loop). Assert the interface set first: if anything
# beyond lo exists, the isolation failed and the run proves nothing.
unshare -rn bash -s -- "$WM" "$STORE" <<'PROOF' || exit 1
WM="$1"; STORE="$2"
set -u
links="$(ip -o link show | awk -F': ' '{print $2}')"
n_links="$(ip -o link show | wc -l)"
if [ "$n_links" -ne 1 ] || [ "$links" != "lo" ]; then
  echo "FAIL: expected exactly one interface (lo), got: $links"
  ip -o link show
  exit 1
fi
if ip link show lo | grep -q UP; then
  echo "FAIL: loopback is UP; tighten the namespace (ip link set lo down) "
  exit 1
fi
echo "[proof] namespace: $(ip -o link show | wc -l) interface(s): lo (DOWN) — no egress path exists"

# The product loop over stdio: initialize → create → recall.
python3 - "$WM" "$STORE" <<'EOF'
import json, subprocess, os, sys, time, threading

wm, store = sys.argv[1], sys.argv[2]
p = subprocess.Popen(
    [wm, "serve", "--store", store, "--profile", "minimal", "--transport", "stdio"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
out = []
threading.Thread(target=lambda: [out.append(l.strip()) for l in p.stdout], daemon=True).start()
time.sleep(2)

def rpc(rid, method, params):
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n")
    p.stdin.flush()

rpc(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "zero-egress-proof", "version": "1"}})
time.sleep(1)
rpc(2, "notifications/initialized", {})
rpc(3, "tools/call", {"name": "wm", "arguments": {"route": "memory.create", "args": {
    "content": "Zero-egress proof memory: written inside a namespace with no interfaces.", "galaxy": "codex"}}})
time.sleep(1.5)
rpc(4, "tools/call", {"name": "wm", "arguments": {"route": "memory.search", "args": {"query": "zero-egress proof"}}})
time.sleep(2)
p.terminate()

results = {}
for line in out:
    try:
        r = json.loads(line)
        if r.get("id") in (3, 4) and "result" in r:
            results[r["id"]] = json.loads(r["result"]["content"][0]["text"])
    except Exception:
        pass

created = results.get(3, {})
found_raw = json.dumps(results.get(4, {}))
if created.get("status") != "success":
    print(f"FAIL: create inside netns did not succeed: {created.get('message', created)}")
    sys.exit(1)
if "zero-egress proof memory" not in found_raw.lower():
    print(f"FAIL: recall inside netns did not find the memory: {found_raw[:300]}")
    sys.exit(1)
print(f"[proof] create OK (id {str(created.get('id', '?'))[:8]}…), recall OK — full product loop with zero network")
EOF
python_rc=$?
if [ "$python_rc" -ne 0 ]; then
  echo "FAIL: proof harness exited $python_rc"
  exit 1
fi
echo "[proof] PASS: WhiteMagic works with no network. Zero egress is a test result, not a claim."
PROOF
rc=$?
[ $rc -eq 0 ] && echo "zero_egress_test: PASS ($(date -u +%Y-%m-%dT%H:%M:%SZ), wm=$($WM --version 2>/dev/null || echo '?'))"
exit $rc
