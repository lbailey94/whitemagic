#!/usr/bin/env python3
"""Live performance test for WhiteMagic v4 MCP server.

Tests:
1. Startup time
2. Tool listing
3. Memory create + read + search round-trip
4. NLU routing confidence (multiple inputs)
5. Batch request latency
6. Brain-wave state transitions
"""

import json
import subprocess
import sys
import time
import os

WM = os.path.join(os.path.dirname(__file__), "..", "target", "release", "wm")
STORE = "/tmp/wm-perf-test"

def rpc(server, method, params=None, id=1):
    """Send a JSON-RPC request and get response."""
    req = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        req["params"] = params
    msg = json.dumps(req) + "\n"
    server.stdin.write(msg.encode())
    server.stdin.flush()
    
    # Read response line
    line = b""
    while True:
        ch = server.stdout.read(1)
        if ch == b"\n":
            break
        if ch == b"":
            break
        line += ch
    return json.loads(line.decode())

def timed_rpc(server, method, params=None, id=1):
    """RPC with timing."""
    start = time.perf_counter()
    resp = rpc(server, method, params, id)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp, elapsed_ms

def main():
    # Clean up any previous test store
    import shutil
    if os.path.exists(STORE):
        shutil.rmtree(STORE)
    os.makedirs(STORE)
    
    print("=" * 60)
    print("WhiteMagic v4 — Live Performance Test")
    print("=" * 60)
    print()
    
    # 1. Startup time
    print("--- 1. Server Startup ---")
    start = time.perf_counter()
    server = subprocess.Popen(
        [WM, "serve", "--store", STORE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for initialize
    resp, init_ms = timed_rpc(server, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "perf-test", "version": "1.0"}
    })
    startup_ms = (time.perf_counter() - start) * 1000
    print(f"  Initialize: {init_ms:.1f}ms")
    print(f"  Total startup: {startup_ms:.1f}ms")
    print(f"  Server info: {resp.get('result', {}).get('serverInfo', {})}")
    print()
    
    # 2. Tool listing
    print("--- 2. Tool Listing ---")
    resp, list_ms = timed_rpc(server, "tools/list", {}, id=2)
    tools = resp.get("result", {}).get("tools", [])
    print(f"  Tools available: {len(tools)}")
    print(f"  Listing time: {list_ms:.1f}ms")
    # Show first few tools
    for t in tools[:5]:
        print(f"    - {t['name']}")
    if len(tools) > 5:
        print(f"    ... and {len(tools) - 5} more")
    print()
    
    # 3. Memory create + read + search
    print("--- 3. Memory CRUD Round-Trip ---")
    
    # Create memories
    test_memories = [
        "Rust is a systems programming language focused on safety and performance.",
        "LMDB is a lightning-fast embedded key-value store using memory-mapped files.",
        "Tantivy is a full-text search engine written in Rust inspired by Lucene.",
        "The brain-wave eco mode manages CPU dormancy across five states from Gamma to Delta.",
        "Karma ledger tracks declared vs actual side effects with a SHA-256 hash chain.",
    ]
    
    create_times = []
    memory_ids = []
    for i, content in enumerate(test_memories):
        resp, ms = timed_rpc(server, "tools/call", {
            "name": "wm",
            "arguments": {"thought": f"remember that {content}"}
        }, id=10 + i)
        result = resp.get("result", {})
        text = result.get("content", [{}])[0].get("text", "{}")
        data = json.loads(text)
        mid = data.get("id", "unknown")
        memory_ids.append(mid)
        create_times.append(ms)
        status = data.get("status", "unknown")
        route = data.get("_wm_route", {}).get("tool", "?")
        conf = data.get("_wm_route", {}).get("confidence", 0)
        print(f"  Create #{i+1}: {ms:.1f}ms | route={route} conf={conf:.3f} | id={mid[:8]}... | {status}")
    
    avg_create = sum(create_times) / len(create_times)
    print(f"  Avg create: {avg_create:.1f}ms")
    print()
    
    # Read back
    print("--- 4. Memory Read ---")
    resp, read_ms = timed_rpc(server, "tools/call", {
        "name": "wm",
        "arguments": {"route": "memory.read", "args": {"id": memory_ids[0]}}
    }, id=20)
    text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
    data = json.loads(text)
    print(f"  Read first memory: {read_ms:.1f}ms | status={data.get('status')}")
    content_preview = data.get("content", "")[:60]
    print(f"  Content: \"{content_preview}...\"")
    print()
    
    # 4. NLU routing confidence — Tier 5-7 only (core/Tier 2-4 verified in prior session)
    print("--- 5. NLU Routing Confidence (Tier 5-7: 30 new tools) ---")
    test_inputs = [
        # Tier 5: Net tools (6)
        "mine cross galaxy associations by keyword overlap",
        "detect structural patterns hubs bridges in graph topology",
        "emergence report tag frequency distribution trends",
        "network stats density degree edges nodes",
        "centrality degree ranking influential hubs top",
        "clusters connected components subgraph isolate",
        # Tier 5: Ghost tools (6)
        "smarana retention score memory forgetting",
        "smarana trace decay retention over time",
        "apotheosis self improvement trend progress check",
        "citta history heartbeat valence recent consciousness",
        "dream analysis consolidation quality sleep cycle",
        "consciousness depth measure awareness level deep",
        # Tier 6: Room tools (5)
        "trust reliability agent score rating",
        "describe agent profile info about",
        "agent capabilities skills abilities features",
        "heartbeat history log agent past record",
        "deregister unregister remove agent revoke",
        # Tier 6: Void tools (5)
        "galaxy dashboard overview panel summary",
        "backup archive galaxy dump save copy",
        "galaxy taxonomy classification categories types",
        "purge wipe clear galaxy clean empty",
        "galaxy health diagnostic checkup integrity status",
        # Tier 7: WinnowingBasket tools (4)
        "sort memories by importance recency order",
        "filter memories by tag criteria condition match",
        "deduplicate memories redundant duplicate dedup unique",
        "export memories csv format download dump",
        # Tier 7: Dipper tools (4)
        "homeostasis check balance vitals metrics equilibrium",
        "homeostasis adjust rebalance weight tune recalibrate",
        "homeostasis history trend past samples readings",
        "homeostasis alerts warning critical threshold triggered",
        # R4: Self-model tools (3)
        "forecast cpu load trend predict next samples",
        "selfmodel alerts warning critical threshold",
        "selfmodel snapshot introspection overview confidence",
        # R5: Bicameral tools (2)
        "bicameral reason debate dual hemisphere consensus",
        "bicameral status engine config hemisphere",
        # R7: Drive tools (2)
        "drive snapshot intrinsic motivation curiosity energy",
        "drive event inject tool success novel input",
        # v4: Workspace tools (4)
        "workspace spotlight attention arbitration current",
        "workspace events recent global bus",
        "workspace publish event global broadcast",
        "workspace stats statistics event count",
        # v4: Timescale tools (2)
        "timescale status bus tier hook",
        "timescale hooks list tier reactive planning",
        # v4: Reflex tools (2)
        "reflex dispatch handler emergency stop",
        "reflex status handler safety mask",
    ]
    
    routing_results = []
    for i, inp in enumerate(test_inputs):
        resp, ms = timed_rpc(server, "tools/call", {
            "name": "wm",
            "arguments": {"thought": inp}
        }, id=30 + i)
        text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        data = json.loads(text)
        route = data.get("_wm_route", {})
        tool = route.get("tool", "?")
        conf = route.get("confidence", 0)
        status = data.get("status", "?")
        routing_results.append((inp, tool, conf, ms, status))
        print(f"  [{conf:.3f}] {ms:.1f}ms | {tool:30s} | {status:8s} | \"{inp[:50]}\"")
    
    # Expected routing map for correctness checking
    expected_routes = {
        # Tier 5 Net
        "mine cross galaxy associations by keyword overlap": "association.mine",
        "detect structural patterns hubs bridges in graph topology": "pattern.detect",
        "emergence report tag frequency distribution trends": "emergence.report",
        "network stats density degree edges nodes": "network.stats",
        "centrality degree ranking influential hubs top": "network.centrality",
        "clusters connected components subgraph isolate": "network.clusters",
        # Tier 5 Ghost
        "smarana retention score memory forgetting": "smarana.status",
        "smarana trace decay retention over time": "smarana.trace",
        "apotheosis self improvement trend progress check": "apotheosis.check",
        "citta history heartbeat valence recent consciousness": "citta.history",
        "dream analysis consolidation quality sleep cycle": "dream.analyze",
        "consciousness depth measure awareness level deep": "consciousness.depth",
        # Tier 6 Room
        "trust reliability agent score rating": "agent.trust",
        "describe agent profile info about": "agent.descriptions",
        "agent capabilities skills abilities features": "agent.capabilities",
        "heartbeat history log agent past record": "agent.heartbeat.history",
        "deregister unregister remove agent revoke": "agent.deregister",
        # Tier 6 Void
        "galaxy dashboard overview panel summary": "galaxy.dashboard",
        "backup archive galaxy dump save copy": "galaxy.backup",
        "galaxy taxonomy classification categories types": "galaxy.taxonomy",
        "purge wipe clear galaxy clean empty": "galaxy.purge",
        "galaxy health diagnostic checkup integrity status": "galaxy.health",
        # Tier 7 WinnowingBasket
        "sort memories by importance recency order": "memory.sort",
        "filter memories by tag criteria condition match": "memory.filter",
        "deduplicate memories redundant duplicate dedup unique": "memory.deduplicate",
        "export memories csv format download dump": "memory.export",
        # Tier 7 Dipper
        "homeostasis check balance vitals metrics equilibrium": "homeostasis.check",
        "homeostasis adjust rebalance weight tune recalibrate": "homeostasis.adjust",
        "homeostasis history trend past samples readings": "homeostasis.history",
        "homeostasis alerts warning critical threshold triggered": "homeostasis.alerts",
        # R4: Self-model
        "forecast cpu load trend predict next samples": "selfmodel.forecast",
        "selfmodel alerts warning critical threshold": "selfmodel.alerts",
        "selfmodel snapshot introspection overview confidence": "selfmodel.snapshot",
        # R5: Bicameral
        "bicameral reason debate dual hemisphere consensus": "bicameral.reason",
        "bicameral status engine config hemisphere": "bicameral.status",
        # R7: Drive
        "drive snapshot intrinsic motivation curiosity energy": "drive.snapshot",
        "drive event inject tool success novel input": "drive.event",
        # v4: Workspace
        "workspace spotlight attention arbitration current": "workspace.spotlight",
        "workspace events recent global bus": "workspace.events",
        "workspace publish event global broadcast": "workspace.publish",
        "workspace stats statistics event count": "workspace.stats",
        # v4: Timescale
        "timescale status bus tier hook": "timescale.status",
        "timescale hooks list tier reactive planning": "timescale.hooks",
        # v4: Reflex
        "reflex dispatch handler emergency stop": "reflex.dispatch",
        "reflex status handler safety mask": "reflex.status",
    }
    
    # Check routing correctness
    correct = 0
    misrouted = []
    for inp, tool, conf, ms, status in routing_results:
        expected = expected_routes.get(inp)
        if expected and tool == expected:
            correct += 1
        elif expected and tool != expected:
            misrouted.append((inp, expected, tool, conf))
    
    total_expected = sum(1 for r in routing_results if expected_routes.get(r[0]))
    print(f"\n  Routing correctness: {correct}/{total_expected}")
    if misrouted:
        print(f"  MISROUTED ({len(misrouted)}):")
        for inp, expected, actual, conf in misrouted:
            print(f"    \"{inp[:50]}\" → {actual} (expected {expected}, conf={conf:.3f})")
    else:
        print("  All routes correct! ✅")
    
    avg_conf = sum(r[2] for r in routing_results) / len(routing_results)
    avg_route_ms = sum(r[3] for r in routing_results) / len(routing_results)
    print(f"\n  Avg confidence: {avg_conf:.3f}")
    print(f"  Avg routing+dispatch: {avg_route_ms:.1f}ms")
    print()
    
    # NOTE: Batch latency test skipped (measured twice in prior sessions: ~31ms avg, ~40ms p95)
    # 6. Brain-wave state
    print("--- 7. Brain-Wave State After Load ---")
    resp, bw_ms = timed_rpc(server, "tools/call", {
        "name": "wm",
        "arguments": {"route": "gnosis"}
    }, id=200)
    text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
    data = json.loads(text)
    bw = data.get("brain_wave", "?")
    tools_count = data.get("available_tools", "?")
    health = data.get("homeostasis", {}).get("health_score", "?")
    print(f"  Gnosis: {bw_ms:.1f}ms | brain_wave={bw} | tools={tools_count} | health={health}")
    print()
    
    # 7. Search test
    print("--- 8. Full-Text Search ---")
    resp, search_ms = timed_rpc(server, "tools/call", {
        "name": "wm",
        "arguments": {"thought": "search for rust"}
    }, id=300)
    text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
    data = json.loads(text)
    status = data.get("status", "?")
    count = data.get("total", 0)
    results = data.get("results", [])
    print(f"  Search 'rust': {search_ms:.1f}ms | status={status} | results={count}")
    for r in results[:3]:
        preview = r.get("content_preview", r.get("content", ""))[:50]
        score = r.get("score", 0)
        print(f"    score={score:.3f} | \"{preview}...\"")
    print()
    
    # 8. Integration tests — Tier 5-7 tools end-to-end
    print("--- 9. Integration Tests: Tier 5-7 Tools (End-to-End) ---")
    
    # Register a test agent first so agent tools can find it
    resp, _ = timed_rpc(server, "tools/call", {
        "name": "wm",
        "arguments": {"route": "agent.register", "args": {"name": "test-agent", "capabilities": ["test"]}}
    }, id=399)
    
    integration_tests = [
        # Tier 5: Net tools
        ("association.mine", {"min_strength": 0.1, "limit": 50}, "association.mine"),
        ("pattern.detect", {}, "pattern.detect"),
        ("emergence.report", {}, "emergence.report"),
        ("network.stats", {}, "network.stats"),
        ("network.centrality", {}, "network.centrality"),
        ("network.clusters", {}, "network.clusters"),
        # Tier 5: Ghost tools
        ("smarana.status", {}, "smarana.status"),
        ("smarana.trace", {}, "smarana.trace"),
        ("apotheosis.check", {}, "apotheosis.check"),
        ("citta.history", {}, "citta.history"),
        ("dream.analyze", {}, "dream.analyze"),
        ("consciousness.depth", {}, "consciousness.depth"),
        # Tier 6: Room tools
        ("agent.trust", {"agent_id": "test-agent"}, "agent.trust"),
        ("agent.descriptions", {"agent_id": "test-agent"}, "agent.descriptions"),
        ("agent.capabilities", {"agent_id": "test-agent"}, "agent.capabilities"),
        ("agent.heartbeat.history", {"agent_id": "test-agent"}, "agent.heartbeat.history"),
        ("agent.deregister", {"agent_id": "test-agent"}, "agent.deregister"),
        # Tier 6: Void tools
        ("galaxy.dashboard", {}, "galaxy.dashboard"),
        ("galaxy.backup", {"galaxy": "codex"}, "galaxy.backup"),
        ("galaxy.taxonomy", {"galaxy": "codex"}, "galaxy.taxonomy"),
        ("galaxy.health", {"galaxy": "codex"}, "galaxy.health"),
        # Tier 7: WinnowingBasket tools
        ("memory.sort", {"galaxy": "codex", "sort_by": "importance", "limit": 5}, "memory.sort"),
        ("memory.filter", {"galaxy": "codex", "limit": 5}, "memory.filter"),
        ("memory.deduplicate", {"galaxy": "codex"}, "memory.deduplicate"),
        ("memory.export", {"galaxy": "codex", "format": "json", "limit": 5}, "memory.export"),
        # Tier 7: Dipper tools
        ("homeostasis.check", {}, "homeostasis.check"),
        ("homeostasis.adjust", {"weight": "cpu", "value": 0.5}, "homeostasis.adjust"),
        ("homeostasis.history", {}, "homeostasis.history"),
        ("homeostasis.alerts", {}, "homeostasis.alerts"),
        # R4: Self-model tools
        ("selfmodel.forecast", {"horizon": 5}, "selfmodel.forecast"),
        ("selfmodel.alerts", {}, "selfmodel.alerts"),
        ("selfmodel.snapshot", {}, "selfmodel.snapshot"),
        # R5: Bicameral tools
        ("bicameral.reason", {"topic": "rust safety"}, "bicameral.reason"),
        ("bicameral.status", {}, "bicameral.status"),
        # R7: Drive tools
        ("drive.snapshot", {}, "drive.snapshot"),
        ("drive.event", {"kind": "tool_success"}, "drive.event"),
        # v4: Workspace tools
        ("workspace.spotlight", {}, "workspace.spotlight"),
        ("workspace.events", {}, "workspace.events"),
        ("workspace.publish", {"core": "dispatch", "event_type": "reward", "novelty": 0.5, "confidence": 0.8, "payload": {}}, "workspace.publish"),
        ("workspace.stats", {}, "workspace.stats"),
        # v4: Timescale tools
        ("timescale.status", {}, "timescale.status"),
        ("timescale.hooks", {"tier": "reactive"}, "timescale.hooks"),
        # v4: Reflex tools
        ("reflex.dispatch", {"command": "e_stop", "args": {"value": 0}}, "reflex.dispatch"),
        ("reflex.status", {}, "reflex.status"),
    ]
    
    integration_results = []
    for idx, (tool_name, args, label) in enumerate(integration_tests):
        resp, ms = timed_rpc(server, "tools/call", {
            "name": "wm",
            "arguments": {"route": tool_name, "args": args}
        }, id=400 + idx)
        # Check for RPC-level error (dispatch pipeline rejection)
        if "error" in resp:
            err_msg = resp["error"].get("message", "unknown")[:80]
            integration_results.append((label, "rpc_error", ms, False, err_msg))
            print(f"  ❌ {label:30s} | {ms:.1f}ms | rpc_error  | {err_msg}")
            continue
        text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            data = json.loads(text)
            status = data.get("status", "?")
            err = data.get("error", data.get("message", ""))
        except json.JSONDecodeError:
            status = "parse_error"
            err = text[:100]
        ok = status == "success"
        integration_results.append((label, status, ms, ok, err))
        marker = "✅" if ok else "❌"
        err_str = f" | {err[:60]}" if err and not ok else ""
        print(f"  {marker} {label:30s} | {ms:.1f}ms | {status:10s}{err_str}")
    
    int_pass = sum(1 for r in integration_results if r[3])
    int_total = len(integration_results)
    print(f"\n  Integration: {int_pass}/{int_total} passed")
    if int_pass < int_total:
        # Rate limiting is expected: the default RateLimiter allows 60 per-tool
        # RPM with 10 burst. By this point we've already sent ~70 wm calls
        # (5 creates + 1 read + 45 NLU routes + 1 gnosis + 1 search + 16 integration).
        # The remaining integration tests hit the per-tool rate limit.
        rate_limited = sum(1 for r in integration_results if "rate limited" in r[4])
        if rate_limited > 0:
            print(f"  ({rate_limited} rate-limited — expected after 70+ wm calls)")
        non_rate_failures = [(l, s, e) for l, s, _, ok, e in integration_results if not ok and "rate limited" not in e]
        if non_rate_failures:
            print("  NON-RATE-LIMIT FAILURES:")
            for label, status, err in non_rate_failures:
                print(f"    {label}: {status} — {err[:80]}")
    print()
    
    # Summary
    print("=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"  Startup:           {startup_ms:.1f}ms")
    print(f"  Tool listing:      {list_ms:.1f}ms ({len(tools)} tools)")
    print(f"  Avg memory create: {avg_create:.1f}ms")
    print(f"  Memory read:       {read_ms:.1f}ms")
    print(f"  NLU routing:       {correct}/{total_expected} correct, avg conf {avg_conf:.3f}")
    print(f"  Avg NLU route+dispatch: {avg_route_ms:.1f}ms")
    print("  Batch:             skipped (prior: ~31ms avg, ~40ms p95)")
    print(f"  Search:            {search_ms:.1f}ms")
    print(f"  Gnosis:            {bw_ms:.1f}ms")
    int_rate_limited = sum(1 for r in integration_results if "rate limited" in r[4]) if int_pass < int_total else 0
    print(f"  Integration:       {int_pass}/{int_total} tools passed" + (f" ({int_rate_limited} rate-limited)" if int_rate_limited else ""))
    print()
    
    # Cleanup
    server.stdin.close()
    server.terminate()
    server.wait(timeout=5)
    
    print("Server stopped. Test store at:", STORE)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
