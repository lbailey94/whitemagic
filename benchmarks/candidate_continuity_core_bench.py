#!/usr/bin/env python3
"""Benchmark continuity-core reservation without overwriting pinned archives.

Compares the installed laptop binary against a local source-built candidate on:
  1. The pinned T_CONTINUITY family (8 scenarios, 280-token compact cap)
  2. A resume-shaped overcrowding microbench that used to drop checkpoint
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pinned_task_eval import (  # noqa: E402
    CALL_AUDIT,
    WMMcpSession,
    assert_mcp_ok,
    run_continuity_family,
    sha256_file,
    validate_agent_context,
)


def avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def p50_p95(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"p50_ms": 0.0, "p95_ms": 0.0}
    ordered = sorted(vals)
    p50 = statistics.median(ordered)
    p95_idx = min(len(ordered) - 1, int(math.ceil(0.95 * len(ordered))) - 1)
    return {"p50_ms": round(p50, 2), "p95_ms": round(ordered[p95_idx], 2)}


def binary_meta(path: Path) -> dict:
    version = (
        __import__("subprocess")
        .check_output([str(path), "--version"], text=True)
        .strip()
    )
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "version": version,
    }


def resume_shaped_microbench(wm_bin: Path, budgets: list[int], repeats: int = 5) -> dict:
    """Flood recent/salient history so a non-reserving projector used to null checkpoint."""
    results = []
    with tempfile.TemporaryDirectory(prefix="resume_shaped_") as td:
        store = Path(td) / "store"
        wm = WMMcpSession(wm_bin, store)
        session = "resume-shaped-s1"
        seed: list[tuple[str, dict]] = []
        for i in range(1, 13):
            seed.append(
                (
                    "session_record",
                    {
                        "session_id": session,
                        "role": "assistant",
                        "turn_type": "decision",
                        "track": "estate",
                        "importance": 0.95,
                        "content": (
                            f"D{i}: Keep estate lane decisions durable under budget pressure; "
                            f"detail block {i}: " + ("x" * 48)
                        ),
                    },
                )
            )
        for i in range(1, 21):
            seed.append(
                (
                    "session_record",
                    {
                        "session_id": session,
                        "role": "assistant",
                        "turn_type": "note",
                        "track": "estate",
                        "importance": 0.2,
                        "content": f"recent noise heartbeat {i}: " + ("n" * 64),
                    },
                )
            )
        seed.append(
            (
                "session_checkpoint",
                {
                    "session_id": session,
                    "agent_id": "cursor",
                    "checkpoint_type": "milestone",
                    "track": "estate",
                    "summary": "Production hosted lane now runs v11.2.1; verify cards before deploy.",
                    "next_queue": ["Do not promote until continuity-core bench is green."],
                    "open_flags": ["candidate-binary-only"],
                },
            )
        )
        seeded, _, _ = wm.run_batch(seed)
        for row in seeded:
            assert_mcp_ok(row, "resume_shaped_seed")

        # Foreign lane that must not become session "all" under track-only resume.
        foreign, _, _ = wm.run_batch(
            [
                (
                    "session_record",
                    {
                        "session_id": "foreign-lane",
                        "role": "assistant",
                        "turn_type": "decision",
                        "track": "other",
                        "importance": 0.95,
                        "content": "FOREIGN_DECISION: rotate staging CSS on Tuesday.",
                    },
                )
            ]
        )
        assert_mcp_ok(foreign[0], "resume_shaped_foreign")

        for budget in budgets:
            samples = []
            for mode in ("scoped", "track_only"):
                for _ in range(repeats):
                    args = {
                        "track": "estate",
                        "token_budget": budget,
                        "n": 8,
                    }
                    if mode == "scoped":
                        args["session_id"] = session
                    t0 = time.perf_counter()
                    ordered, _, _ = wm.run_batch([("session_continuity", args)])
                    ms = (time.perf_counter() - t0) * 1000.0
                    resp = ordered[0]
                    assert_mcp_ok(resp, f"resume_shaped_continuity_{mode}_{budget}")
                    context, text = validate_agent_context(resp)
                    top_cp = resp.get("checkpoint")
                    compact_cp = context.get("checkpoint")
                    semantics = "\n".join(
                        part
                        for part in (
                            [text]
                            + [str(v) for v in (context.get("queue") or [])]
                            + [
                                turn.get("text", "")
                                for turn in (context.get("turns") or [])
                                if isinstance(turn, dict)
                            ]
                        )
                    )
                    samples.append(
                        {
                            "mode": mode,
                            "latency_ms": ms,
                            "session_id": resp.get("session_id"),
                            "budget_completeness": resp["agent_context"].get(
                                "budget_completeness"
                            ),
                            "continuity_core_omitted": resp["agent_context"].get(
                                "continuity_core_omitted"
                            ),
                            "top_level_checkpoint_present": isinstance(top_cp, dict),
                            "compact_checkpoint_present": isinstance(compact_cp, dict),
                            "compact_checkpoint_null": compact_cp is None and bool(text),
                            "queue": context.get("queue") or [],
                            "foreign_imported": "FOREIGN_DECISION" in semantics,
                            "context_bytes": len(text.encode("utf-8")),
                            "tokens_used": resp["agent_context"].get("estimated_tokens"),
                        }
                    )
            checkpoint_kept = all(s["compact_checkpoint_present"] for s in samples)
            null_partial = any(s["compact_checkpoint_null"] for s in samples)
            results.append(
                {
                    "token_budget": budget,
                    "byte_cap": budget * 4,
                    "repeats": repeats,
                    "checkpoint_kept_every_repeat": checkpoint_kept,
                    "null_checkpoint_partial_seen": null_partial,
                    "queue_kept_every_repeat": all(
                        "Do not promote until continuity-core bench is green." in s["queue"]
                        for s in samples
                    ),
                    "session_never_all": all(s["session_id"] != "all" for s in samples),
                    "foreign_never_imported": all(not s["foreign_imported"] for s in samples),
                    "latency": p50_p95([s["latency_ms"] for s in samples]),
                    "mean_tokens_used": avg([float(s["tokens_used"] or 0) for s in samples]),
                    "samples": samples,
                }
            )
    return {"name": "resume_shaped_overcrowd", "budgets": results}


def continuity_summary(family: dict) -> dict:
    scenarios = family["scenarios"]
    wm_rows = [s["whitemagic_v10_4"] for s in scenarios]
    return {
        "scenario_count": len(scenarios),
        "mean_decision_recall": avg([r["decision_recall"] for r in wm_rows]),
        "mean_open_arc_precision": avg([r["open_arc_precision"] for r in wm_rows]),
        "track_routing_rate": avg(
            [1.0 if r["new_session_track_routing_ok"] else 0.0 for r in wm_rows]
        ),
        "crystal_rate": avg(
            [1.0 if r["cross_session_crystal_surfaced"] else 0.0 for r in wm_rows]
        ),
        "budget_enforced_rate": avg([1.0 if r["budget_enforced"] else 0.0 for r in wm_rows]),
        "mean_tokens_used": avg([float(r["tokens_used"]) for r in wm_rows]),
        "latency": p50_p95([r["latency_ms"] for r in wm_rows]),
        "checkpoint_in_compact_rate": avg(
            [
                1.0
                if '"checkpoint":{' in r["consumed_context"]
                or '"checkpoint": {' in r["consumed_context"]
                else 0.0
                for r in wm_rows
            ]
        ),
    }


def run_for_binary(label: str, path: Path) -> dict:
    CALL_AUDIT.clear()
    t0 = time.perf_counter()
    family = run_continuity_family(path)
    continuity_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    micro = resume_shaped_microbench(path, budgets=[120, 280, 400], repeats=5)
    micro_s = time.perf_counter() - t1
    return {
        "label": label,
        "binary": binary_meta(path),
        "continuity_family_wall_s": continuity_s,
        "microbench_wall_s": micro_s,
        "continuity_summary": continuity_summary(family),
        "continuity_family": family,
        "resume_shaped_microbench": micro,
    }


def main() -> int:
    installed = Path.home() / ".local/bin/wm3"
    candidate = HERE.parent / "target/candidate/wm-continuity-core"
    if not installed.is_file():
        raise SystemExit(f"installed binary missing: {installed}")
    if not candidate.is_file():
        raise SystemExit(f"candidate binary missing: {candidate}")

    report = {
        "purpose": "pre-deploy continuity-core reservation check",
        "generated_note": "Does not overwrite pinned-task-eval-results.json",
        "installed": run_for_binary("installed-11.2.1", installed),
        "candidate": run_for_binary("candidate-continuity-core", candidate),
    }

    # Compact delta view for humans.
    inst = report["installed"]["continuity_summary"]
    cand = report["candidate"]["continuity_summary"]
    report["delta"] = {
        "continuity_mean_decision_recall": cand["mean_decision_recall"]
        - inst["mean_decision_recall"],
        "continuity_mean_open_arc_precision": cand["mean_open_arc_precision"]
        - inst["mean_open_arc_precision"],
        "continuity_checkpoint_in_compact_rate": cand["checkpoint_in_compact_rate"]
        - inst["checkpoint_in_compact_rate"],
        "continuity_p50_ms": cand["latency"]["p50_ms"] - inst["latency"]["p50_ms"],
        "continuity_p95_ms": cand["latency"]["p95_ms"] - inst["latency"]["p95_ms"],
        "resume_shaped": {},
    }
    for budget in (120, 280, 400):
        i = next(
            b
            for b in report["installed"]["resume_shaped_microbench"]["budgets"]
            if b["token_budget"] == budget
        )
        c = next(
            b
            for b in report["candidate"]["resume_shaped_microbench"]["budgets"]
            if b["token_budget"] == budget
        )
        report["delta"]["resume_shaped"][str(budget)] = {
            "installed_checkpoint_kept": i["checkpoint_kept_every_repeat"],
            "candidate_checkpoint_kept": c["checkpoint_kept_every_repeat"],
            "installed_null_partial": i["null_checkpoint_partial_seen"],
            "candidate_null_partial": c["null_checkpoint_partial_seen"],
            "installed_session_never_all": i.get("session_never_all"),
            "candidate_session_never_all": c.get("session_never_all"),
            "installed_foreign_never_imported": i.get("foreign_never_imported"),
            "candidate_foreign_never_imported": c.get("foreign_never_imported"),
            "p50_ms_delta": c["latency"]["p50_ms"] - i["latency"]["p50_ms"],
        }

    out = HERE / "candidate-continuity-core-bench.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"delta": report["delta"], "out": str(out)}, indent=2, sort_keys=True))
    print("\ninstalled continuity:", json.dumps(inst, indent=2, sort_keys=True))
    print("\ncandidate continuity:", json.dumps(cand, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
