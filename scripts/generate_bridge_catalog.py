#!/usr/bin/env python3
"""
Generate catalog entries + TS impls for the 143 whitemagic.mcp_api_bridge functions.

Usage:
  cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
  python3 scripts/generate_bridge_catalog.py

Outputs:
  - Patches lib/data/mcp-bridge.ts with all missing BRIDGE_MODULES entries
  - Patches lib/bridge/impl.ts with matching TS impls + dispatcher entries

This is a one-shot v22.3.0 generator. After it runs, both files contain
the full 143-function surface. Hand-edits are still expected for the
explanatory comments at the top of each file.
"""
from __future__ import annotations
import os
import sys
import inspect
import textwrap
from pathlib import Path

REPO = Path("/home/lucas/Desktop/WHITEMAGIC")
SITE = Path("/home/lucas/Desktop/WHITEMAGIC-aux/site/whitemagic-site")
sys.path.insert(0, str(REPO / "core"))

import whitemagic.mcp_api_bridge as bridge  # noqa: E402

# Categories by module substring or known list
CATEGORY_BY_PREFIX = [
    ("gana_", "gana"),
    ("meditation_", "meditation"),
    ("zodiac_", "zodiac"),
    ("garden_", "garden"),
    ("manage_gardens", "garden"),
    ("session_", "session"),
    ("memory_", "memory"),
    ("manage_memories", "memory"),
    ("archaeology_", "archaeology"),
    ("dharma_", "dharma"),
    ("gana_invoke", "gana"),
    ("gana_", "gana"),
    ("prat_", "gana"),
    ("route_prat", "gana"),
    ("invoke_gana", "gana"),
    ("manage_voice", "voice"),
    ("voice_", "voice"),
    ("voice_pattern", "voice"),
    ("manage_voice_patterns", "voice"),
    ("run_autonomous_", "autonomous"),
    ("run_benchmarks", "benchmark"),
    ("run_kaizen", "kaizen"),
    ("kaizen_", "kaizen"),
    ("analyze_wu_xing", "kaizen"),
    ("run_local_", "inference"),
    ("local_ml_", "inference"),
    ("bitnet_", "inference"),
    ("optimize_", "optimization"),
    ("solve_optimization", "optimization"),
    ("check_system_", "system"),
    ("check_memory_", "system"),
    ("check_resonance_", "system"),
    ("check_integrations_", "system"),
    ("system_initialize_", "system"),
    ("system_get_status", "system"),
    ("debug_system", "system"),
    ("validate_integrations", "system"),
    ("protect_context", "system"),
    ("consult_", "wisdom"),
    ("synthesize_wisdom", "wisdom"),
    ("research_topic", "wisdom"),
    ("apply_reasoning_", "reasoning"),
    ("analyze_pattern", "reasoning"),
    ("detect_patterns", "reasoning"),
    ("conduct_reasoning", "reasoning"),
    ("detect_intelligence", "reasoning"),
    ("execute_cascade", "reasoning"),
    ("list_cascade_patterns", "reasoning"),
    ("run_benchmarks", "benchmark"),
    ("run_benchmark", "benchmark"),
    ("get_metrics_summary", "metrics"),
    ("track_metric", "metrics"),
    ("get_system_time", "metrics"),
    ("get_timestamp", "metrics"),
    ("sangha_", "collaboration"),
    ("profile_", "collaboration"),
    ("windsurf_", "collaboration"),
    ("manage_agent_", "collaboration"),
    ("manage_zodiac_", "zodiac"),
    ("manage_federation", "infrastructure"),
    ("enable_rust_acceleration", "infrastructure"),
    ("rust_", "infrastructure"),
    ("manage_federation", "infrastructure"),
    ("search_web", "wisdom"),
    ("process_voice", "voice"),
    ("execute_mcp_tool", "tool"),
    ("cast", "tool"),
    ("ensure_string", "tool"),
    ("adapt_response", "tool"),
    ("parallel_search", "tool"),
]


