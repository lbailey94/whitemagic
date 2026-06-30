#!/usr/bin/env python3
"""Clone Army Training Exercises — Deploy armies across tactical and strategic scenarios.

Measures real-world performance with live LLM (Ollama qwen2.5:7b).
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("train_clone_armies")

# Ensure we use the right model
os.environ.setdefault("WM_LLM_MODEL", "qwen2.5:7b")


def print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_result(label: str, value: any, indent: int = 2) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}:")
        for k, v in value.items():
            print(f"{prefix}  {k}: {v}")
    elif isinstance(value, list):
        print(f"{prefix}{label}: [{len(value)} items]")
        for item in value[:3]:
            print(f"{prefix}  - {item}")
    else:
        print(f"{prefix}{label}: {value}")


# ---------------------------------------------------------------------------
# Scenario 1: AsyncThoughtCloneArmy — Tactical Reconnaissance
# ---------------------------------------------------------------------------


async def scenario_1_thought_clones():
    """Deploy thought clone army for multi-strategy analysis of a tactical problem."""
    print_header("SCENARIO 1: Thought Clone Army — Tactical Reconnaissance")
    print(
        "Objective: Analyze 'How to optimize SQLite query performance for a memory system'"
    )
    print("Deployment: 3 clones × 3 tiers (9 total), 14 strategies\n")

    from whitemagic.edge.thought_clones_async import (
        AsyncThoughtCloneArmy,
        CloneConfig,
        CloneTier,
    )

    config = CloneConfig(max_clones=3, max_concurrent_api_calls=3)
    army = AsyncThoughtCloneArmy(config=config)

    start = time.perf_counter()
    result = await army.parallel_explore_tiered(
        "How to optimize SQLite query performance for a memory system with 100K records?",
        num_clones=3,
    )
    elapsed = time.perf_counter() - start

    print(f"Best path (tier={result.metadata.get('tier', '?')}):")
    print_result("Strategy", result.strategy)
    print_result("Confidence", f"{result.confidence:.3f}")
    print_result("Tokens", result.tokens)
    print_result("Duration", f"{result.duration_ms:.0f}ms")
    print_result("LLM Used", result.metadata.get("llm_used", False))
    print_result("Model", result.metadata.get("model", "N/A"))
    print(f"\nContent preview:\n  {result.content[:300]}...")

    print(f"\nTotal elapsed: {elapsed:.1f}s")
    print_result("Army Stats", army.get_stats())

    return {
        "scenario": "thought_clones",
        "confidence": result.confidence,
        "llm_used": result.metadata.get("llm_used", False),
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Scenario 2: ImmortalClone — Strategic Persistent Loop
# ---------------------------------------------------------------------------


async def scenario_2_immortal_clone():
    """Deploy an ImmortalClone with LLM-driven action selection on a real task."""
    print_header("SCENARIO 2: ImmortalClone — Strategic Persistent Loop")
    print("Objective: Analyze and improve a Python file's error handling")
    print("Deployment: 1 ImmortalClone, max 3 iterations, LLM-driven actions\n")

    from whitemagic.agents.immortal_clone_v2 import (
        ImmortalClone,
        Task,
        CampaignVictoryTracker,
    )

    # Create a test file with poor error handling
    tmpdir = tempfile.mkdtemp()
    test_file = os.path.join(tmpdir, "buggy_code.py")
    with open(test_file, "w") as f:
        f.write("""import sqlite3

