"""Adaptive bridge handlers — PRAT context and morphology tools."""
from typing import Any

from whitemagic.core.bridge.adaptive import (
    prat_get_context,
    prat_invoke,
    prat_list_morphologies,
    prat_status,
)


def handle_prat_get_context(**kwargs: Any) -> dict[str, Any]:
    """Get unified consciousness context for PRAT morphology decisions."""
    result = prat_get_context(**kwargs)
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}


def handle_prat_invoke(**kwargs: Any) -> dict[str, Any]:
    """Invoke a tool through the PRAT adaptive portal with context-aware morphology."""
    result = prat_invoke(**kwargs)
    if isinstance(result, dict) and "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", "result": result}


def handle_prat_list_morphologies(**kwargs: Any) -> dict[str, Any]:
    """List available morphologies for PRAT tools."""
    result = prat_list_morphologies(**kwargs)
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}


def handle_prat_status(**kwargs: Any) -> dict[str, Any]:
    """Get PRAT system status."""
    result = prat_status(**kwargs)
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}