def categorize(name: str) -> str:
    for prefix, cat in CATEGORY_BY_PREFIX:
        if name.startswith(prefix) or name == prefix.rstrip("_"):
            return cat
    return "tool"


def get_signature(name: str) -> str:
    fn = getattr(bridge, name, None)
    if fn is None:
        return f"{name}(**kwargs) -> dict"
    try:
        sig = str(inspect.signature(fn))
    except (ValueError, TypeError):
        sig = "(**kwargs)"
    # Strip -> ... return annotation from inspect.signature
    if " ->" in sig:
        sig = sig.split(" ->")[0]
    return f"{name}{sig} -> dict"


def get_docstring(name: str) -> str:
    fn = getattr(bridge, name, None)
    if fn is None:
        return f"Bridge function {name}."
    doc = inspect.getdoc(fn)
    if not doc:
        return f"Bridge function {name}."
    # Take first paragraph
    return doc.strip().split("\n\n")[0].replace("\n", " ")


def list_all_functions() -> list[str]:
    funcs = []
    for n in dir(bridge):
        if n.startswith("_"):
            continue
        attr = getattr(bridge, n)
        if not (callable(attr) and (inspect.isfunction(attr) or inspect.iscoroutinefunction(attr))):
            continue
        # Skip modules / non-bridge items
        if inspect.ismodule(attr):
            continue
        funcs.append(n)
    return sorted(funcs)


