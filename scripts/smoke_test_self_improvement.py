#!/usr/bin/env python3
"""Comprehensive smoke test for WhiteMagic self-improvement systems.

Exercises:
  1. Skill self-improvement loop: forge → record failures → amend → evaluate → rollback
  2. KaizenEngine full analyze() including skill health proposals
  3. GunaBalanceMetric: record tones → measure → check balance
  4. EmergenceEngine: scan for emergent patterns
  5. DreamCycle: status check + single phase execution
  6. MCP dispatch: skill.amend, skill.history, skill.rollback, skill.evaluate

Usage:
    cd core && python ../scripts/smoke_test_self_improvement.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

# ── Environment setup ──────────────────────────────────────────────────────────
# Use a temp state root to avoid polluting production data
_tmpdir = tempfile.mkdtemp(prefix="wm_smoke_")
os.environ["WM_STATE_ROOT"] = _tmpdir
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_SKIP_POLYGLOT"] = "1"

# Ensure we can import whitemagic
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

# ── Helpers ────────────────────────────────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def ok(msg: str) -> None:
    print(f"  ✅ {msg}")

def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")

def fail(msg: str) -> None:
    print(f"  ❌ {msg}")

def info(msg: str) -> None:
    print(f"  ℹ️  {msg}")


# ── 1. Skill Self-Improvement Loop ────────────────────────────────────────────

def test_skill_self_improvement() -> bool:
    section("1. Skill Self-Improvement Loop")
    from whitemagic.core.intelligence.omni.chain_tracker import (
        ChainTracker,
        reset_chain_tracker,
    )
    from whitemagic.core.intelligence.omni.skill_forge import (
        ExecutionChain,
        GanaStep,
        SkillForge,
        get_skill_forge,
        reset_skill_forge,
    )

    reset_chain_tracker()
    reset_skill_forge()

    skill_dir = Path(_tmpdir) / "skills"
    forge = SkillForge(skill_library_path=skill_dir)

    # Override the global singleton so ChainTracker can find it
    import whitemagic.core.intelligence.omni.skill_forge as sf_mod
    sf_mod._forge = forge

    # Step 1: Forge a skill via ChainTracker
    info("Forging skill via ChainTracker (3 successful calls)...")
    tracker = ChainTracker()
    tracker.record("gana_neck", "create_memory", "store research data", True, 12.0)
    tracker.record("gana_ghost", "gnosis", "analyze patterns", True, 25.0)
    tracker.record("gana_winnowing_basket", "search_memories", "find connections", True, 18.0)
    tracker._last_flush = time.time() - 100

    forged = tracker.try_auto_forge()
    if forged is None:
        fail("Failed to forge skill from successful chain")
        return False
    ok(f"Forged skill: {forged.name} v{forged.version} ({len(forged.optimized_chain.steps)} steps)")

    # Step 2: Record failures against the skill directly
    info("Recording 5 failing executions against the skill...")
    skill_name = forged.name
    for i in range(5):
        forge.record_execution(
            skill_name, success=False, error="step 2 fails",
            steps_completed=1, total_steps=len(forged.optimized_chain.steps),
        )

    skill = forge.known_skills.get(skill_name)
    if skill is None:
        fail(f"Skill '{skill_name}' not found in known_skills after recording")
        return False
    exec_count = len(skill.execution_history)
    fail_count = sum(1 for e in skill.execution_history if not e.success)
    info(f"Execution history: {exec_count} total, {fail_count} failures")
    ok(f"Failure rate: {forge.get_failure_rate(skill.name):.0%}")

    # Step 3: Amend the skill
    info("Amending skill based on failure pattern...")
    proposal = forge.amend(skill.name)
    if proposal is None:
        fail("Amendment returned None — expected a proposal")
        return False
    ok(f"Amended: v{proposal.old_version} → v{proposal.new_version}")
    info(f"Changes: {'; '.join(proposal.changes)}")
    info(f"Failing steps identified: {proposal.failing_steps}")

    # Step 4: Evaluate the amendment
    info("Recording post-amendment successes...")
    for _ in range(5):
        forge.record_execution(skill.name, success=True)

    evaluation = forge.evaluate_amendment(skill.name)
    info(f"Evaluation: improved={evaluation['improved']}, recommendation={evaluation['recommendation']}")
    info(f"  Pre-amendment failure rate: {evaluation['pre_amendment_failure_rate']:.0%}")
    info(f"  Post-amendment failure rate: {evaluation['post_amendment_failure_rate']:.0%}")
    ok(f"Recommendation: {evaluation['recommendation']}")

    # Step 5: Test rollback
    info("Testing rollback to previous version...")
    rolled_back = forge.rollback(skill.name)
    if not rolled_back:
        fail("Rollback failed")
        return False
    skill = forge.known_skills[skill.name]
    ok(f"Rolled back to v{skill.version}, previous_versions: {len(skill.previous_versions)}")

    # Step 6: Check skill health
    info("Checking skill health metrics...")
    health = forge.get_skill_health()
    for h in health:
        info(f"  {h['name']}: v{h['version']}, failure_rate={h['failure_rate']:.0%}, "
             f"executions={h['recent_executions']}, needs_amendment={h['needs_amendment']}")

    ok("Skill self-improvement loop complete")
    return True


# ── 2. KaizenEngine Full Analysis ─────────────────────────────────────────────

def test_kaizen_engine() -> bool:
    section("2. KaizenEngine Full Analysis")
    from whitemagic.core.intelligence.synthesis.kaizen_engine import KaizenEngine

    # Use the temp DB (will be empty but won't crash)
    db_path = Path(_tmpdir) / "whitemagic.db"
    # Create a minimal DB so KaizenEngine doesn't fail
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT, title TEXT, importance REAL, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS tags (memory_id INTEGER, tag TEXT)")
    conn.commit()
    conn.close()

    engine = KaizenEngine(db_path=str(db_path))

    info("Running full kaizen analysis...")
    try:
        report = engine.analyze()
        info(f"Total proposals: {len(report.proposals)}")
        info(f"Metrics: {report.metrics}")

        # Group by category
        by_cat: dict[str, int] = {}
        for p in report.proposals:
            by_cat[p.category] = by_cat.get(p.category, 0) + 1

        for cat, count in by_cat.items():
            info(f"  Category '{cat}': {count} proposals")

        # Check for skill_health proposals specifically
        skill_proposals = [p for p in report.proposals if p.category == "skill_health"]
        if skill_proposals:
            ok(f"Found {len(skill_proposals)} skill_health proposals")
            for p in skill_proposals:
                info(f"  {p.title}")
                info(f"    Auto-fixable: {p.auto_fixable}, fix_action: {p.fix_action}")
        else:
            info("No skill_health proposals (expected if no failing skills in temp DB)")

        ok("KaizenEngine analysis complete")
        return True
    except Exception as e:
        fail(f"KaizenEngine failed: {e}")
        traceback.print_exc()
        return False


# ── 3. GunaBalanceMetric ──────────────────────────────────────────────────────

def test_guna_balance() -> bool:
    section("3. GunaBalanceMetric")
    from whitemagic.core.consciousness.guna_balance import GunaBalanceMetric

    gb = GunaBalanceMetric(window_size=20)

    info("Recording emotional tones...")
    # Record a mix of tones to see the balance
    tones = ["sattvic", "calm", "neutral", "rajasic", "rajasic", "tamasic",
             "tamasic", "tamasic", "frustrated", "curious", "sattvic", "neutral",
             "joyful", "active", "tamasic", "tamasic", "tamasic", "tamasic",
             "tamasic", "tamasic"]

    for tone in tones:
        gb.record_tone(tone)

    reading = gb.measure()
    info(f"Sattvic ratio: {reading.sattvic_ratio:.1%}")
    info(f"Rajasic ratio: {reading.rajasic_ratio:.1%}")
    info(f"Tamasic ratio: {reading.tamasic_ratio:.1%}")
    info(f"Balanced: {reading.balanced}")
    info(f"Correction action: {reading.correction_action or '(none needed)'}")

    status = gb.get_status()
    info(f"Samples: {status['samples']}")
    info(f"Corrections applied: {status['correction_count']}")

    report = gb.get_report()
    info(f"Report preview:\n{report[:200]}...")

    ok("GunaBalanceMetric test complete")
    return True


# ── 4. EmergenceEngine ────────────────────────────────────────────────────────

def test_emergence_engine() -> bool:
    section("4. EmergenceEngine")
    from whitemagic.core.intelligence.agentic.emergence_engine import EmergenceEngine

    engine = EmergenceEngine()

    info("Running emergence scan...")
    try:
        insights = engine.scan_for_emergence()
        info(f"Found {len(insights)} emergent insights")
        for i, insight in enumerate(insights[:5]):
            info(f"  Insight {i+1}: type={insight.insight_type}, confidence={insight.confidence:.2f}")
            info(f"    Description: {insight.description[:100]}...")
            if insight.tags:
                info(f"    Tags: {insight.tags[:5]}")

        if not insights:
            info("  (No emergent patterns detected — expected with empty memory DB)")
        ok("EmergenceEngine scan complete")
        return True
    except Exception as e:
        fail(f"EmergenceEngine failed: {e}")
        traceback.print_exc()
        return False


# ── 5. DreamCycle Status ──────────────────────────────────────────────────────

def test_dream_cycle() -> bool:
    section("5. DreamCycle Status")
    from whitemagic.core.dreaming.dream_cycle import DreamCycle

    dc = DreamCycle(idle_threshold_seconds=1.0)

    info("Checking dream cycle status (not started)...")
    status = dc.status()
    info(f"Running: {status['running']}")
    info(f"Total cycles: {status['total_cycles']}")
    info(f"Current phase: {status.get('current_phase', 'none')}")
    info(f"Idle threshold: {status['idle_threshold']}s")

    # Test a single phase execution (without starting the background thread)
    info("Executing single dream phase (triage)...")
    import asyncio
    try:
        result = asyncio.run(dc._run_phase())
        info(f"Phase result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        for key, val in (result or {}).items():
            if isinstance(val, dict):
                info(f"  {key}: {list(val.keys())}")
            else:
                info(f"  {key}: {val}")
        ok("Dream phase execution complete")
    except Exception as e:
        warn(f"Dream phase execution had issues (expected with empty DB): {e}")

    ok("DreamCycle test complete")
    return True


# ── 6. MCP Dispatch (skill.amend, skill.history, etc.) ────────────────────────

def test_mcp_dispatch() -> bool:
    section("6. MCP Dispatch — Skill Self-Improvement Tools")
    from whitemagic.core.intelligence.omni.skill_forge import (
        ExecutionChain,
        GanaStep,
        SkillForge,
        reset_skill_forge,
    )
    from whitemagic.tools.handlers.skill_forge import (
        handle_skill_amend,
        handle_skill_evaluate,
        handle_skill_history,
        handle_skill_rollback,
    )

    reset_skill_forge()

    skill_dir = Path(_tmpdir) / "skills_mcp"
    forge = SkillForge(skill_library_path=skill_dir)

    import whitemagic.core.intelligence.omni.skill_forge as sf_mod
    sf_mod._forge = forge

    # Forge a skill
    chain = ExecutionChain(
        intent="test workflow",
        steps=[
            GanaStep(mansion="NECK", operation="transform", context_key="create", parameters={}),
            GanaStep(mansion="GHOST", operation="analyze", context_key="review", parameters={}),
            GanaStep(mansion="WINNOWING_BASKET", operation="search", context_key="find", parameters={}),
        ],
        estimated_complexity=2.4,
        required_capabilities=[],
    )
    forge.forge(chain, name="dispatch_test_skill")

    # Record failures
    for _ in range(5):
        forge.record_execution("dispatch_test_skill", success=False, error="fail",
                               steps_completed=1, total_steps=3)

    # Test skill.history via handler
    info("Calling handle_skill_history()...")
    from unittest.mock import patch
    with patch("whitemagic.core.intelligence.omni.skill_forge.get_skill_forge", return_value=forge):
        result = handle_skill_history()
    info(f"Status: {result['status']}")
    info(f"Total skills: {result['total_skills']}")
    info(f"Needs amendment: {result['needs_amendment_count']}")
    for s in result.get("skills", []):
        info(f"  {s['name']}: failure_rate={s['failure_rate']:.0%}, needs_amendment={s['needs_amendment']}")
    ok("skill.history handler works")

    # Test skill.amend via handler
    info("Calling handle_skill_amend()...")
    with patch("whitemagic.core.intelligence.omni.skill_forge.get_skill_forge", return_value=forge):
        result = handle_skill_amend(name="dispatch_test_skill")
    info(f"Status: {result['status']}")
    info(f"Amended: {result.get('amended', 'N/A')}")
    if result.get("amended"):
        info(f"  v{result['old_version']} → v{result['new_version']}")
        info(f"  Changes: {result.get('changes', [])}")
    ok("skill.amend handler works")

    # Test skill.evaluate via handler
    info("Recording post-amendment successes and calling handle_skill_evaluate()...")
    for _ in range(5):
        forge.record_execution("dispatch_test_skill", success=True)
    with patch("whitemagic.core.intelligence.omni.skill_forge.get_skill_forge", return_value=forge):
        result = handle_skill_evaluate(name="dispatch_test_skill")
    info(f"Status: {result['status']}")
    info(f"Has amendment: {result.get('has_amendment')}")
    info(f"Improved: {result.get('improved')}")
    info(f"Recommendation: {result.get('recommendation')}")
    ok("skill.evaluate handler works")

    # Test skill.rollback via handler
    info("Calling handle_skill_rollback()...")
    with patch("whitemagic.core.intelligence.omni.skill_forge.get_skill_forge", return_value=forge):
        result = handle_skill_rollback(name="dispatch_test_skill")
    info(f"Status: {result['status']}")
    info(f"Rolled back: {result.get('rolled_back', 'N/A')}")
    ok("skill.rollback handler works")

    # Verify dispatch table entries exist
    info("Verifying dispatch table entries...")
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE
    from whitemagic.tools.prat_mappings import TOOL_TO_GANA

    for tool in ["skill.amend", "skill.history", "skill.rollback", "skill.evaluate"]:
        assert tool in DISPATCH_TABLE, f"Missing dispatch entry: {tool}"
        assert tool in TOOL_TO_GANA, f"Missing PRAT mapping: {tool}"
        assert TOOL_TO_GANA[tool] == "gana_ox", f"Wrong Gana for {tool}"
        ok(f"{tool} → dispatch + PRAT verified")

    ok("MCP dispatch test complete")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\nWhiteMagic Self-Improvement Smoke Test")
    print(f"Temp state root: {_tmpdir}")
    print(f"Python: {sys.version.split()[0]}")

    results: list[tuple[str, bool]] = []

    tests = [
        ("Skill Self-Improvement Loop", test_skill_self_improvement),
        ("KaizenEngine Full Analysis", test_kaizen_engine),
        ("GunaBalanceMetric", test_guna_balance),
        ("EmergenceEngine", test_emergence_engine),
        ("DreamCycle Status", test_dream_cycle),
        ("MCP Dispatch", test_mcp_dispatch),
    ]

    for name, fn in tests:
        try:
            success = fn()
            results.append((name, success))
        except Exception as e:
            fail(f"{name} crashed: {e}")
            traceback.print_exc()
            results.append((name, False))

    # Summary
    section("SUMMARY")
    passed = sum(1 for _, s in results if s)
    total = len(results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} — {name}")
    print(f"\n  {passed}/{total} tests passed\n")

    # Cleanup
    import shutil
    shutil.rmtree(_tmpdir, ignore_errors=True)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
