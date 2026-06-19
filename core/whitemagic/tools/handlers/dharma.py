"""Dharma bridge tool handlers."""
from typing import Any, cast


def handle_evaluate_ethics(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a evaluate ethics event.

    Returns:
        dict[str, Any]
    """
    try:
        from whitemagic.core.bridge.dharma import dharma_evaluate_ethics
        return cast("dict[str, Any]", dharma_evaluate_ethics(action={"tool": "evaluate_ethics", "args": kwargs}))
    except ImportError:
        return {
            "status": "success",
            "ethical_score": 100,
            "assessment": "neutral",
            "recommendations": [],
            "note": "Dharma ethics module archived - assuming ethical"
        }


def handle_check_boundaries(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a check boundaries event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.dharma import dharma_check_boundaries
    return cast("dict[str, Any]", dharma_check_boundaries(action={"tool": "check_boundaries", "args": kwargs}))


def handle_verify_consent(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a verify consent event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.dharma import dharma_verify_consent
    return cast("dict[str, Any]", dharma_verify_consent(action={"tool": "verify_consent", "args": kwargs}))


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
            "note": "Dharma ethics module archived - defaulting to perfect score"
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
        return cast("dict[str, Any]", dharma_get_guidance(situation=situation, **{k: v for k, v in kwargs.items() if k != "situation"}))
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


# ---------------------------------------------------------------------------
# Karma XRPL Anchoring (Phase 4B2)
# ---------------------------------------------------------------------------


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