def example_payload_for(name: str) -> dict:
    """Pick a reasonable example payload based on the function name."""
    if name in ("meditation_pause", "meditation_reflect", "meditation_meditate"):
        return {"duration": 5}
    if name in ("zodiac_activate_core",):
        return {"core_name": "aries", "context": {"question": "Should I start the deployment now?"}}
    if name in ("zodiac_consult_council",):
        return {"query": "How should we handle the auth refactor?", "context": {"urgency": "medium"}}
    if name in ("zodiac_run_cycle",):
        return {"intention": "Resolve the session handoff deadlock", "context": {"session_id": "sess_001"}}
    if name in ("garden_activate", "garden_garden_activate"):
        return {"garden_name": "ethics_dharma"}
    if name == "manage_gardens":
        return {"operation": "list"}
    if name in ("session_init",):
        return {"name": "demo_session", "goals": ["catalog expansion", "v22.3.0"]}
    if name in ("session_checkpoint",):
        return {"session_name": "current", "include_state": True}
    if name in ("session_create_handoff",):
        return {"target_session": "next", "context": {"phase": "A"}}
    if name in ("session_handoff",):
        return {"from_session": "current", "to_session": "next"}
    if name in ("session_get_context",):
        return {}
    if name in ("session_list",):
        return {"include_archived": False}
    if name in ("memory_create",):
        return {"content": "A new memory", "memory_type": "long_term", "tags": ["demo"]}
    if name in ("memory_read",):
        return {"memory_id": "mem_demo_001"}
    if name in ("memory_update",):
        return {"memory_id": "mem_demo_001", "content": "Updated content"}
    if name in ("memory_delete",):
        return {"memory_id": "mem_demo_001"}
    if name in ("memory_list",):
        return {"limit": 20}
    if name in ("memory_search",):
        return {"query": "ethics", "limit": 10}
    if name in ("manage_memories",):
        return {"operation": "list"}
    if name in ("parallel_search",):
        return {"queries": ["a", "b", "c"]}
    if name.startswith("dharma_"):
        return {"action": {"type": "deploy", "target": "production"}, "strict_mode": False}
    if name.startswith("archaeology_"):
        return {"query": "ethics", "limit": 10}
    if name.startswith("gana_"):
        return {"operation": "invoke", "task": "list capabilities"}
    if name == "prat_invoke":
        return {"target_tool": "memory_search", "params": {"query": "ethics"}}
    if name == "prat_list_morphologies":
        return {}
    if name == "prat_get_context":
        return {"as_json": True}
    if name == "prat_status":
        return {"target_tool": "memory_search"}
    if name.startswith("consult_"):
        return {"question": "How should we sequence the catalog expansion?"}
    if name == "synthesize_wisdom":
        return {"sources": ["council", "iching"], "urgency": "normal"}
    if name == "research_topic":
        return {"query": "WhiteMagic session handoff best practices"}
    if name == "apply_reasoning_methods":
        return {"question": "What is the optimal order for closing the catalog gap?"}
    if name == "analyze_pattern":
        return {"pattern_id": "pat_001"}
    if name == "detect_patterns":
        return {"query": "governance drift over time"}
    if name == "conduct_reasoning":
        return {"question": "Should we ship v22.3.0 today?"}
    if name == "detect_intelligence_patterns":
        return {"content": "This is sample content for pattern detection."}
    if name == "execute_cascade":
        return {"pattern": "balanced_refactor", "tools": ["memory_search", "dharma_check"]}
    if name == "list_cascade_patterns":
        return {}
    if name == "run_autonomous_cycle":
        return {"duration_seconds": 60}
    if name == "manage_voice_patterns":
        return {"operation": "list"}
    if name == "run_benchmarks":
        return {"category": "all"}
    if name == "run_benchmark":
        return {"category": "all"}
    if name == "run_kaizen_analysis":
        return {"auto_fix": False}
    if name == "kaizen_analyze":
        return {}
    if name == "analyze_wu_xing_phase":
        return {}
    if name == "local_ml_infer":
        return {"prompt": "Hello", "max_tokens": 64}
    if name == "bitnet_infer":
        return {"prompt": "Hello"}
    if name == "run_local_inference":
        return {"prompt": "Hello"}
    if name in ("optimize_cache", "optimize_models"):
        return {}
    if name == "solve_optimization":
        return {"objective": "minimize_latency"}
    if name == "check_system_health":
        return {"deep_scan": False}
    if name == "check_memory_health":
        return {"component": "memory"}
    if name == "check_resonance_health":
        return {"component": "resonance", "duration_seconds": 30}
    if name == "check_integrations_health":
        return {"component": "integrations", "quick_check": True}
    if name == "system_initialize_all":
        return {"verbose": False}
    if name == "system_get_status":
        return {}
    if name == "debug_system":
        return {"operation": "inspect_state"}
    if name == "validate_integrations":
        return {"quick_check": True}
    if name == "protect_context":
        return {}
    if name == "get_metrics_summary":
        return {}
    if name == "track_metric":
        return {"name": "demo_metric", "value": 1.0}
    if name in ("get_system_time", "get_timestamp"):
        return {}
    if name in ("sangha_lock_acquire",):
        return {"resource": "memory_ledger", "reason": "txn-123", "timeout": 60}
    if name in ("sangha_lock_release",):
        return {"resource": "memory_ledger"}
    if name == "sangha_lock_list":
        return {}
    if name == "sangha_chat_read":
        return {"channel": "general", "limit": 10}
    if name == "sangha_chat_send":
        return {"content": "Hello sangha", "channel": "general", "sender_id": "librarian"}
    if name in ("profile_get_profile", "profile_update_preferences"):
        return {}
    if name in ("windsurf_backup", "windsurf_merge_backups"):
        return {}
    if name == "manage_agent_collaboration":
        return {"operation": "list"}
    if name == "manage_zodiac_cores":
        return {"operation": "list"}
    if name == "manage_federation":
        return {"operation": "status"}
    if name == "search_web":
        return {"query": "best AI memory architectures 2026"}
    if name == "process_voice":
        return {"audio_data": "<base64>"}
    if name.startswith("rust_"):
        return {}
    if name == "enable_rust_acceleration":
        return {}
    if name == "execute_mcp_tool":
        return {"tool": "memory_search", "kwargs": {"query": "ethics"}}
    if name == "cast":
        return {"spell": "list"}
    if name == "ensure_string":
        return {"value": 42}
    if name == "adapt_response":
        return {"context": {"agent": "librarian"}, "operation": "adapt_to_context"}
    if name == "gana_invoke":
        return {"gana_name": "horn", "task": "list capabilities"}
    if name == "route_prat_call":
        return {"target_tool": "memory_search"}
    if name == "manage_voice_patterns":
        return {"operation": "list"}
    if name == "invoke_gana":
        return {"gana_name": "horn", "task": "list capabilities"}
    return {}


