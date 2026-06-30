# ruff: noqa: BLE001
import asyncio
import logging
import os
import time
import traceback
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any, TypeVar, cast
from uuid import uuid4

from whitemagic.config.paths import WM_ROOT, ensure_paths
from whitemagic.tools.errors import ErrorCode, ToolExecutionError
from whitemagic.tools.timeouts import (
    FAST_INTERACTIVE_WRITE_TOOLS,
    LIGHTWEIGHT_STATUS_TOOLS,
    get_timeout_for_tool,
    should_skip_nervous_system_check,
)
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads
from whitemagic.utils.time import now_iso, override_now

logger = logging.getLogger(__name__)
T = TypeVar("T")

# v21: Centralized executor for tool dispatch to prevent thread-bombing
_TOOL_DISPATCH_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool-dispatch")


# ---------------------------------------------------------------------------
# Tool ID Registry for Nervous System (avoids hash collisions)
# ---------------------------------------------------------------------------
_TOOL_ID_REGISTRY: dict[str, int] = {}
_MAX_TOOL_ID = 28  # Maximum tool ID for dispatch bridge (0-27)


def _get_or_assign_tool_id(tool_name: str) -> int:
    """Get or assign a unique tool ID from the registry, avoiding hash collisions."""
    if tool_name not in _TOOL_ID_REGISTRY:
        # Assign next available ID
        tool_id = len(_TOOL_ID_REGISTRY) % _MAX_TOOL_ID
        _TOOL_ID_REGISTRY[tool_name] = tool_id
    return _TOOL_ID_REGISTRY[tool_name]


def _nervous_system_check(tool_name: str) -> tuple[bool, str]:
    """Pre-dispatch check via Nervous System (StateBoard + DispatchBridge).

    Checks circuit breakers and rate limits via the Zig/Python dispatch bridge.
    Returns (allowed, reason).

    Diagnostic tools are always allowed to ensure troubleshooting capability.
    """
    if should_skip_nervous_system_check(tool_name):
        return True, ""

    try:
        from whitemagic.core.acceleration.dispatch_bridge import (  # noqa: E402
            DispatchResult,
            get_dispatch,
        )
        bridge = get_dispatch()
        # Use dedicated registry to avoid hash collisions
        tool_id = _get_or_assign_tool_id(tool_name)
        result = bridge.check(tool_id)
        if result == DispatchResult.CIRCUIT_OPEN:
            return False, f"Circuit breaker OPEN for {tool_name}"
        if result == DispatchResult.RATE_LIMITED:
            return False, f"Rate limited: {tool_name}"
        if result == DispatchResult.IMMATURE:
            return False, f"Tool maturity gate blocked: {tool_name}"
    except Exception as e:
        logger.debug("Nervous system check failed for %s: %s", tool_name, e)  # Advisory — never block on failure
    return True, ""


def _nervous_system_post(tool_name: str, duration: float, success: bool) -> None:
    """Post-dispatch: sync Harmony Vector to StateBoard and publish to EventRing."""
    # Sync Harmony Vector → StateBoard mmap
    try:
        from whitemagic.core.acceleration.state_board_bridge import get_state_board
        from whitemagic.harmony.vector import get_harmony_vector
        hv = get_harmony_vector()
        snap = hv.snapshot()
        board = get_state_board()
        board.write_harmony(
            balance=snap.balance,
            throughput=snap.throughput,
            latency=snap.latency,
            error_rate=snap.error_rate,
            dharma=snap.dharma,
            karma_debt=snap.karma_debt,
            energy=snap.energy,
        )
    except Exception as e:
        logger.debug("Failed to publish tool completion to EventRing: %s", e, exc_info=True)
    # Publish tool completion to EventRing
    try:
        from whitemagic.core.acceleration.event_ring_bridge import get_event_ring
        event_type = "tool_completed" if success else "error_occurred"
        get_event_ring().publish(
            event_type=event_type,
            source=tool_name,
            confidence=1.0,
            data=f"{duration:.3f}s".encode()[:80],
        )
    except Exception as e:
        logger.debug("Failed to publish tool start to EventRing: %s", e, exc_info=True)


def _emit_gan_ying(event_type_name: str, data: dict[str, Any], source: str = "mcp") -> None:
    """Emit Gan Ying events without breaking tool flows."""
    try:
        # Use the public wrapper (handles unknown string event types safely).
        from whitemagic.core.resonance.gan_ying import emit_event

        emit_event(event_type_name, data, source=source, confidence=1.0)
    except Exception as exc:
        logger.info("Gan Ying event (%s) failed: %s", event_type_name, exc, exc_info=True)

