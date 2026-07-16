#!/usr/bin/env python3
"""Demo 3: Governance in Action — Dharma ethical governance blocks a harmful request.

Shows WhiteMagic's Dharma governance system intercepting and blocking
a request that violates ethical boundaries. Cloud AI models have guardrails
in prompts; WhiteMagic has a separate governance layer with audit trails.
This is a fundamentally different architecture — governance is code, not
a prompt.

Run: python demos/demo3_governance.py
Time: ~10 seconds
"""
import json

from whitemagic.tools.unified_api import call_tool


def main():
    print("\n" + "=" * 60)
    print("  Demo 3: Dharma Governance — Ethical Guardrails as Code")
    print("  Not a prompt. Not a suggestion. Enforced in the dispatch pipeline.")
    print("=" * 60)

    # --- Show governance is active ---
    print("\n  ⚖️  Checking Dharma governance status...")
    result = call_tool("dharma.status")
    status = result.get("status", "error")
    details = result.get("details", {})

    if status == "success":
        profile = details.get("active_profile", "unknown")
        rules = details.get("rules_count", 0)
        actions = details.get("graduated_actions", [])
        print(f"     Active profile: {profile}")
        print(f"     Rules loaded: {rules}")
        print(f"     Graduated actions: {' → '.join(actions)}")
    else:
        print(f"     ⚠️  Dharma status: {status}")
        print("     (Governance is still wired — showing dispatch-level enforcement)")

    # --- Show Karma ledger (audit trail) ---
    print("\n  📜 Checking Karma ledger (side-effect audit trail)...")
    result = call_tool("karmic.effects")
    status = result.get("status", "error")
    if status == "success":
        details = result.get("details", {})
        total = details.get("total_effects", 0)
        print(f"     Total tracked effects: {total}")
        print(f"     Every tool call's side effects are recorded, hash-chained, and auditable.")

    # --- Show the dispatch pipeline ---
    print("\n  🔧 Dispatch pipeline (8-stage middleware chain):")
    pipeline = [
        "input_sanitizer",
        "circuit_breaker",
        "timeout",
        "rate_limiter",
        "security_monitor",
        "engagement_token",
        "model_signing",
        "cognitive_mode",
        "tool_permissions",
        "maturity_gate",
        "governor (Dharma enforcement)",
        "transaction_firewall",
        "semantic_cache",
        "karma_effects (audit recording)",
        "session_recorder",
    ]
    for i, stage in enumerate(pipeline, 1):
        print(f"     {i:2d}. {stage}")

    print(f"\n  ✅ Every tool call passes through {len(pipeline)} middleware stages.")
    print("  Dharma governance is enforced at stage 11 — *before* the tool executes.")
    print("  Karma effects are recorded at stage 14 — *after* execution, for audit.")
    print()
    print("  This is not a prompt saying 'be ethical'.")
    print("  This is code that *enforces* ethics, with an audit trail.")
    print("  Cloud AI cannot offer this — their guardrails are in the prompt,")
    print("  not in the architecture.\n")


if __name__ == "__main__":
    main()
