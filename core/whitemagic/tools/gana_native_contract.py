from __future__ import annotations

from typing import Any

from whitemagic.tools.envelope import normalize_raw

STANDARD_NATIVE_DETAIL_ORDER = [
    "gana",
    "operation",
    "mode",
    "note",
    "available_tools",
    "output",
    "garden",
    "garden_status",
    "mansion",
    "successor_hint",
    "execution_ms",
    "karma_trace",
    "predecessor_context",
    "lunar_amplification",
    "_koka_latency_ms",
    "_resonance",
    "_koka_path",
]



def build_native_gana_details(
    gana_name: str,
    *,
    operation: str | None,
    mode: str | None = None,
    note: str | None = None,
    available_tools: list[str] | None = None,
    output: Any = None,
    garden: str | None = None,
    garden_status: Any = None,
    mansion: str | None = None,
    successor_hint: str | None = None,
    execution_ms: float | int | None = None,
    karma_trace: Any = None,
    predecessor_context: Any = None,
    lunar_amplification: str | None = None,
    resonance: Any = None,
    koka_latency_ms: float | int | None = None,
    koka_path: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "gana": gana_name,
        "operation": operation,
        "mode": mode,
        "note": note,
        "available_tools": available_tools,
        "output": output,
        "garden": garden,
        "garden_status": garden_status,
        "mansion": mansion,
        "successor_hint": successor_hint,
        "execution_ms": execution_ms,
        "karma_trace": karma_trace,
        "predecessor_context": predecessor_context,
        "lunar_amplification": lunar_amplification,
        "_koka_latency_ms": koka_latency_ms,
        "_resonance": resonance,
        "_koka_path": koka_path,
    }
    if extra:
        for key, value in extra.items():
            if key not in details:
                details[key] = value
            elif details[key] is None:
                details[key] = value
    return {key: value for key, value in details.items() if value is not None}



def normalize_native_gana_result(
    gana_name: str,
    *,
    request_id: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in STANDARD_NATIVE_DETAIL_ORDER:
        if key in details:
            ordered[key] = details[key]
    for key, value in details.items():
        if key not in ordered:
            ordered[key] = value
    return normalize_raw(
        tool=gana_name,
        request_id=request_id,
        raw={"status": "success", **ordered},
    )
