from typing import Any, cast

from whitemagic.core.bridge.wisdom import consult_full_council


def run_kaizen_analysis(auto_fix: bool = False, **kwargs: Any) -> dict[str, Any]:
    """Run Kaizen continuous improvement analysis."""
    from whitemagic.core.intelligence.synthesis.kaizen_engine import get_kaizen_engine

    engine = get_kaizen_engine()

    if auto_fix:
        return cast(dict[str, Any], engine.apply_auto_fixes())

    report = engine.analyze()

    return {
        "timestamp": report.timestamp.isoformat(),
        "metrics": report.metrics,
        "proposals": [
            {
                "id": p.id,
                "category": p.category,
                "title": p.title,
                "impact": p.impact,
                "effort": p.effort,
                "auto_fixable": p.auto_fixable,
            }
            for p in report.proposals
        ],
        "summary": {cat: len(items) for cat, items in report.by_category.items()},
    }


def kaizen_analyze(**kwargs: Any) -> dict[str, Any]:
    """Backward-compatible tool name used by the MCP bridge."""
    return run_kaizen_analysis(auto_fix=False, **kwargs)


def analyze_wu_xing_phase(
    description: str | None = None,
    question: str | None = None,
    operation: str = "analyze",
    task_type: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Analyze Wu Xing phase or get recommendations."""
    if question:
        return cast(dict[str, Any], consult_full_council(question=question, urgency="normal", **kwargs))
    if description:
        return cast(dict[str, Any], consult_full_council(
            question=f"Wu Xing analysis: {description}",
            urgency="normal",
            **kwargs,
        ))
    if task_type:
        return cast(dict[str, Any], consult_full_council(
            question=f"Wu Xing analysis for task type: {task_type}",
            urgency="normal",
            **kwargs,
        ))
    return {"error": "Either description, question, or task_type must be provided"}