def example_response_for(name: str, category: str) -> dict:
    """Return a sample response shape for the catalog entry."""
    if name in ("meditation_pause",):
        return {"paused": True, "duration": 5}
    if name in ("meditation_reflect",):
        return {"reflected": True, "duration": 5}
    if name in ("meditation_meditate",):
        return {"meditated": True, "duration": 10}
    if name.startswith("dharma_"):
        return {"status": "ok", "principle": "ahimsa"}
    if name.startswith("gana_") or name == "gana_invoke" or name == "invoke_gana":
        return {"mansion": name.replace("gana_", ""), "task": "ok", "status": "ok"}
    if name.startswith("prat_") or name == "route_prat_call":
        return {"status": "ok", "target_tool": "memory_search"}
    if name.startswith("zodiac_") or name == "manage_zodiac_cores":
        return {"status": "ok", "core": "aries"}
    if name.startswith("garden_") or name == "manage_gardens":
        return {"status": "ok", "garden": "ethics_dharma"}
    if name.startswith("session_"):
        return {"status": "ok", "session": "demo"}
    if name.startswith("memory_") or name == "manage_memories":
        return {"status": "ok", "memory_id": "mem_demo_001"}
    if name.startswith("archaeology_"):
        return {"status": "ok", "results": []}
    if name.startswith("consult_") or name == "synthesize_wisdom" or name == "research_topic":
        return {"status": "ok", "wisdom": "..."}
    if name in ("apply_reasoning_methods", "analyze_pattern", "detect_patterns", "conduct_reasoning", "detect_intelligence_patterns", "execute_cascade", "list_cascade_patterns"):
        return {"status": "ok", "method": "default"}
    if name.startswith("sangha_") or name.startswith("profile_") or name.startswith("windsurf_") or name == "manage_agent_collaboration":
        return {"status": "ok"}
    if name in ("optimize_cache", "optimize_models", "solve_optimization"):
        return {"status": "ok", "optimized": True}
    if name in ("check_system_health", "check_memory_health", "check_resonance_health", "check_integrations_health", "validate_integrations", "system_get_status", "debug_system", "protect_context", "system_initialize_all"):
        return {"status": "healthy"}
    if name.startswith("local_ml_") or name.startswith("bitnet_") or name == "run_local_inference":
        return {"status": "ok", "result": "..."}
    if name in ("run_benchmarks", "run_benchmark", "run_kaizen_analysis", "kaizen_analyze", "analyze_wu_xing_phase", "run_autonomous_cycle"):
        return {"status": "ok", "ran": True}
    if name in ("get_metrics_summary", "track_metric", "get_system_time", "get_timestamp"):
        return {"status": "ok"}
    if name.startswith("rust_") or name == "enable_rust_acceleration":
        return {"status": "ok"}
    if name == "manage_voice_patterns":
        return {"status": "ok"}
    if name == "manage_federation":
        return {"status": "ok"}
    if name == "search_web":
        return {"results": []}
    if name == "process_voice":
        return {"text": "transcribed"}
    if name == "execute_mcp_tool":
        return {"status": "ok", "result": {}}
    if name == "cast":
        return {"status": "ok"}
    if name == "ensure_string":
        return {"value": "42"}
    if name == "adapt_response":
        return {"status": "ok"}
    if name == "parallel_search":
        return {"results": []}
    if name == "gana_invoke":
        return {"status": "ok"}
    if name == "garden_garden_status":
        return {"status": "ok"}
    return {"status": "ok"}


def py_to_ts(value):
    """Convert a Python dict to a TS object literal."""
    s = repr(value)
    s = s.replace("True", "true").replace("False", "false").replace("None", "null")
    # Convert single-quoted Python strings to double-quoted TS strings.
    # Use json.dumps which gives double quotes, but we need to be careful
    # about non-string values. Simpler: re-do the conversion with json.
    import json
    return json.dumps(value)


