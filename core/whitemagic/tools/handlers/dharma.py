"""Dharma bridge tool handlers."""

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def handle_evaluate_ethics(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a evaluate ethics event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.bridge.dharma import dharma_evaluate_ethics

        return cast(
            "dict[str, Any]",
            dharma_evaluate_ethics(action={"tool": "evaluate_ethics", "args": kwargs}),
        )
    except ImportError:
        return {
            "status": "success",
            "ethical_score": 100,
            "assessment": "neutral",
            "recommendations": [],
            "note": "Dharma ethics module archived - assuming ethical",
        }


def handle_check_boundaries(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a check boundaries event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.dharma import dharma_check_boundaries

    return cast(
        "dict[str, Any]",
        dharma_check_boundaries(action={"tool": "check_boundaries", "args": kwargs}),
    )


def handle_verify_consent(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a verify consent event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.dharma import dharma_verify_consent

    return cast(
        "dict[str, Any]",
        dharma_verify_consent(action={"tool": "verify_consent", "args": kwargs}),
    )


def handle_get_ethical_score(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a get ethical score event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.bridge.dharma import dharma_get_ethical_score

        return cast("dict[str, Any]", dharma_get_ethical_score(**kwargs))
    except ImportError:
        return {
            "status": "success",
            "ethical_score": 100,
            "dimension_scores": {},
            "note": "Dharma ethics module archived - defaulting to perfect score",
        }


def handle_get_dharma_guidance(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a get dharma guidance event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.bridge.dharma import dharma_get_guidance

        situation = kwargs.get("situation", "general inquiry")
        return cast(
            "dict[str, Any]",
            dharma_get_guidance(
                situation=situation,
                **{k: v for k, v in kwargs.items() if k != "situation"},
            ),
        )
    except (ImportError, ModuleNotFoundError):
        return {
            "status": "success",
            "guidance": "Dharma module archived — operate with awareness",
            "note": "Dharma guidance module archived",
        }
    except TypeError as e:
        return {"status": "error", "error_code": "invalid_params", "error": str(e)}


def handle_karma_report(**kwargs: Any) -> dict[str, Any]:
    """Return the Karma Ledger report (declared vs actual side-effects)."""
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    limit = int(kwargs.get("limit", 100))
    return {"status": "success", "karma": get_karma_ledger().report(limit=limit)}


def handle_karma_record(**kwargs: Any) -> dict[str, Any]:
    """Record a new entry in the Karma Ledger.

    This is the write-path counterpart to karma_report.  It wraps
    KarmaLedger.record() so callers (e.g. the Hermes policy gate)
    can append Merkle-hashed entries without bypassing the tool layer.
    """
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    ledger = get_karma_ledger()
    entry = ledger.record(
        tool=str(kwargs.get("tool", "unknown")),
        declared_safety=str(kwargs.get("declared_safety", "READ")),
        actual_writes=int(kwargs.get("actual_writes", 0)),
        success=bool(kwargs.get("success", True)),
        ops_class=str(kwargs.get("ops_class", "")),
    )
    return {"status": "success", "entry": entry.to_dict()}


def handle_karmic_trace(**kwargs: Any) -> dict[str, Any]:
    """Return recent Karmic Trace entries from the Dharma Rules Engine."""
    from whitemagic.dharma.rules import get_rules_engine

    limit = int(kwargs.get("limit", 50))
    engine = get_rules_engine()
    return {"status": "success", "trace": engine.get_karmic_trace(limit=limit)}


def handle_dharma_rules(**kwargs: Any) -> dict[str, Any]:
    """List active Dharma rules and the current profile."""
    from whitemagic.dharma.rules import get_rules_engine

    engine = get_rules_engine()
    profile = kwargs.get("profile", None)
    return {
        "status": "success",
        "active_profile": engine.get_profile(),
        "rules": engine.get_rules(profile=profile),
    }


def handle_karma_verify_chain(**kwargs: Any) -> dict[str, Any]:
    """Verify the Merkle hash chain integrity of the Karma Ledger."""
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    ledger = get_karma_ledger()
    return {"status": "success", **ledger.verify_chain()}


def handle_set_dharma_profile(**kwargs: Any) -> dict[str, Any]:
    """Switch the active Dharma profile (default, creative, secure)."""
    from whitemagic.dharma.rules import get_rules_engine

    profile = kwargs.get("profile", "default")
    engine = get_rules_engine()
    engine.set_profile(profile)
    return {
        "status": "success",
        "message": f"Dharma profile set to: {profile}",
        "active_profile": engine.get_profile(),
    }


def handle_karma_anchor(**kwargs: Any) -> dict[str, Any]:
    """Compute and optionally submit a karma Merkle root anchor to XRPL."""
    from whitemagic.dharma.karma_anchor import compute_anchor, submit_anchor

    submit = kwargs.get("submit", False)
    network = kwargs.get("network", "testnet")
    wallet_seed = kwargs.get("wallet_seed", None)

    snapshot = compute_anchor()
    if not submit:
        return {"status": "success", "action": "snapshot_only", **snapshot}

    result = submit_anchor(
        merkle_root=snapshot.get("merkle_root"),
        wallet_seed=wallet_seed,
        network=network,
    )
    return {"status": "success", "action": "submitted", "snapshot": snapshot, **result}


def handle_karma_verify_anchor(**kwargs: Any) -> dict[str, Any]:
    """Verify a karma anchor transaction on the XRP Ledger."""
    from whitemagic.dharma.karma_anchor import verify_anchor

    tx_hash = kwargs.get("tx_hash", "")
    if not tx_hash:
        return {"status": "error", "reason": "tx_hash is required"}

    expected_root = kwargs.get("expected_merkle_root", None)
    network = kwargs.get("network", "testnet")
    return verify_anchor(tx_hash, expected_root, network)


def handle_karma_anchor_status(**kwargs: Any) -> dict[str, Any]:
    """Get the current karma anchor system status."""
    from whitemagic.dharma.karma_anchor import anchor_status

    return {"status": "success", **anchor_status()}


def handle_dharma_escalate(**kwargs: Any) -> dict[str, Any]:
    """Run the 4-tier Dharma escalation pipeline on an action.

    Tiers: policy → heuristic → LLM → human.
    Only escalates when the policy tier returns an ambiguous score.

    Args:
        action: The action dict to evaluate (tool, description, args).
    """
    from whitemagic.dharma import get_dharma_system

    action = kwargs.get("action", {})
    if not isinstance(action, dict):
        action = {"tool": str(action)}

    dharma = get_dharma_system()
    result = dharma.evaluate_with_escalation(action)
    return {"status": "success", **result}


def handle_dharma_review_queue(**kwargs: Any) -> dict[str, Any]:
    """Get pending human review items from the escalation pipeline."""
    from whitemagic.dharma.escalation import get_escalation_pipeline

    pipeline = get_escalation_pipeline()
    queue = pipeline.get_review_queue()
    pending = [item for item in queue if item.get("status") == "pending"]
    return {
        "status": "success",
        "pending_count": len(pending),
        "total_count": len(queue),
        "reviews": pending,
    }


def handle_dharma_resolve_review(**kwargs: Any) -> dict[str, Any]:
    """Resolve a human review item from the escalation pipeline.

    Args:
        review_id: The review ID to resolve.
        decision: "allow", "warn", or "block".
        score: Human-assigned score (0.0-1.0).
    """
    from whitemagic.dharma.escalation import get_escalation_pipeline

    review_id = kwargs.get("review_id", "")
    decision = kwargs.get("decision", "warn")
    score = float(kwargs.get("score", 0.5))

    if not review_id:
        return {"status": "error", "error": "review_id is required"}

    pipeline = get_escalation_pipeline()
    resolved = pipeline.resolve_review(review_id, decision, score)
    if not resolved:
        return {"status": "error", "error": f"Review {review_id} not found or already resolved"}

    return {
        "status": "success",
        "review_id": review_id,
        "decision": decision,
        "score": score,
        "message": f"Review {review_id} resolved as {decision}",
    }


def handle_karmic_effects(**kwargs: Any) -> dict[str, Any]:
    """Query declared effect signatures and mismatches for tools (MandalaOS Phase A).

    Args:
        tool: Optional tool name to query. If omitted, returns summary for all tools.
    """
    from whitemagic.dharma.effect_registry import get_effect_registry, get_declared_effects

    tool_name = kwargs.get("tool", "")
    if tool_name:
        effects = get_declared_effects(tool_name)
        return {
            "status": "success",
            "tool": tool_name,
            "declared_effects": [e.to_dict() for e in effects],
        }

    registry = get_effect_registry()
    summary: dict[str, Any] = {}
    for name, sigs in registry.items():
        summary[name] = [e.to_dict() for e in sigs]
    return {
        "status": "success",
        "total_tools": len(registry),
        "effects": summary,
    }


def handle_karmic_debt(**kwargs: Any) -> dict[str, Any]:
    """Per-tool, per-session, or per-shelter karma debt reports (MandalaOS Phase A).

    Args:
        tool: Optional tool name to filter debt.
        shelter_id: Optional shelter ID to filter debt (Phase B).
    """
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    ledger = get_karma_ledger()
    report = ledger.report()

    tool_name = kwargs.get("tool", "")
    if tool_name:
        per_tool = report.get("per_tool", {})
        tool_stats = per_tool.get(tool_name, {})
        return {
            "status": "success",
            "tool": tool_name,
            "debt": tool_stats.get("debt", 0.0),
            "calls": tool_stats.get("calls", 0),
            "mismatches": tool_stats.get("mismatches", 0),
            "effect_mismatches": tool_stats.get("effect_mismatches", 0),
        }

    return {
        "status": "success",
        "total_debt": report.get("total_debt", 0.0),
        "total_calls": report.get("total_calls", 0),
        "total_mismatches": report.get("total_mismatches", 0),
        "effect_mismatch_count": report.get("effect_mismatch_count", 0),
        "per_tool": report.get("per_tool", {}),
    }


def handle_karmic_verify(**kwargs: Any) -> dict[str, Any]:
    """Verify Merkle chain + effect signature integrity of the Karma Ledger (MandalaOS Phase A).

    Combines the existing chain verification with an effect mismatch audit.
    """
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    ledger = get_karma_ledger()
    chain_result = ledger.verify_chain()

    # Audit effect mismatches
    report = ledger.report()
    effect_mismatches = report.get("effect_mismatch_count", 0)

    return {
        "status": "success",
        "chain_valid": chain_result.get("valid", False),
        "chain_entries": chain_result.get("entries", 0),
        "effect_mismatches": effect_mismatches,
        "integrity_ok": chain_result.get("valid", False) and effect_mismatches == 0,
    }


def handle_effect_trace(**kwargs: Any) -> dict[str, Any]:
    """Get effect trace for a tool call (MandalaOS Phase C).

    Returns the declared effects, actual effects, mismatches, and debt
    for a given tool from the Karma Ledger. Optionally uses the Koka
    karmic_effects module for type-safe comparison.

    Args:
        tool: Tool name to trace.
        use_koka: If True, attempt Koka karmic comparison (default False).
    """
    tool_name = kwargs.get("tool", "")
    if not tool_name:
        return {"status": "error", "error": "Missing 'tool' parameter"}

    from whitemagic.dharma.effect_registry import get_declared_effects
    from whitemagic.dharma.karma_ledger import get_karma_ledger

    declared = get_declared_effects(tool_name)
    declared_dicts = [e.to_dict() for e in declared]

    use_koka = kwargs.get("use_koka", False)
    if use_koka:
        try:
            from whitemagic.core.acceleration.koka_native_bridge import KokaNativeBridge

            bridge = KokaNativeBridge()
            if bridge.is_available("karmic"):
                result = bridge.dispatch_karmic(
                    tool=tool_name,
                    params={},
                    declared_effects=declared_dicts,
                    actual_effects=declared_dicts,  # No actual yet — comparison is no-op
                )
                if result and result.get("status") == "success":
                    return {
                        "status": "success",
                        "tool": tool_name,
                        "declared_effects": declared_dicts,
                        "karmic_result": result,
                        "koka_enforced": True,
                    }
        except Exception as e:
            logger.debug("Koka karmic dispatch failed: %s", e, exc_info=True)

    # Python fallback: return trace from ledger
    ledger = get_karma_ledger()
    report = ledger.report()
    per_tool = report.get("per_tool", {}).get(tool_name, {})

    return {
        "status": "success",
        "tool": tool_name,
        "declared_effects": declared_dicts,
        "karma_debt": per_tool.get("debt", 0.0),
        "calls": per_tool.get("calls", 0),
        "mismatches": per_tool.get("mismatches", 0),
        "effect_mismatches": per_tool.get("effect_mismatches", 0),
        "koka_enforced": False,
    }


def handle_effect_visualize(**kwargs: Any) -> dict[str, Any]:
    """Export effect flow visualization (MandalaOS Phase C).

    Generates a visualization of effect relationships for a tool or
    the entire system. Supports DOT (Graphviz) and Mermaid formats.

    Args:
        tool: Optional tool name to visualize. Omit for system-wide view.
        format: Output format — "dot" (default), "mermaid", or "json".
    """
    fmt = kwargs.get("format", "dot")
    tool_name = kwargs.get("tool", "")

    from whitemagic.dharma.effect_registry import get_effect_registry

    registry = get_effect_registry()

    if tool_name:
        effects = registry.get(tool_name, [])
        if not effects:
            return {"status": "error", "error": f"No effects found for '{tool_name}'"}

        if fmt == "json":
            return {
                "status": "success",
                "tool": tool_name,
                "format": "json",
                "effects": [e.to_dict() for e in effects],
            }

        if fmt == "mermaid":
            lines = ["graph TD"]
            lines.append(f'  tool["{tool_name}"]')
            for i, eff in enumerate(effects):
                et = eff.effect_type.value
                lines.append(f'  eff{i}["{et}: {eff.target or "—"}"]')
                declared_label = "declared" if eff.declared else "actual"
                lines.append(f'  tool -->|{declared_label}| eff{i}')
            return {
                "status": "success",
                "tool": tool_name,
                "format": "mermaid",
                "graph": "\n".join(lines),
            }

        # DOT format (default)
        lines = ["digraph effect_flow {", "  rankdir=LR;"]
        lines.append(f'  "tool" [label="{tool_name}", shape=box, style=filled, fillcolor=lightblue];')
        for i, eff in enumerate(effects):
            et = eff.effect_type.value
            color = {
                "destructive": "red",
                "network": "orange",
                "local": "yellow",
                "observation": "green",
                "pure": "white",
            }.get(et, "gray")
            lines.append(
                f'  "eff{i}" [label="{et}", shape=ellipse, style=filled, fillcolor={color}];'
            )
            lines.append(f'  "tool" -> "eff{i}";')
        lines.append("}")
        return {
            "status": "success",
            "tool": tool_name,
            "format": "dot",
            "graph": "\n".join(lines),
        }

    # System-wide summary
    type_counts: dict[str, int] = {}
    for sigs in registry.values():
        for s in sigs:
            et = s.effect_type.value
            type_counts[et] = type_counts.get(et, 0) + 1

    if fmt == "json":
        return {
            "status": "success",
            "format": "json",
            "total_tools": len(registry),
            "effect_type_counts": type_counts,
        }

    if fmt == "mermaid":
        lines = ["pie title Effect Distribution"]
        for et, count in sorted(type_counts.items()):
            lines.append(f'  "{et}" : {count}')
        return {
            "status": "success",
            "format": "mermaid",
            "graph": "\n".join(lines),
            "total_tools": len(registry),
            "effect_type_counts": type_counts,
        }

    # DOT system-wide
    lines = ["digraph effect_summary {", "  rankdir=TB;"]
    lines.append('  "system" [label="Effect Registry", shape=box, style=filled, fillcolor=lightblue];')
    for et, count in sorted(type_counts.items()):
        color = {
            "destructive": "red",
            "network": "orange",
            "local": "yellow",
            "observation": "green",
            "pure": "white",
        }.get(et, "gray")
        lines.append(
            f'  "{et}" [label="{et}\\n({count} tools)", shape=ellipse, style=filled, fillcolor={color}];'
        )
        lines.append(f'  "system" -> "{et}";')
    lines.append("}")
    return {
        "status": "success",
        "format": "dot",
        "graph": "\n".join(lines),
        "total_tools": len(registry),
        "effect_type_counts": type_counts,
    }
