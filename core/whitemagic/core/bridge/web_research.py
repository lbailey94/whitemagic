# ruff: noqa: BLE001

from __future__ import annotations

from typing import Any, TypeVar, cast

from whitemagic.utils.async_bridge import run_async as _run_async

T = TypeVar("T")


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.core.ports import emit_gan_ying

    emit_gan_ying(event_type, data)




def research_topic(**kwargs: Any) -> dict[str, Any]:
    """Deep research on a topic: search, fetch, synthesize."""
    topic = kwargs.get("topic", "")
    if not topic:
        raise ValueError("topic is required")

    num_search_results = int(kwargs.get("num_search_results", 6))
    max_sources = int(kwargs.get("max_sources", 4))
    max_chars_per_source = int(kwargs.get("max_chars_per_source", 15_000))

    from whitemagic.gardens.browser.web_research import (
        research_topic as _research_topic,
    )

    async def _research() -> dict[str, Any]:
        report = await _research_topic(
            topic,
            num_search_results=num_search_results,
            max_sources_to_fetch=max_sources,
            max_chars_per_source=max_chars_per_source,
        )
        data = cast(dict[str, Any], report.to_dict())
        data["findings"] = [
            {
                **finding.to_dict(),
                "content": finding.content,
                "content_length": len(finding.content),
            }
            for finding in report.findings
        ]
        return data

    result = cast(dict[str, Any], _run_async(_research()))
    _emit(
        "RESEARCH_TOPIC",
        {
            "topic": topic,
            "sources": result.get("sources_fetched", 0),
            "duration_ms": result.get("duration_ms"),
        },
    )
    return {"status": "success", **result}