def _load_rust() -> tuple[object | None, str | None]:
    """Load the Rust bridge if available."""
    try:
        try:
            import whitemagic_rust as rs_module  # type: ignore
        except ImportError:
            import whitemagic_rs as rs_module  # type: ignore
        return rs_module, None
    except Exception as exc:
        # pragma: no cover - best-effort availability
        return None, str(exc)


def _resolve_base_path(kwargs: dict[str, Any]) -> Path:
    """Resolve base path with security validation."""
    base_path = kwargs.get("base_path") or os.environ.get("WM_BASE_PATH")
    if not base_path:
        return cast("Path", WM_ROOT)

    resolved = Path(base_path).resolve()

    # Strong default: state lives under WM_STATE_ROOT. Allow external state roots
    # only via explicit opt-in.
    allow_external = os.getenv("WHITEMAGIC_ALLOW_EXTERNAL_STATE_ROOT", "false").lower() == "true"
    if not allow_external:
        try:
            resolved.relative_to(WM_ROOT)
        except ValueError:
            return cast("Path", WM_ROOT)

    # Security: validate base_path is allowed (read/write allowlist).
    from whitemagic.security.tool_gating import get_tool_gate
    gate = get_tool_gate()
    allowed, _reason = gate.path_validator.is_path_allowed(str(resolved))
    if not allowed:
        return cast("Path", WM_ROOT)

    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _session_dir(base_path: Path) -> Path:
    session_dir = base_path / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _session_path(base_path: Path, session_id: str) -> Path:
    return _session_dir(base_path) / f"{session_id}.json"


def _load_session(base_path: Path, session_id: str) -> dict[str, Any]:
    path = _session_path(base_path, session_id)
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    return cast("dict[str, Any]", _json_loads(path.read_text(encoding="utf-8")))