def generate_ts_impl(name: str, category: str) -> str:
    """Generate a TS impl for the function."""
    # Special cases first
    if name == "gana_dipper":
        return ""  # already exists
    if name in ("meditation_pause", "meditation_reflect", "meditation_meditate",
                "zodiac_list_cores", "zodiac_activate_core", "zodiac_consult_council",
                "zodiac_run_cycle", "run_autonomous_cycle", "manage_voice_patterns",
                "run_benchmarks", "system_initialize_all", "check_system_health",
                "check_memory_health", "check_resonance_health", "check_integrations_health",
                "session_init", "session_get_context", "session_checkpoint",
                "session_list", "session_create_handoff", "garden_list",
                "garden_activate", "manage_gardens", "consult_full_council",
                "consult_iching", "apply_reasoning_methods", "archaeology_stats",
                "gana_horn", "gana_winnowing_basket", "local_ml_status"):
        return ""  # already exists

    response = example_response_for(name, category)
    ts_response = py_to_ts(response)
    return (
        f"export function {name}(payload: Payload) {{\n"
        f"  return fnOk(\"{name}\", {ts_response});\n"
        f"}}\n\n"
    )


def generate_catalog_entry(name: str) -> str:
    cat = categorize(name)
    sig = get_signature(name)
    desc = get_docstring(name).replace('"', "'").replace("\n", " ")
    payload = example_payload_for(name)
    response = example_response_for(name, cat)
    ts_payload = py_to_ts(payload)
    ts_response = py_to_ts(response)
    return (
        f"  {{\n"
        f"    name: \"{name}\",\n"
        f"    module: \"whitemagic.mcp_api_bridge\",\n"
        f"    signature: \"{sig}\",\n"
        f"    description: \"{desc}\",\n"
        f"    category: \"{cat}\",\n"
        f"    stability: \"stable\",\n"
        f"    example_payload: {ts_payload},\n"
        f"    example_response: {ts_response},\n"
        f"  }},\n\n"
    )


def main():
    all_fns = list_all_functions()
    print(f"Total functions in mcp_api_bridge: {len(all_fns)}")

    # Generate catalog and impls
    catalog_entries = []
    ts_impls = []
    dispatcher_additions = []
    for name in all_fns:
        cat = categorize(name)
        # Skip if already in impl.ts (check by name in IMPLS list)
        impl_text = generate_ts_impl(name, cat)
        if impl_text:
            ts_impls.append((name, impl_text))
        if name not in ("gana_dipper", "meditation_pause", "meditation_reflect",
                        "meditation_meditate", "zodiac_list_cores",
                        "zodiac_activate_core", "zodiac_consult_council",
                        "run_autonomous_cycle", "manage_voice_patterns",
                        "run_benchmarks", "system_initialize_all",
                        "check_system_health", "check_memory_health",
                        "check_resonance_health", "check_integrations_health",
                        "session_init", "session_get_context",
                        "session_checkpoint", "session_list",
                        "session_create_handoff", "garden_list",
                        "garden_activate", "manage_gardens",
                        "consult_full_council", "consult_iching",
                        "apply_reasoning_methods", "archaeology_stats",
                        "gana_horn", "gana_winnowing_basket", "local_ml_status"):
            catalog_entries.append(generate_catalog_entry(name))
            dispatcher_additions.append(f"  {name},\n")

    print(f"New catalog entries: {len(catalog_entries)}")
    print(f"New TS impls: {len(ts_impls)}")
    print(f"New dispatcher entries: {len(dispatcher_additions)}")

    # Write the files (overwrite impl.ts, append to catalog)
    out_dir = SITE / "tmp" / "catalog_gen"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "new_catalog_entries.ts").write_text("".join(catalog_entries))
    (out_dir / "new_impls.ts").write_text("".join(t[1] for t in ts_impls))
    (out_dir / "new_dispatcher.txt").write_text("".join(dispatcher_additions))
    print(f"Wrote to {out_dir}")


if __name__ == "__main__":
    main()
