#!/usr/bin/env python3
"""
WhiteMagic v4 — Comprehensive Tool Evaluation Script

Calls every registered tool through the `wm` meta-tool and reports:
  - Tool name
  - Status (success / error / rpc_error)
  - Error message (if any)
  - Key response fields

Usage:
    python3 scripts/eval_all_tools.py [--store PATH] [--binary PATH] [-v]

Exit code 0 = all tools succeeded, 1 = some tools had errors.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


# ── Tool-specific test arguments ─────────────────────────────────────
# Tools that need specific args to avoid "missing required arg" errors.
# Tools not listed here are called with empty args ({}) — most read-only
# tools work fine with no args.
TOOL_ARGS = {
    # Memory
    "memory.create": {"content": "eval test memory"},
    "memory.read": {"id": "00000000-0000-0000-0000-000000000000"},
    "memory.delete": {"id": "00000000-0000-0000-0000-000000000000", "confirm": True},
    "memory.search": {"query": "test"},
    "memory.query": {"query": "tag:test"},
    "memory.associate": {"source": "00000000-0000-0000-0000-000000000000", "target": "00000000-0000-0000-0000-000000000000"},
    "memory.associations": {"id": "00000000-0000-0000-0000-000000000000"},
    "memory.batch_read": {"ids": ["00000000-0000-0000-0000-000000000000"]},
    "memory.nearby": {"query": "test memory"},
    "memory.update": {"id": "00000000-0000-0000-0000-000000000000", "tags": ["eval"]},
    "memory.tag": {"id": "00000000-0000-0000-0000-000000000000", "tags": ["eval"]},
    "memory.list": {"galaxy": "codex", "limit": 3},
    "memory.count": {"galaxy": "codex"},
    "memory.export": {"galaxy": "codex", "format": "json"},
    "memory.sort": {"galaxy": "codex"},
    "memory.filter": {"galaxy": "codex"},
    "memory.deduplicate": {"galaxy": "codex", "confirm": True},
    "memory.stats": {"galaxy": "codex"},
    "memory.tags": {"galaxy": "codex"},
    "memory.vector.search": {"memory_id": "00000000-0000-0000-0000-000000000000"},
    "memory.hybrid_recall": {"query": "test", "galaxy": "codex"},
    "memory.chat": {"query": "test"},

    # Session
    "session.start": {"name": "eval-session"},
    "session.end": {"session_id": "00000000-0000-0000-0000-000000000000"},
    "session.recall": {"session_id": "00000000-0000-0000-0000-000000000000"},
    "session.checkpoint": {"session_id": "00000000-0000-0000-0000-000000000000"},

    # Agents
    "agent.register": {"name": "eval-agent", "description": "eval test"},
    "agent.trust": {"agent_id": "eval-agent"},
    "agent.descriptions": {"agent_id": "eval-agent"},
    "agent.capabilities": {"agent_id": "eval-agent"},
    "agent.heartbeat": {"agent_id": "eval-agent"},
    "agent.heartbeat.history": {"agent_id": "eval-agent"},
    "agent.deregister": {"agent_id": "eval-agent"},

    # Tasks
    "task.distribute": {"task": "eval task"},

    # Galaxy — use different galaxies for transfer/merge
    "galaxy.purge": {"galaxy": "tutorial", "confirm": True},
    "galaxy.transfer": {"from_galaxy": "research", "to_galaxy": "codex", "confirm": True},
    "galaxy.merge": {"from_galaxy": "research", "to_galaxy": "codex"},
    "galaxy.import": {"galaxy": "tutorial", "memories": []},
    "galaxy.export": {"galaxy": "codex"},
    "galaxy.snapshot": {"galaxy": "codex"},
    "galaxy.restore": {"galaxy": "codex", "snapshot_id": "00000000-0000-0000-0000-000000000000", "confirm": True},
    "galaxy.health": {"galaxy": "codex"},
    "galaxy.stats": {"galaxy": "codex"},

    # Knowledge graph
    "kg.extract": {"id": "00000000-0000-0000-0000-000000000000"},
    "kg.query": {"entity": "test"},

    # Graph
    "graph.walk": {"start_id": "00000000-0000-0000-0000-000000000000"},
    "graph.propagate": {"seed_ids": ["00000000-0000-0000-0000-000000000000"]},

    # Reasoning
    "bicameral.reason": {"topic": "Is the sky blue?"},
    "reasoning.bicameral": {"topic": "Is the sky blue?"},
    "think": {"query": "What is WhiteMagic?"},
    "explain": {"topic": "What is WhiteMagic?"},

    # Pipeline
    "pipeline.create": {"name": "eval-pipeline", "steps": []},
    "pipeline.status": {"name": "eval-pipeline"},

    # Skill
    "skill.invoke": {"skill": "eval-skill"},

    # RSI
    "friction.log": {
        "what_happened": "eval test friction",
        "expected_behavior": "should work",
        "severity": "low",
        "category": "test",
        "tool_name": "eval",
    },
    "friction.review": {"category": "test"},
    "friction.resolve": {"friction_id": "00000000-0000-0000-0000-000000000000", "resolution_note": "fixed in eval"},
    "friction.auto_log": {"tool_name": "eval", "error": "test error", "latency_ms": 10.0},

    # Drive
    "drive.event": {"kind": "tool_success", "tool": "eval"},

    # Reflex
    "reflex.add": {
        "sensor_id": "eval-sensor",
        "actuator_id": "eval-actuator",
        "actuator_kind": "command",
        "condition": ">",
        "threshold": 100,
    },
    "reflex.dispatch": {"reflex_id": 1},

    # Sensor
    "sensor.read": {"sensor_id": "cpu_temp"},

    # Actuator
    "actuator.command": {"actuator_id": "eval-actuator", "value": 0},

    # Bus — valid Gan Ying Bus event type (from EventType::as_str)
    "bus.emit": {"event_type": "system_heartbeat", "source": "eval", "data": {}},
    "bus.recent": {"limit": 3},

    # Sangha — valid signal types from parse_signal_type()
    "sangha.discover": {"peer_id": "eval-peer", "address": "127.0.0.1:0"},
    "sangha.signal": {"signal_type": "memory_created", "source": "eval"},
    "sangha.chat": {"action": "read"},
    "sangha.locks": {"action": "list"},

    # Simulation
    "sim.mc": {"n_samples": 100, "seed": 42, "distributions": [{"kind": "normal", "mean": 0.0, "std_dev": 1.0}]},
    "sim.forecast": {"data": [1, 2, 3, 4, 5], "horizon": 3},
    "sim.counterfactual": {"pre": [1, 2, 3], "post": [2, 3, 4]},

    # Workspace — valid CoreId and EventType from parse_core_id/parse_event_type
    "workspace.publish": {"core": "citta", "event_type": "novel_detection", "salience": 0.5, "confidence": 0.8},

    # State
    "state.revert": {"snapshot_id": "00000000-0000-0000-0000-000000000000"},

    # Transaction
    "transaction.begin": {},
    "transaction.commit": {},
    "transaction.rollback": {"confirm": True},

    # Boundary
    "boundary.enforce": {"resource": "memory", "action": "read"},

    # Anti-loop
    "anti_loop.check": {"tool": "eval"},

    # Archaeology
    "archaeology.search": {"galaxy": "codex"},

    # Pattern
    "pattern.search": {"query": "test", "galaxy": "codex"},

    # Correlation
    "correlation.analyze": {"galaxy": "codex"},

    # Constellation
    "constellation.detect": {"galaxy": "codex"},

    # Emergence
    "emergence.scan": {"galaxy": "codex"},
    "emergence.report": {"galaxy": "codex"},

    # Association
    "association.mine": {"galaxy": "codex", "limit": 20, "max_comparisons": 1000},
    "memory.associate_mine": {"galaxy": "codex"},

    # Consolidation
    "consolidation.connect": {"galaxy": "codex"},
    "consolidation.compress": {"galaxy": "codex"},

    # Retention
    "retention.prune": {"galaxy": "codex"},

    # Serendipity
    "serendipity.surface": {"galaxy": "codex"},

    # Network
    "network.stats": {"galaxy": "codex"},
    "network.centrality": {"galaxy": "codex"},
    "network.clusters": {"galaxy": "codex"},

    # Pattern detect
    "pattern.detect": {"galaxy": "codex"},

    # Karma
    "karma.clear": {"keep": 10, "confirm": True},
}


def run_batch(binary, store, requests):
    """Run a batch of JSON-RPC requests and return parsed responses."""
    proc = subprocess.run(
        [binary, "serve", "--store", store],
        input="\n".join(requests) + "\n",
        capture_output=True, text=True, timeout=300,
    )
    responses = []
    for line in proc.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return responses


def parse_tool_response(d):
    """Parse a tools/call response dict into a result dict."""
    if d.get("error"):
        return {"status": "rpc_error", "error": d["error"].get("message", "unknown")[:120]}

    result = d.get("result", {})
    content = result.get("content", [])
    if not content:
        return {"status": "no_content", "error": "Empty content array"}

    try:
        text = content[0].get("text", "")
        parsed = json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError):
        return {"status": "raw_text", "error": content[0].get("text", "")[:100]}

    route = parsed.get("_wm_route", {})
    tool = route.get("tool", "?")
    status = parsed.get("status", "?")
    # Only treat 'message' as error when status indicates failure
    error = parsed.get("error", "")
    if not error and status not in ("success", "Completed", "ok", "partial", "?", "duplicate"):
        error = parsed.get("message", "")

    summary = {}
    for k in ["total", "entries", "proposals_generated", "total_vectors",
              "coverage_pct", "active_proposals", "healthy", "brain_wave",
              "galaxies", "nodes", "edges", "spotlight", "retention",
              "conclusion", "forecast", "mean", "std_dev", "steps",
              "agent_id", "session_id", "id", "harmony", "anomaly",
              "resolved_friction_count", "regression_count", "events"]:
        if k in parsed:
            v = parsed[k]
            if isinstance(v, str) and len(v) > 30:
                v = v[:30] + "..."
            elif isinstance(v, list):
                v = f"[{len(v)} items]"
            summary[k] = v

    return {
        "status": status,
        "tool": tool,
        "error": str(error)[:120] if error else "",
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate all WhiteMagic v4 MCP tools")
    parser.add_argument("--store", default=".whitemagic", help="LMDB store path")
    parser.add_argument("--binary", default="target/release/wm", help="wm binary path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all results, not just failures")
    parser.add_argument("--batch-size", type=int, default=5, help="Tools per batch (rate limit: ~20 per 15s)")
    parser.add_argument("--batch-delay", type=float, default=16.0, help="Seconds to wait between batches")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    binary = str(project_root / args.binary)
    store = str(project_root / args.store)

    if not Path(binary).exists():
        print(f"ERROR: Binary not found: {binary}")
        print("Run: cargo build --release -p wm-mcp")
        return 1

    print(f"WhiteMagic v4 — Comprehensive Tool Evaluation")
    print(f"Binary: {binary}")
    print(f"Store:  {store}")
    print(f"Batch:  {args.batch_size} tools / {args.batch_delay}s delay")
    print()

    # Phase 1: Get tool list
    print("Phase 1: Discovering tools...")
    init_and_list = [
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"wm","arguments":{"route":"tools.list"}}}',
    ]
    responses = run_batch(binary, store, init_and_list)

    tool_names = []
    for d in responses:
        if d.get("id") == 2 and not d.get("error"):
            p = json.loads(d["result"]["content"][0]["text"])
            tool_names = sorted([t["name"] for t in p["tools"]])
            break

    if not tool_names:
        print("ERROR: Could not retrieve tool list")
        return 1

    print(f"  Found {len(tool_names)} tools\n")

    # Phase 1.5: Create resources needed by tools that require existing IDs
    print("Phase 1.5: Creating test resources...")
    setup_reqs = ['{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}']

    # Create memory1 → for memory.read/tag/update/associations/associate/batch_read/kg.extract
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "memory.create", "args": {"content": "eval test memory for ID capture"}}},
    }))
    # Create memory2 → for memory.delete (separate so it doesn't delete memory1 before tag/update run)
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 10, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "memory.create", "args": {"content": "eval test memory for delete"}}},
    }))
    # Register agent1 → for agent.capabilities/descriptions/heartbeat/trust
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "agent.register", "args": {"name": "eval-agent", "description": "eval test agent"}}},
    }))
    # Register agent2 → for agent.deregister (separate so it doesn't delete agent1 before descriptions/trust run)
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 11, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "agent.register", "args": {"name": "eval-agent-2", "description": "eval test agent for deregister"}}},
    }))
    # Log a friction entry → get its ID for friction.resolve
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "friction.log", "args": {
            "what_happened": "eval test friction for ID capture",
            "expected_behavior": "should work", "severity": "low",
            "category": "test", "tool_name": "eval",
        }}},
    }))
    # Take a galaxy snapshot → for galaxy.restore
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "galaxy.snapshot", "args": {"galaxy": "codex"}}},
    }))
    # Take a state snapshot → for state.revert
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "state.snapshot", "args": {}}},
    }))
    # List sensors → for sensor.read
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "sensor.list", "args": {}}},
    }))
    # List actuators → for actuator.command
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 8, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "actuator.list", "args": {}}},
    }))
    # List skills → for skill.invoke
    setup_reqs.append(json.dumps({
        "jsonrpc": "2.0", "id": 9, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": "skill.list", "args": {}}},
    }))

    setup_responses = run_batch(binary, store, setup_reqs)
    time.sleep(args.batch_delay)  # Wait for rate limiter to reset

    # Extract IDs from setup responses
    captured_ids = {}
    for d in setup_responses:
        rid = d.get("id")
        if rid is None or rid == 1 or d.get("error"):
            continue
        try:
            p = json.loads(d["result"]["content"][0]["text"])
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if rid == 2 and "id" in p:
            captured_ids["memory_id"] = p["id"]
        elif rid == 10 and "id" in p:
            captured_ids["memory_delete_id"] = p["id"]
        elif rid == 3 and "agent_id" in p:
            captured_ids["agent_id"] = p["agent_id"]
        elif rid == 11 and "agent_id" in p:
            captured_ids["agent_deregister_id"] = p["agent_id"]
        elif rid == 4 and "id" in p:
            captured_ids["friction_id"] = p["id"]
        elif rid == 5 and "snapshot_id" in p:
            captured_ids["galaxy_snapshot_id"] = p["snapshot_id"]
        elif rid == 6 and "snapshot_id" in p:
            captured_ids["state_snapshot_id"] = p["snapshot_id"]
        elif rid == 7:
            # sensor.list — extract first sensor_id
            sensors = p.get("sensors", p.get("list", []))
            if isinstance(sensors, list) and sensors:
                s = sensors[0]
                sid = s.get("id", s.get("sensor_id", s.get("name", ""))) if isinstance(s, dict) else str(s)
                if sid:
                    captured_ids["sensor_id"] = sid
        elif rid == 8:
            # actuator.list — extract first actuator_id
            actuators = p.get("actuators", p.get("list", []))
            if isinstance(actuators, list) and actuators:
                a = actuators[0]
                aid = a.get("id", a.get("actuator_id", a.get("name", ""))) if isinstance(a, dict) else str(a)
                if aid:
                    captured_ids["actuator_id"] = aid
        elif rid == 9:
            # skill.list — extract first skill name
            skills = p.get("skills", p.get("list", []))
            if isinstance(skills, list) and skills:
                sk = skills[0]
                sname = sk.get("name", sk.get("skill", "")) if isinstance(sk, dict) else str(sk)
                if sname:
                    captured_ids["skill_name"] = sname

    print(f"  Captured IDs: {captured_ids}")

    # Update TOOL_ARGS with captured IDs
    if "memory_id" in captured_ids:
        mid = captured_ids["memory_id"]
        TOOL_ARGS["memory.read"] = {"id": mid}
        TOOL_ARGS["memory.tag"] = {"id": mid, "tags": ["eval"]}
        TOOL_ARGS["memory.update"] = {"id": mid, "tags": ["eval"]}
        TOOL_ARGS["memory.associations"] = {"id": mid}
        TOOL_ARGS["memory.associate"] = {"source": mid, "target": mid}
        TOOL_ARGS["memory.batch_read"] = {"ids": [mid]}
    if "memory_delete_id" in captured_ids:
        TOOL_ARGS["memory.delete"] = {"id": captured_ids["memory_delete_id"], "confirm": True}
    if "agent_id" in captured_ids:
        aid = captured_ids["agent_id"]
        TOOL_ARGS["agent.descriptions"] = {"agent_id": aid}
        TOOL_ARGS["agent.capabilities"] = {"agent_id": aid}
        TOOL_ARGS["agent.trust"] = {"agent_id": aid}
        TOOL_ARGS["agent.heartbeat"] = {"agent_id": aid}
        TOOL_ARGS["agent.heartbeat.history"] = {"agent_id": aid}
    if "agent_deregister_id" in captured_ids:
        TOOL_ARGS["agent.deregister"] = {"agent_id": captured_ids["agent_deregister_id"]}
    if "friction_id" in captured_ids:
        TOOL_ARGS["friction.resolve"] = {"friction_id": captured_ids["friction_id"], "resolution_note": "fixed in eval"}
    if "galaxy_snapshot_id" in captured_ids:
        TOOL_ARGS["galaxy.restore"] = {"galaxy": "codex", "snapshot_id": captured_ids["galaxy_snapshot_id"]}
    if "state_snapshot_id" in captured_ids:
        TOOL_ARGS["state.revert"] = {"snapshot_id": captured_ids["state_snapshot_id"]}
    if "sensor_id" in captured_ids:
        TOOL_ARGS["sensor.read"] = {"sensor_id": captured_ids["sensor_id"]}
    if "actuator_id" in captured_ids:
        TOOL_ARGS["actuator.command"] = {"actuator_id": captured_ids["actuator_id"], "value": 0}
    if "skill_name" in captured_ids:
        TOOL_ARGS["skill.invoke"] = {"skill": captured_ids["skill_name"]}
    if "memory_id" in captured_ids:
        TOOL_ARGS["kg.extract"] = {"id": captured_ids["memory_id"]}

    # Track tools that will fail because no hardware/data is available
    no_resource_tools = set()
    if "sensor_id" not in captured_ids:
        no_resource_tools.add("sensor.read")
    if "actuator_id" not in captured_ids:
        no_resource_tools.add("actuator.command")
    if "skill_name" not in captured_ids:
        no_resource_tools.add("skill.invoke")

    print()

    # Phase 2: Call each tool in batches
    # Each batch: initialize + up to batch_size tool calls
    # Rate limiter allows ~20 calls per 15s, so batch_size=15 with 16s delay is safe
    print(f"Phase 2: Calling all {len(tool_names)} tools via wm meta-tool...")

    all_results = {}
    t0 = time.time()
    num_batches = (len(tool_names) + args.batch_size - 1) // args.batch_size

    for batch_idx in range(num_batches):
        start = batch_idx * args.batch_size
        end = min(start + args.batch_size, len(tool_names))
        batch_tools = tool_names[start:end]

        # Build requests: initialize + tool calls
        batch_reqs = ['{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}']
        for i, name in enumerate(batch_tools, start=2):
            tool_args = TOOL_ARGS.get(name, {})
            req = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "wm",
                    "arguments": {"route": name, "args": tool_args},
                },
            }
            batch_reqs.append(json.dumps(req))

        batch_num = batch_idx + 1
        first_tool = batch_tools[0]
        last_tool = batch_tools[-1]
        print(f"  Batch {batch_num}/{num_batches} ({len(batch_tools)} tools: {first_tool}..{last_tool})...", flush=True)

        responses = run_batch(binary, store, batch_reqs)

        # Match responses to tools by id (id=2 → first tool, id=3 → second, etc.)
        for d in responses:
            rid = d.get("id")
            if rid is None or rid == 1:
                continue
            tool_idx_in_batch = rid - 2
            if 0 <= tool_idx_in_batch < len(batch_tools):
                name = batch_tools[tool_idx_in_batch]
                all_results[name] = parse_tool_response(d)

        if batch_idx < num_batches - 1:
            time.sleep(args.batch_delay)

    elapsed = time.time() - t0

    # Phase 3: Report
    print(f"\nPhase 3: Results (elapsed: {elapsed:.1f}s)\n")
    print(f"{'#':>3}  {'Tool':<30} {'Status':<12} {'Error/Summary'}")
    print("-" * 100)

    success_count = 0
    error_count = 0
    missing_count = 0
    errors = []

    for i, name in enumerate(tool_names, 1):
        r = all_results.get(name)
        if r is None:
            missing_count += 1
            print(f"{i:>3}  {name:<30} {'MISSING':<12} No response received")
            errors.append((name, "No response received"))
            continue

        status = r["status"]
        error = r.get("error", "")
        summary = r.get("summary", {})

        if status in ("success", "Completed", "?", "ok", "partial", "resolved", "already_resolved") and not error:
            success_count += 1
            if args.verbose:
                s = " ".join(f"{k}={v}" for k, v in list(summary.items())[:3])
                print(f"{i:>3}  {name:<30} {status:<12} {s}")
        elif name in no_resource_tools and ("not found" in error.lower() or "not registered" in error.lower() or "unavailable" in error.lower()):
            success_count += 1
            if args.verbose:
                print(f"{i:>3}  {name:<30} {status:<12} (expected — no hardware/data)")
        elif name == "actuator.command" and "permission denied" in error.lower():
            success_count += 1
            if args.verbose:
                print(f"{i:>3}  {name:<30} {status:<12} (expected — no root access for hardware)")
        elif status in ("not_found",):
            # Expected when using fake UUIDs — not a real error
            success_count += 1
            if args.verbose:
                print(f"{i:>3}  {name:<30} {status:<12} (expected — fake UUID)")
        elif status == "duplicate":
            success_count += 1  # friction.log dedup is expected
            if args.verbose:
                print(f"{i:>3}  {name:<30} {status:<12} (expected dedup)")
        else:
            error_count += 1
            print(f"{i:>3}  {name:<30} {status:<12} {error}")
            errors.append((name, f"{status}: {error}" if error else status))

    print("-" * 100)
    print(f"\nSummary:")
    print(f"  Total tools:   {len(tool_names)}")
    print(f"  Success:       {success_count}")
    print(f"  Errors:        {error_count}")
    print(f"  Missing:       {missing_count}")
    print(f"  Success rate:  {success_count / len(tool_names) * 100:.1f}%")

    if errors:
        print(f"\n{'='*100}")
        print(f"Errors to investigate ({len(errors)}):")
        print(f"{'='*100}")
        for name, err in errors:
            print(f"  {name:<30} → {err}")

    return 0 if error_count == 0 and missing_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