def _save_session(base_path: Path, session: dict[str, Any]) -> None:
    path = _session_path(base_path, session["id"])
    path.write_text(_json_dumps(session, indent=2), encoding="utf-8")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine safely, handling event loop conflicts.

    Uses a shared executor when an event loop is already running to avoid
    creating new event loops per call (which leaks resources).
    """
    try:
        asyncio.get_running_loop()
        # Event loop is already running - use shared executor
        return _TOOL_DISPATCH_EXECUTOR.submit(asyncio.run, coro).result()
    except RuntimeError:
        # No running loop - safe to use asyncio.run directly
        return asyncio.run(coro)


def _local_models_archived() -> dict[str, Any]:
    return {
        "status": "error",
        "message": "Local model execution is archived/disabled in this build. "
        "Use an external model via MCP/REST to call Whitemagic tools.",
        "archived": True,
    }


def record_yin_yang_activity(activity: str) -> dict[str, Any]:
    """Record Yin-Yang activity from MCP."""
    try:
        from whitemagic.harmony.yin_yang_tracker import get_tracker

        tracker = get_tracker()
        metrics = tracker.record_activity(activity)

        return {
            "success": True,
            "balance_score": metrics.balance_score,
            "burnout_risk": metrics.burnout_risk,
            "recommendation": metrics.recommendation,
            "yang_ratio": metrics.yang_ratio,
            "yin_ratio": metrics.yin_ratio,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_yin_yang_balance() -> dict[str, Any]:
    """Get current Yin-Yang balance report."""
    try:
        from whitemagic.harmony.yin_yang_tracker import get_tracker

        tracker = get_tracker()
        return cast("dict[str, Any]", tracker.get_report())
    except (ImportError, ModuleNotFoundError) as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _dispatch_tool(tool_name: str, **kwargs: Any) -> Any:
    """Dispatch tool calls via the dispatch table (v11 refactor).

    The dispatch table lives in whitemagic.tools.dispatch_table and maps
    tool names to handler functions grouped by category.  Governor
    interception, gana prefix routing, and bridge fallback are handled
    inside ``dispatch()``.
    """
    from whitemagic.tools.dispatch_table import dispatch as _table_dispatch

    return _table_dispatch(tool_name, **kwargs)


def _dispatch_lightweight_tool(tool_name: str, **kwargs: Any) -> Any:
    if tool_name == "vector.status":
        from whitemagic.core.memory.vector_search import get_vector_status
        return {"status": "success", **get_vector_status()}
    if tool_name == "prompt.list":
        from whitemagic.prompts import get_prompt_engine
        tag = kwargs.get("tag")
        engine = get_prompt_engine()
        return {
            "status": "success",
            "templates": engine.list_templates(tag=tag),
            **engine.status(),
        }
    if tool_name == "forge.status":
        from whitemagic.tools.gana_forge import _DEFAULT_EXT_DIR, discover_extensions
        ext_dir = _DEFAULT_EXT_DIR
        manifests = discover_extensions(ext_dir)
        loaded_names: list[str] = []
        try:
            from whitemagic.tools.prat_mappings import TOOL_TO_GANA
            loaded_names = [
                name for name in TOOL_TO_GANA
                if name.startswith("ext.") or name.startswith("custom.")
            ]
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Failed to load TOOL_TO_GANA: %s", e, exc_info=True)
        return {
            "status": "success",
            "extensions_dir": str(ext_dir),
            "extensions_dir_exists": ext_dir.exists(),
            "manifests_found": len(manifests),
            "manifest_files": [m.get("_source_path", "?") for m in manifests],
            "loaded_extension_tools": loaded_names,
            "usage": (
                "Place YAML manifests in ~/.whitemagic/extensions/ with format:\n"
                "tool:\n"
                "  name: custom.my_tool\n"
                "  description: What it does\n"
                "  gana: gana_ghost\n"
                "  safety: read\n"
                "  handler: 'my_module:my_function'"
            ),
        }
    raise KeyError(tool_name)


def _dispatch_tool_with_timeout(tool_name: str, timeout_s: float, **kwargs: Any) -> Any:
    """Run tool dispatch with a hard client-facing timeout."""
    # v21: Use the centralized executor instead of spawning raw threads
    future = _TOOL_DISPATCH_EXECUTOR.submit(_dispatch_tool, tool_name, **kwargs)

    try:
        return future.result(timeout=timeout_s)
    except TimeoutError as exc:
        raise TimeoutError(f"Tool dispatch timed out after {timeout_s:.1f}s: {tool_name}") from exc
    except Exception as exc:
        raise exc


# Dead code removed: the 1400-line if/elif dispatcher was replaced by
# whitemagic.tools.dispatch_table (Phase 2 refactor, v11 hardening).
# Original handlers live in whitemagic/tools/handlers/*.py


_DEAD_CODE_REMOVED = True  # Marker for grep-ability



_TOOL_ALIASES: dict[str, str] = {
    # Legacy names -> canonical v11 names
    "manifest_read": "manifest",
    "manifest_summary": "manifest",
    "state_paths": "state.paths",
    "state_summary": "state.summary",
    "repo_summary": "repo.summary",
    "ship_check": "ship.check",
    # Underscore aliases for dot-notation tools
    "mesh_connect": "mesh.connect",
    "broker_publish": "broker.publish",
    "broker_history": "broker.history",
    "broker_status": "broker.status",
    "task_distribute": "task.distribute",
    "task_status": "task.status",
    "task_list": "task.list",
    "task_complete": "task.complete",
    "vote_create": "vote.create",
    "vote_cast": "vote.cast",
    "vote_analyze": "vote.analyze",
    "vote_list": "vote.list",
    "vote_record_outcome": "vote.record_outcome",
    "ollama_models": "ollama.models",
    "ollama_generate": "ollama.generate",
    "ollama_chat": "ollama.chat",
    "agent_register": "agent.register",
    "agent_heartbeat": "agent.heartbeat",
    "agent_list": "agent.list",
    "agent_capabilities": "agent.capabilities",
    "agent_deregister": "agent.deregister",
    "pipeline_create": "pipeline.create",
    "pipeline_status": "pipeline.status",
    "pipeline_list": "pipeline.list",
    "homeostasis_status": "homeostasis.status",
    "homeostasis_check": "homeostasis.check",
    "maturity_assess": "maturity.assess",
    "tool_graph": "tool.graph",
    "tool_graph_full": "tool.graph_full",
    "dharma_reload": "dharma.reload",
    "salience_spotlight": "salience.spotlight",
    "reasoning_bicameral": "reasoning.bicameral",
    "memory_retention_sweep": "memory.retention_sweep",
    "read_memory": "memory_read",
    "update_memory": "memory_update",
    "delete_memory": "memory_delete",
    "starter_packs_list": "starter_packs.list",
    "starter_packs_get": "starter_packs.get",
    "starter_packs_suggest": "starter_packs.suggest",
    "capability_matrix": "capability.matrix",
    "capability_status": "capability.status",
    "capability_suggest": "capability.suggest",
    # Missing aliases for tools with handlers
    "galaxy_status": "galaxy.status",
    "galaxy_list": "galaxy.list",
    "galaxy_switch": "galaxy.switch",
    "galaxy_ingest": "galaxy.ingest",
    "galaxy_delete": "galaxy.delete",
    "prompt_list": "prompt.list",
    "prompt_render": "prompt.render",
    "prompt_reload": "prompt.reload",
    "otel_status": "otel.status",
    "otel_spans": "otel.spans",
    "otel_metrics": "otel.metrics",
    "working_memory_status": "working_memory.status",
    "working_memory_attend": "working_memory.attend",
    "working_memory_context": "working_memory.context",
    "cognitive_mode": "cognitive.mode",
    "cognitive_set": "cognitive.set",
    "cognitive_hints": "cognitive.hints",
    "cognitive_stats": "cognitive.stats",
    "rate_limiter_stats": "rate_limiter.stats",
    "audit_export": "audit.export",
    "agent_trust": "agent.trust",
}


def _canonical_tool_name(tool_name: str) -> str:
    """Convert tool name to canonical form, with deprecation warnings for aliases."""
    name = tool_name.strip()
    canonical = _TOOL_ALIASES.get(name, name)

    # Log deprecation warning for aliases (but not too frequently)
    if canonical != name and name in _TOOL_ALIASES:
        logger.warning(
            "DEPRECATION: Tool alias '%s' is deprecated. "
            "Use '%s' instead. "
            "This alias will be removed in the next minor release."
        , name, canonical)

    return canonical


def _tool_writes_hint(tool_name: str) -> list[dict[str, Any]]:
    # Best-effort: most writes are within WM_STATE_ROOT.
    return [{"kind": "wm_state_root", "path": str(WM_ROOT)}]


def call_tool(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """Canonical tool entrypoint (AI-first contract).

    Responsibilities:
    - Ensure WM_STATE_ROOT directories exist
    - Validate params (best-effort) against TOOL_REGISTRY schema when available
    - Apply ToolGate policy checks
    - Provide idempotency for write tools via `idempotency_key`
    - Normalize all outputs into the stable envelope format
    """
    from whitemagic.tools.envelope import err, normalize_raw
    from whitemagic.tools.registry import ToolSafety, ToolCategory, get_tool
    from whitemagic.tools.schema import validate_params

    ensure_paths()

    # Common fields (present in every tool schema)
    request_id = str(kwargs.pop("request_id", "") or uuid4())
    idempotency_key = kwargs.pop("idempotency_key", None)
    dry_run = bool(kwargs.pop("dry_run", False))
    now_override = kwargs.pop("now", None)

    canonical = _canonical_tool_name(tool_name)
    ts = now_override or now_iso()
    call_started_at = time.time()

    # Machine-time prediction: predict duration before executing
    _effort_prediction = None
    try:
        from whitemagic.core.consciousness.machine_time import get_machine_time_estimator
        _effort_prediction = get_machine_time_estimator().predict(canonical)
    except Exception as e:
        logger.debug("Machine-time prediction failed for %s: %s", canonical, e)

    if canonical not in FAST_INTERACTIVE_WRITE_TOOLS:
        # Touch dream cycle idle timer on every tool call
        try:
            from whitemagic.core.dreaming import get_dream_cycle
            get_dream_cycle().touch()
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Dream cycle touch failed: %s", e, exc_info=True)

        # Cross-session learning — record tool usage
        try:
            from whitemagic.core.learning import get_session_learner
            get_session_learner().record_tool_use(canonical)
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Session learner record_tool_use failed: %s", e, exc_info=True)

    _cognitive_mode: str | None = None

    def _record_telemetry(out: dict[str, Any]) -> None:
        duration = time.time() - call_started_at
        status_value = str(out.get("status", "")).lower()
        telemetry_status = "success" if status_value in {"success", "ok"} else "error"
        telemetry_error = out.get("error_code") if telemetry_status == "error" else None
        # Token economy: record this tool call
        try:
            from whitemagic.core.consciousness.token_economy import get_token_tracker
            _economy = get_token_tracker()
            _economy.record_mcp_tool(canonical, duration * 1000)
        except (ImportError, ModuleNotFoundError):
            pass

        # Machine-time: record actual duration and update calibration
        try:
            from whitemagic.core.consciousness.machine_time import get_machine_time_estimator
            _estimator = get_machine_time_estimator()
            _estimator.record_actual(canonical, duration, _effort_prediction)
        except (ImportError, ModuleNotFoundError):
            pass
        try:
            from whitemagic.core.consciousness.prediction_calibration import get_calibration
            get_calibration().record_auto(
                task_id=request_id,
                description=canonical,
                estimated_seconds_machine=_effort_prediction.predicted_seconds if _effort_prediction else duration,
                actual_seconds_machine=duration,
                task_type=_effort_prediction.operation_type if _effort_prediction else "unknown",
            )
        except (ImportError, ModuleNotFoundError):
            pass

        try:
            from whitemagic.core.monitoring.telemetry import get_telemetry
            get_telemetry().record_call(canonical, duration, telemetry_status, telemetry_error)
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Telemetry record_call failed: %s", e, exc_info=True)
            logger.debug("Telemetry record_call failed: %s", e, exc_info=True)
            from whitemagic.core.monitoring.otel_export import record_tool_span
            record_tool_span(canonical, duration, telemetry_status)
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("OTel record_tool_span failed: %s", e, exc_info=True)
        if canonical in LIGHTWEIGHT_STATUS_TOOLS:
            return
        if canonical in FAST_INTERACTIVE_WRITE_TOOLS:
            return
        declared_safety = "READ"
        if tool_def is not None:
            declared_safety = tool_def.safety.value.upper()
        actual_writes = len(out.get("writes", []) or [])
        try:
            from whitemagic.harmony.vector import get_harmony_vector
            hv = get_harmony_vector()
            snap = hv.record_call(
                tool_name=canonical,
                duration_s=duration,
                success=(telemetry_status == "success"),
                declared_safety=declared_safety,
                actual_writes=actual_writes,
            )
            metrics = out.get("metrics")
            if isinstance(metrics, dict):
                metrics["harmony_score"] = snap.harmony_score
                metrics["guna"] = snap.guna_rajasic_pct
                if _cognitive_mode:
                    metrics["cognitive_mode"] = _cognitive_mode
        except Exception as e:
            logger.debug("Failed to add harmony snapshot to metrics: %s", e, exc_info=True)
        try:
            from whitemagic.core.monitoring.neurotransmitter_vector import (
                get_neurotransmitter_vector,
            )
            nt = get_neurotransmitter_vector()
            nt.record_tool_call(
                success=(telemetry_status == "success"),
                result=out,
            )
        except Exception as e:
            logger.debug("Failed to record neurotransmitter snapshot: %s", e, exc_info=True)
        try:
            from whitemagic.dharma.karma_ledger import get_karma_ledger
            get_karma_ledger().record(
                tool=canonical,
                declared_safety=declared_safety,
                actual_writes=actual_writes,
                success=(telemetry_status == "success"),
            )
        except Exception as e:
            logger.debug("Failed to publish tool metrics: %s", e, exc_info=True)
        # Jaynes Voice Audit: verify claim after ledger record
        try:
            if _voice_audit_claim_id:
                from whitemagic.core.governance.voice_audit import (
                    get_voice_audit_scanner,
                )
                get_voice_audit_scanner().verify_claim(tool=canonical)
        except Exception as e:
            logger.debug("VoiceAudit claim verification failed: %s", e, exc_info=True)

    def _finish(out: dict[str, Any]) -> dict[str, Any]:
        _record_telemetry(out)
        return out

    with override_now(now_override):
        tool_def = get_tool(canonical)

        # Best-effort schema validation (only for registry tools).
        if tool_def is not None:
            valid, reason, sanitized = validate_params(tool_def.input_schema, kwargs)
            if not valid:
                return _finish(err(
                    tool=canonical,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    timestamp=ts,
                    error_code=ErrorCode.INVALID_PARAMS,
                    message=reason,
                    details={"tool": canonical},
                ))
            kwargs = sanitized

        # ToolGate policy checks + param sanitation (applies to all non-lightweight tools).
        if canonical not in LIGHTWEIGHT_STATUS_TOOLS:
            from whitemagic.security.tool_gating import check_tool_execution
            allowed, reason, sanitized_params = check_tool_execution(canonical, kwargs)
            if not allowed:
                return _finish(err(
                    tool=canonical,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    timestamp=ts,
                    error_code=ErrorCode.POLICY_BLOCKED,
                    message=reason,
                    details={"tool": canonical},
                    retryable=False,
                ))
            kwargs = sanitized_params

        # Idempotency replay (write/delete tools only)
        if idempotency_key and tool_def is not None and tool_def.safety != ToolSafety.READ:
            from whitemagic.tools.idempotency import get_record
            record = get_record(canonical, str(idempotency_key))
            if record is not None:
                replay = dict(record.response)
                replay["request_id"] = request_id
                replay["timestamp"] = ts
                side_effects_obj = replay.get("side_effects")
                side_effects: dict[str, Any] = dict(side_effects_obj) if isinstance(side_effects_obj, dict) else {}
                side_effects.update(
                    {
                        "idempotency_replay": True,
                        "idempotency_stored_at": record.stored_at,
                    },
                )
                replay["side_effects"] = side_effects
                return _finish(replay)

        # Jaynes Voice Audit: register claim before dispatch
        _voice_audit_claim_id: str | None = None
        try:
            from whitemagic.core.governance.voice_audit import get_voice_audit_scanner
            _voice_audit_claim_id = get_voice_audit_scanner().register_claim(
                module=f"call_tool:{request_id}",
                tool=canonical,
                params={"dry_run": dry_run},
            )
        except Exception as e:
            logger.debug("VoiceAudit claim registration failed: %s", e, exc_info=True)

        # Nervous System pre-dispatch check (circuit breakers, rate limits)
        ns_allowed = True
        ns_reason = ""
        if not should_skip_nervous_system_check(canonical):
            ns_allowed, ns_reason = _nervous_system_check(canonical)
            if not ns_allowed:
                return _finish(err(
                    tool=canonical,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                    timestamp=ts,
                    error_code=ErrorCode.POLICY_BLOCKED,
                    message=ns_reason,
                    details={"tool": canonical, "source": "nervous_system"},
                    retryable=True,
                ))

        # Cognitive mode pre-dispatch enforcement (v23.2: all modes enforce behavior)
        try:
            from whitemagic.core.intelligence.cognitive_modes import get_cognitive_modes
            cm = get_cognitive_modes()
            hints = cm.get_tool_hints()
            _cognitive_mode = hints["mode"]
            _preferred = hints.get("preferred_tools", [])
            if canonical in hints.get("avoided_tools", []):
                # GUARDIAN mode enforces read-only — block avoided tools
                if _cognitive_mode == "guardian":
                    return _finish(err(
                        tool=canonical,
                        request_id=request_id,
                        idempotency_key=idempotency_key,
                        timestamp=ts,
                        error_code=ErrorCode.POLICY_BLOCKED,
                        message=f"Tool {canonical} blocked by GUARDIAN cognitive mode (read-only)",
                        details={"tool": canonical, "cognitive_mode": _cognitive_mode},
                        retryable=False,
                    ))
                # EXECUTOR mode: increased strictness for avoided tools — block writes
                if _cognitive_mode == "executor" and tool_def is not None and tool_def.safety != ToolSafety.READ:
                    return _finish(err(
                        tool=canonical,
                        request_id=request_id,
                        idempotency_key=idempotency_key,
                        timestamp=ts,
                        error_code=ErrorCode.POLICY_BLOCKED,
                        message=f"Tool {canonical} blocked by EXECUTOR mode (avoided tool for write operations)",
                        details={"tool": canonical, "cognitive_mode": _cognitive_mode},
                        retryable=False,
                    ))
                logger.warning(
                    "🧠 Cognitive mode %s avoids tool %s — proceeding but mode mismatch",
                    _cognitive_mode, canonical,
                )
            # Log preferred tool usage for non-balanced modes
            if _cognitive_mode != "balanced" and canonical in _preferred:
                logger.debug(
                    "🧠 Cognitive mode %s prefers tool %s — alignment confirmed",
                    _cognitive_mode, canonical,
                )
        except Exception as e:
            logger.debug("Cognitive mode hint failed: %s", e)

        # SelfModel forecast pre-dispatch (v23.1: feed forecasts into dispatch)
        try:
            from whitemagic.core.intelligence.self_model import get_self_model
            sm = get_self_model()
            alerts = sm.get_alerts()
            if alerts:
                for alert in alerts:
                    # Block write tools when error rate or energy is critical
                    # BUT: never block memory/thought writes — the system must always
                    # be able to record its observations, especially when energy is low.
                    # This includes the wm meta-tool when routing to memory operations.
                    if alert.threshold_eta is not None and alert.threshold_eta <= 2:
                        _is_memory_op = (
                            tool_def is not None
                            and (tool_def.category == ToolCategory.MEMORY
                                 or (canonical == "wm"
                                     and isinstance(kwargs.get("route"), str)
                                     and "gana_neck" in kwargs["route"])))
                        if (alert.metric in ("error_rate", "energy")
                                and tool_def is not None
                                and tool_def.safety != ToolSafety.READ
                                and not _is_memory_op):
                            return _finish(err(
                                tool=canonical,
                                request_id=request_id,
                                idempotency_key=idempotency_key,
                                timestamp=ts,
                                error_code=ErrorCode.POLICY_BLOCKED,
                                message=f"Write tool blocked: {alert.metric} critical ETA {alert.threshold_eta} steps ({alert.alert})",
                                details={"tool": canonical, "self_model_alert": alert.to_dict()},
                                retryable=True,
                            ))
                        # Log warning for non-critical alerts
                        if alert.metric not in ("error_rate", "energy"):
                            logger.warning("SelfModel alert: %s", alert.alert)
                        break
        except Exception as e:
            logger.debug("SelfModel forecast check failed: %s", e)

        # Garden resonance pre-dispatch (v23.3: gardens as active participants)
        try:
            from whitemagic.core.engines.registry import get_garden_for_tool
            garden_name = get_garden_for_tool(canonical)
            if garden_name is not None:
                from whitemagic.gardens import get_garden
                garden = get_garden(garden_name)
                if garden is not None:
                    garden.boost(0.1)
        except Exception:
            pass

        # Dispatch to handler.
        try:
            dispatch_kwargs = dict(kwargs)
            if dry_run:
                dispatch_kwargs["dry_run"] = True
            # Zig/StateBoard already validated circuit breaker, rate limit, maturity
            # — tell the middleware pipeline to skip redundant Python checks
            if ns_allowed:
                dispatch_kwargs["_zig_prevalidated"] = True
            # Working memory context injection (v23.2: bridge working memory to dispatch)
            if canonical not in LIGHTWEIGHT_STATUS_TOOLS:
                try:
                    from whitemagic.core.intelligence.working_memory import (
                        get_working_memory,
                    )
                    _wm = get_working_memory()
                    _wm_context = _wm.get_context(max_tokens=500, dense=True)
                    if _wm_context and "_working_memory_context" not in dispatch_kwargs:
                        dispatch_kwargs["_working_memory_context"] = _wm_context
                except Exception:
                    pass
            if canonical in LIGHTWEIGHT_STATUS_TOOLS:
                raw = _dispatch_lightweight_tool(canonical, **dispatch_kwargs)
            else:
                raw = _dispatch_tool_with_timeout(canonical, get_timeout_for_tool(canonical), **dispatch_kwargs)
        except ImportError as exc:
            out = err(
                tool=canonical,
                request_id=request_id,
                idempotency_key=idempotency_key,
                timestamp=ts,
                error_code=ErrorCode.MISSING_DEPENDENCY,
                message=str(exc),
                details={"tool": canonical},
                retryable=False,
            )
        except ToolExecutionError as exc:
            out = err(
                tool=canonical,
                request_id=request_id,
                idempotency_key=idempotency_key,
                timestamp=ts,
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details or {},
                retryable=exc.retryable,
            )
        except Exception as exc:
            out = err(
                tool=canonical,
                request_id=request_id,
                idempotency_key=idempotency_key,
                timestamp=ts,
                error_code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
                details={"tool": canonical, "traceback": traceback.format_exc() if os.getenv("WM_DEBUG") else None},
                retryable=False,
            )
        else:
            # Normalize into the stable envelope.
            out = normalize_raw(
                tool=canonical,
                request_id=request_id,
                idempotency_key=str(idempotency_key) if idempotency_key else None,
                timestamp=ts,
                raw=raw,
            )

        # Ensure write tools include an explicit writes hint.
        if tool_def is not None and tool_def.safety != ToolSafety.READ and not out.get("writes"):
            out["writes"] = _tool_writes_hint(canonical)

        # Persist idempotency result on success (write/delete only)
        if (
            idempotency_key
            and not dry_run
            and tool_def is not None
            and tool_def.safety != ToolSafety.READ
            and out.get("status") == "success"
        ):
            try:
                from whitemagic.tools.idempotency import put_record
                put_record(canonical, str(idempotency_key), out)
            except (ImportError, ModuleNotFoundError) as e:
                # Never fail a tool call due to idempotency persistence.
                logger.debug("Failed to persist idempotency record for %s: %s", canonical, e, exc_info=True)

        # Nervous System post-dispatch sync
        if (
            canonical not in LIGHTWEIGHT_STATUS_TOOLS
            and canonical not in FAST_INTERACTIVE_WRITE_TOOLS
        ):
            _nervous_system_post(
                canonical,
                time.time() - call_started_at,
                out.get("status") in ("success", "ok"),
            )

        # SelfModel post-dispatch recording (v23.1: auto-record metrics)
        try:
            from whitemagic.core.intelligence.self_model import get_self_model
            _sm = get_self_model()
            _elapsed = time.time() - call_started_at
            _is_success = out.get("status") in ("success", "ok")
            # Record latency (seconds)
            _sm.record("latency", _elapsed)
            # Record error rate (1.0 for error, 0.0 for success)
            _sm.record("error_rate", 0.0 if _is_success else 1.0)
            # Record energy as inverse of latency (normalized 0-1, 5s+ = 0)
            _sm.record("energy", max(0.0, 1.0 - _elapsed / 5.0))
            # Route critical alerts to homeostasis loop
            _sm_alerts = _sm.get_alerts()
            if _sm_alerts:
                try:
                    from whitemagic.harmony.homeostatic_loop import HomeostaticLoop
                    _loop = HomeostaticLoop()
                    _loop.check()
                except Exception:
                    pass
        except Exception:
            pass

        # v23.3: Bidirectional WM↔Scratchpad sync — attend important tool
        # results to working memory and persist to active scratchpad.
        if (
            canonical not in LIGHTWEIGHT_STATUS_TOOLS
            and out.get("status") in ("success", "ok")
        ):
            try:
                from whitemagic.core.intelligence.working_memory import (
                    get_working_memory,
                )
                _wm = get_working_memory()
                # Attend the tool result to working memory
                _result_summary = str(out.get("details", out.get("result", "")))[:300]
                if _result_summary and _result_summary != "None":
                    _wm.attend(
                        memory_id=f"dispatch:{canonical}:{request_id}",
                        content=_result_summary,
                        title=canonical,
                        importance=0.4,
                        tags=["dispatch", canonical.split(".")[0]],
                    )
                    # Sync to active scratchpad if one exists
                    try:
                        from whitemagic.config.paths import WM_ROOT
                        from whitemagic.core.memory.scratchpad_interleave import (
                            ScratchpadManager,
                        )
                        _sm_mgr = ScratchpadManager(
                            scratch_dir=WM_ROOT / "scratchpads",
                        )
                        if _sm_mgr.scratchpads:
                            _active_pad = max(
                                _sm_mgr.scratchpads.values(),
                                key=lambda p: p.last_active,
                            )
                            _sm_mgr.write_to(
                                _active_pad.name,
                                f"[{canonical}] {_result_summary[:150]}",
                                tag="dispatch_sync",
                            )
                    except Exception:
                        pass  # Scratchpad sync is best-effort
            except Exception:
                pass  # Working memory attendance is best-effort

        return _finish(out)

def smart_infer(query: str, mode: str = "auto", ground_in_memory: bool = False) -> dict:
    """Unified local inference with automatic tier selection.

    Wu Wei principle: Query finds its own path (fast/explore/deep).

    Args:
        query: Query string
        mode: auto/fast/explore/deep/memory_augmented
        ground_in_memory: Use memory for RAG-style context

    Returns:
        dict with answer, tier, confidence, latency_ms, tokens_saved

    """
    return {
        "status": "error",
        "error": "Local inference (edge_infer) has been archived. Please use an external model via MCP.",
    }



def inference_stats() -> dict:
    """Get unified inference statistics."""
    return {
        "status": "error",
        "error": "Local inference (edge_stats) has been archived.",
    }


def make_result(tool: str, data: Any = None, *, error: str | None = None) -> dict[str, Any]:
    """Create a tool result envelope (legacy compatibility helper).

    Used by handler modules that need a simple positional-arg interface.
    Generates a request_id automatically.

    Args:
        tool: Tool name (e.g. ``"dream.list"``).
        data: Payload to include under ``details``.
        error: If provided, creates an error envelope with this message.

    Returns:
        Envelope dict conforming to the WhiteMagic tool contract.
    """
    from whitemagic.tools.envelope import err, ok

    request_id = str(uuid4())
    if error is not None:
        return err(
            tool=tool,
            request_id=request_id,
            error_code="internal_error",
            message=error,
            details=data,
        )
    return ok(tool=tool, request_id=request_id, details=data)
