from whitemagic.runtime_status import get_runtime_status
from whitemagic.tools.dispatch_table import dispatch  # noqa: F401
from whitemagic.tools.handlers.introspection import handle_health_report
from whitemagic.tools.tool_surface import GANA_NAMES, get_surface_counts


def test_runtime_status_exposes_canonical_surface_counts():
    status = get_runtime_status()
    assert status["version"]
    assert status["surface_counts"]["gana_tools"] == len(GANA_NAMES) == 28
    assert status["surface_counts"] == get_surface_counts()
    assert "degraded_mode" in status
    assert "debug_enabled" in status


def test_health_report_includes_runtime_and_degraded_fields():
    report = handle_health_report()
    assert report["status"] == "success"
    assert "runtime" in report
    assert "degraded_mode" in report
    assert "degraded_reasons" in report
    assert "debug_enabled" in report
    assert report["runtime"]["surface_counts"]["gana_tools"] == 28
    assert report["health_status"] in {"healthy", "degraded", "critical"}


def test_unknown_tool_returns_resolution_envelope():
    from whitemagic.tools.unified_api import call_tool

    result = call_tool("totally_nonexistent_tool_xyz_12345")
    assert result is not None
    assert result["status"] == "error"
    assert result.get("error_code") in ("tool_not_found", "internal_error")
    assert "resolution" in result or "message" in result
