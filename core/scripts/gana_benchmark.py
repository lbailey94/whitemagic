"""Per-Gana benchmark: tests all tools in each Gana sequentially."""
import json, time, os, sys
os.environ["WM_BENCHMARK_MODE"] = "1"
os.environ["WM_BENCHMARK_QUIET"] = "1"
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_TOOL_TIMEOUT"] = "15"

from whitemagic.tools.prat_mappings import TOOL_TO_GANA
from whitemagic.tools.dispatch_table import DISPATCH_TABLE, dispatch
from benchmark_tool_campaign import _build_smart_args, _is_expected_failure, SKIP_PREFIXES, SKIP_TOOLS
from whitemagic.tools.registry import get_all_tools

all_tools = get_all_tools()
tool_schemas = {t.name: t.input_schema for t in all_tools}

# Group by Gana
gana_tools = {}
unmapped = []
for tool_name in sorted(DISPATCH_TABLE.keys()):
    gana = TOOL_TO_GANA.get(tool_name)
    if gana:
        gana_tools.setdefault(gana, []).append(tool_name)
    else:
        unmapped.append(tool_name)

# Which Gana to test (from command line arg or all)
target_gana = sys.argv[1] if len(sys.argv) > 1 else None

def test_tool(tool_name):
    """Test a single tool, return (status, elapsed_ms, error_msg, notes)."""
    if tool_name.startswith(SKIP_PREFIXES) or tool_name in SKIP_TOOLS:
        return ("skipped", 0, "external dep", "")

    schema = tool_schemas.get(tool_name, {})
    args = _build_smart_args(tool_name, schema)
    tool_timeout = args.pop("_timeout_s", 15.0)

    t0 = time.perf_counter()
    try:
        result = dispatch(tool_name, **args, _timeout_s=tool_timeout)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if result is None:
            return ("null", elapsed_ms, "returned None", "")
        elif isinstance(result, dict):
            status = result.get("status", "unknown")
            if status in ("success", "ok"):
                return ("ok", elapsed_ms, "", "")
            elif status == "error" and result.get("error_code") == "TIMEOUT":
                return ("timeout", elapsed_ms, (result.get("error") or "")[:120], "")
            elif status == "error":
                err_msg = (result.get("error") or result.get("message") or "")[:120]
                if _is_expected_failure(result):
                    return ("expected", elapsed_ms, err_msg, "")
                else:
                    return ("error", elapsed_ms, err_msg, "")
            else:
                return ("ok", elapsed_ms, "", f"status={status}")
        else:
            return ("ok", elapsed_ms, "", f"type={type(result).__name__}")
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return ("exception", elapsed_ms, str(e)[:120], "")

def run_gana(gana_name, tools):
    """Test all tools in a Gana."""
    results = []
    ok = 0; expected = 0; errors = 0; timeouts = 0; skipped = 0; exceptions = 0

    print(f"\n{'='*70}")
    print(f"  {gana_name.upper()} — {len(tools)} tools")
    print(f"{'='*70}")

    for tool_name in tools:
        status, ms, err, notes = test_tool(tool_name)
        results.append({"tool": tool_name, "status": status, "ms": round(ms, 1), "error": err, "notes": notes})

        if status == "ok": ok += 1
        elif status == "expected": expected += 1
        elif status == "error": errors += 1
        elif status == "timeout": timeouts += 1
        elif status == "exception": exceptions += 1
        elif status == "skipped": skipped += 1

        marker = {"ok": "✓", "expected": "≈", "error": "✗", "timeout": "⏱", "exception": "💥", "skipped": "⊘"}[status]
        if status in ("error", "timeout", "exception"):
            print(f"  {marker} {tool_name:45s} {ms:7.1f}ms  {err}")
        elif status == "expected":
            print(f"  {marker} {tool_name:45s} {ms:7.1f}ms  {err[:60]}")
        elif status == "skipped":
            print(f"  {marker} {tool_name:45s}       —  {err}")

    attempted = ok + expected + errors + timeouts + exceptions
    rate = (ok / max(attempted, 1)) * 100
    adj_rate = ((ok + expected) / max(attempted, 1)) * 100

    print(f"\n  Summary: ok={ok} expected={expected} errors={errors} timeouts={timeouts} exceptions={exceptions} skipped={skipped}")
    print(f"  Success: {rate:.1f}%  Adjusted: {adj_rate:.1f}%")

    return {"gana": gana_name, "total": len(tools), "ok": ok, "expected": expected,
            "errors": errors, "timeouts": timeouts, "exceptions": exceptions, "skipped": skipped,
            "rate": round(rate, 1), "adj_rate": round(adj_rate, 1),
            "results": results}

# Run
all_results = []
ganas_to_run = sorted(gana_tools.keys()) if not target_gana else [target_gana]

for gana in ganas_to_run:
    res = run_gana(gana, gana_tools[gana])
    all_results.append(res)

# Print final summary
print(f"\n{'='*70}")
print("  FINAL SUMMARY")
print(f"{'='*70}")
print(f"  {'Gana':30s} {'Tools':>5} {'OK':>5} {'Exp':>5} {'Err':>5} {'T/O':>5} {'Exc':>5} {'Rate':>7} {'Adj':>7}")
print(f"  {'-'*30} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*7} {'-'*7}")
for r in all_results:
    print(f"  {r['gana']:30s} {r['total']:5d} {r['ok']:5d} {r['expected']:5d} {r['errors']:5d} {r['timeouts']:5d} {r['exceptions']:5d} {r['rate']:6.1f}% {r['adj_rate']:6.1f}%")

# Save
outpath = f"/tmp/gana_benchmark_{int(time.time())}.json"
with open(outpath, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\n  Results saved to {outpath}")