def get_data(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories")
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_data(db_path, data):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memories VALUES (?)", (data,))
    conn.commit()
    conn.close()
""")

    task = Task(
        id="improve-error-handling",
        type="code_improvement",
        target=test_file,
        victory_conditions=["error_handling_added", "resource_cleanup_verified"],
    )

    tracker = CampaignVictoryTracker(
        victory_conditions=[
            {
                "id": "error_handling_added",
                "description": "Error handling added to code",
            },
            {
                "id": "resource_cleanup_verified",
                "description": "Resource cleanup verified",
            },
        ],
    )
    clone = ImmortalClone(
        clone_id=1,
        task=task,
        victory_tracker=tracker,
        max_iterations=3,
    )

    start = time.perf_counter()
    result = clone.execute_persistent_loop()
    elapsed = time.perf_counter() - start

    # execute_persistent_loop returns a single ActionResult
    actions_count = result.data.get("iterations", 0) if result.data else 0
    print(f"Clone executed {actions_count} iterations in {elapsed:.1f}s")
    print_result(
        "Final result",
        {
            "success": result.success,
            "error": (result.error or "none")[:100],
            "vcs_met": result.data.get("vcs_met", []) if result.data else [],
        },
    )

    met = clone.check_victory_conditions()
    print(f"\nVictory conditions met: {met}")
    print(f"VC count: {len(met)}/{len(task.victory_conditions)}")

    return {
        "scenario": "immortal_clone",
        "actions_taken": actions_count,
        "vcs_met": len(met),
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Scenario 3: BicameralReasoner — Strategic Dual-Hemisphere Analysis
# ---------------------------------------------------------------------------


async def scenario_3_bicameral():
    """Deploy BicameralReasoner for dual-hemisphere strategic analysis."""
    print_header("SCENARIO 3: BicameralReasoner — Strategic Dual-Hemisphere Analysis")
    print(
        "Objective: Reason about 'Should WhiteMagic use vector DB or SQLite FTS5 for search?'"
    )
    print(
        "Deployment: 2 left (analytical) + 2 right (creative) clones, 2 debate rounds, LLM synthesis\n"
    )

    from whitemagic.core.intelligence.bicameral import get_bicameral_reasoner

    reasoner = get_bicameral_reasoner(
        left_clones=2, right_clones=2, max_debate_rounds=2
    )

    start = time.perf_counter()
    result = await reasoner.reason(
        "Should WhiteMagic use a dedicated vector database (like ChromaDB) or stick with SQLite FTS5 + embedding search for memory retrieval?",
    )
    elapsed = time.perf_counter() - start

    print_result(
        "Left hemisphere",
        {
            "strategy": result.left_analysis.strategy,
            "confidence": f"{result.left_analysis.confidence:.3f}",
            "content_preview": result.left_analysis.content[:200],
        },
    )
    print_result(
        "Right hemisphere",
        {
            "strategy": result.right_analysis.strategy,
            "confidence": f"{result.right_analysis.confidence:.3f}",
            "content_preview": result.right_analysis.content[:200],
        },
    )
    print_result("Dominant", result.dominant_hemisphere)
    print_result("Tension", f"{result.tension_score:.3f}")
    print_result("Final confidence", f"{result.final_confidence:.3f}")
    print_result("Duration", f"{result.duration_ms:.0f}ms")
    print(f"\nSynthesis preview:\n  {result.synthesis[:400]}...")

    print(f"\nTotal elapsed: {elapsed:.1f}s")

    return {
        "scenario": "bicameral",
        "dominant": result.dominant_hemisphere,
        "tension": result.tension_score,
        "confidence": result.final_confidence,
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Scenario 4: CodeWritingClone — Tactical File Operations
# ---------------------------------------------------------------------------


async def scenario_4_code_writing():
    """Deploy CodeWritingArmy for parallel file generation."""
    print_header("SCENARIO 4: CodeWritingClone Army — Tactical File Operations")
    print("Objective: Generate 20 Python module stubs in parallel")
    print("Deployment: 4 clones, 20 write operations via Rayon\n")

    from whitemagic.optimization.rust_code_writing import (
        deploy_writing_army,
        code_writing_available,
    )

    if not code_writing_available():
        print("Rust CodeWritingClone not available — skipping")
        return {"scenario": "code_writing", "skipped": True}

    tmpdir = tempfile.mkdtemp()

    module_templates = [
        (
            "memory/scanner.py",
            '"""Memory scanner module {i}."""\n\ndef scan():\n    pass\n',
        ),
        (
            "memory/analyzer.py",
            '"""Memory analyzer module {i}."""\n\ndef analyze():\n    pass\n',
        ),
        (
            "memory/optimizer.py",
            '"""Memory optimizer module {i}."""\n\ndef optimize():\n    pass\n',
        ),
    ]

    operations = []
    for i in range(20):
        mod_path, mod_template = module_templates[i % 3]
        filename = mod_path.replace(".py", f"_{i}.py")
        operations.append(
            {
                "op_type": "write",
                "target_file": f"output/{filename}",
                "content": mod_template.format(i=i),
            }
        )

    start = time.perf_counter()
    results = deploy_writing_army(
        tmpdir, operations, clone_count=4, army_id="training-army"
    )
    elapsed = time.perf_counter() - start

    succeeded = sum(1 for r in results if r["success"])
    total_lines = sum(r.get("lines_written", 0) for r in results)

    print(f"Deployed {len(operations)} write operations across 4 clones")
    print_result("Succeeded", f"{succeeded}/{len(operations)}")
    print_result("Total lines written", total_lines)
    print_result("Elapsed", f"{elapsed * 1000:.1f}ms")
    print_result("Throughput", f"{len(operations) / elapsed:.0f} ops/sec")

    # Verify files exist
    import pathlib

    files_created = list(pathlib.Path(tmpdir).rglob("*.py"))
    print_result("Files on disk", len(files_created))

    return {
        "scenario": "code_writing",
        "operations": len(operations),
        "succeeded": succeeded,
        "throughput_ops": len(operations) / elapsed,
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Scenario 5: ToolBandit — Strategy Learning Feedback
# ---------------------------------------------------------------------------


async def scenario_5_bandit_learning():
    """Deploy thought clones and check if ToolBandit learned from outcomes."""
    print_header("SCENARIO 5: ToolBandit — Strategy Learning Feedback Loop")
    print("Objective: Deploy clones, then check bandit learned which strategies work")
    print("Deployment: 2 rounds of 2 clones each, then inspect bandit stats\n")

    from whitemagic.edge.thought_clones_async import AsyncThoughtCloneArmy, CloneConfig
    from whitemagic.tools.handlers.tool_bandit import get_tool_bandit, reset_tool_bandit

    reset_tool_bandit()
    bandit = get_tool_bandit()

    config = CloneConfig(max_clones=2, max_concurrent_api_calls=2)
    army = AsyncThoughtCloneArmy(config=config)

    # Round 1
    print("Round 1: Deploying 2 clones for 'How to improve code review processes?'...")
    start = time.perf_counter()
    await army.parallel_explore(
        "How to improve code review processes?", 2, use_tokio=False
    )
    elapsed1 = time.perf_counter() - start
    print(f"  Round 1 done in {elapsed1:.1f}s")

    # Round 2
    print("Round 2: Deploying 2 clones for 'How to optimize API response times?'...")
    start = time.perf_counter()
    await army.parallel_explore(
        "How to optimize API response times?", 2, use_tokio=False
    )
    elapsed2 = time.perf_counter() - start
    print(f"  Round 2 done in {elapsed2:.1f}s")

    # Check bandit state
    all_stats = bandit.get_all_stats()
    clone_stats = {k: v for k, v in all_stats.items() if k.startswith("clone.")}
    print(f"\nBandit learned {len(clone_stats)} clone strategy outcomes:")
    for name, stats in sorted(
        clone_stats.items(), key=lambda x: x[1]["expected_success_rate"], reverse=True
    )[:5]:
        print(
            f"  {name}: α={stats['alpha']:.1f} β={stats['beta']:.1f} "
            f"success_rate={stats['expected_success_rate']:.3f} calls={stats['total_calls']}"
        )

    # Get recommendations
    recommendations = bandit.recommend_clone_strategies(
        "analyze and deploy code", clone_type="thought", k=5
    )
    print(f"\nTop 5 recommended strategies for next deployment:")
    for rec in recommendations:
        print(
            f"  {rec['strategy']}: sample={rec['sample']:.3f} ev={rec['expected_value']:.3f} calls={rec['total_calls']}"
        )

    return {
        "scenario": "bandit_learning",
        "strategies_learned": len(clone_stats),
        "total_calls": sum(s["total_calls"] for s in clone_stats.values()),
        "elapsed_s": elapsed1 + elapsed2,
    }


# ---------------------------------------------------------------------------
# Scenario 6: WarRoom Execute — Full Campaign
# ---------------------------------------------------------------------------


async def scenario_6_war_room():
    """Execute a WarRoom campaign with real ImmortalClone deployment."""
    print_header("SCENARIO 6: WarRoom Execute — Full Campaign Deployment")
    print(
        "Objective: Execute a campaign to 'audit and fix error handling in a codebase'"
    )
    print("Deployment: WarRoom → GasTownOrchestrator → ImmortalClones\n")

    from whitemagic.tools.handlers.war_room import handle_war_room_execute

    tmpdir = tempfile.mkdtemp()
    test_file = os.path.join(tmpdir, "target.py")
    with open(test_file, "w") as f:
        f.write("def risky():\n    return 1/0\n")

    campaign = {
        "name": "error_handling_audit",
        "objective": f"Audit and fix error handling in {test_file}",
        "victory_conditions": [
            {
                "id": "error_handling_added",
                "description": "Error handling added",
                "target": test_file,
            },
        ],
    }

    start = time.perf_counter()
    result = handle_war_room_execute(
        campaign=campaign,
        max_clones=2,
        max_iterations=3,
        dashboard_enabled=False,
    )
    elapsed = time.perf_counter() - start

    print_result("Status", result.get("status"))
    if result.get("status") == "success":
        print_result("Total actions", result.get("total", 0))
        print_result("Succeeded", result.get("succeeded", 0))
        results = result.get("results", [])
        for i, r in enumerate(results[:3]):
            print_result(
                f"  Result {i + 1}",
                {
                    "success": r.get("success"),
                    "error": (r.get("error") or "none")[:80],
                },
            )
    else:
        print_result("Error", result.get("message", "unknown"))

    print(f"\nTotal elapsed: {elapsed:.1f}s")

    return {
        "scenario": "war_room",
        "status": result.get("status"),
        "total_actions": result.get("total", 0),
        "succeeded": result.get("succeeded", 0),
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    print_header("WHITE MAGIC CLONE ARMY TRAINING EXERCISES")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"LLM: Ollama qwen2.5:7b at http://localhost:11434")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # Verify LLM
    from whitemagic.inference.local_llm import LocalLLM

    llm = LocalLLM()
    if not llm.is_available:
        print("FATAL: Ollama not available. Run 'ollama serve' first.")
        sys.exit(1)
    print(f"LLM verified: {llm.model}")

    results = []

    # Run scenarios
    scenarios = [
        ("Thought Clones", scenario_1_thought_clones),
        ("ImmortalClone", scenario_2_immortal_clone),
        ("BicameralReasoner", scenario_3_bicameral),
        ("CodeWritingClone", scenario_4_code_writing),
        ("Bandit Learning", scenario_5_bandit_learning),
        ("WarRoom Execute", scenario_6_war_room),
    ]

    for name, func in scenarios:
        try:
            print(f"\n>>> Starting {name}...")
            result = await func()
            results.append(result)
            print(f"<<< {name} complete")
        except Exception as e:
            logger.error("Scenario %s failed: %s", name, e, exc_info=True)
            results.append({"scenario": name, "error": str(e)})

    # Summary
    print_header("TRAINING EXERCISE SUMMARY")
    print(f"{'Scenario':<25} {'Status':<10} {'Key Metric':<25} {'Time':>8}")
    print("-" * 70)
    for r in results:
        name = r.get("scenario", "?")
        if "error" in r:
            status = "FAILED"
            metric = r["error"][:25]
        else:
            status = "OK"
            if "confidence" in r:
                metric = f"confidence={r['confidence']:.3f}"
            elif "vcs_met" in r:
                metric = f"vcs={r['vcs_met']}, actions={r.get('actions_taken', 0)}"
            elif "tension" in r:
                metric = f"dominant={r['dominant']}, tension={r['tension']:.2f}"
            elif "throughput_ops" in r:
                metric = f"throughput={r['throughput_ops']:.0f}/s"
            elif "strategies_learned" in r:
                metric = f"learned={r['strategies_learned']} strategies"
            elif "succeeded" in r:
                metric = f"{r['succeeded']}/{r.get('total_actions', 0)} actions"
            else:
                metric = "-"
        elapsed = r.get("elapsed_s", 0)
        print(f"{name:<25} {status:<10} {metric:<25} {elapsed:>7.1f}s")

    print(f"\nTotal training time: {sum(r.get('elapsed_s', 0) for r in results):.1f}s")
    print("\nArmy training complete. Ready for iterative optimization.")

    # Save results
    results_file = "/tmp/clone_army_training_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
