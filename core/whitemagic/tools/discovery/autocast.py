# ruff: noqa: BLE001
"""Tool Discovery & Autocast System - Context-Aware Tool Suggestions

Analyzes tool usage patterns, context, and metrics to suggest next tools.
Integrates with Gan Ying bus for real-time awareness.
"""

import logging
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

logger = logging.getLogger(__name__)


@dataclass
class ToolUsageMetrics:
    """Track tool usage patterns."""

    tool_name: str
    call_count: int = 0
    last_called: datetime | None = None
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    context_tags: set[str] = field(default_factory=set)
    follows_tools: dict[str, int] = field(
        default_factory=dict
    )  # What tools typically follow this one
    precedes_tools: dict[str, int] = field(
        default_factory=dict
    )  # What tools typically precede this one


class ToolDiscovery:
    """Discover and suggest tools based on context and usage patterns."""

    def __init__(self, max_history: int = 1000):
        self.metrics: dict[str, ToolUsageMetrics] = {}
        self.recent_calls: deque[tuple[str, datetime]] = deque(maxlen=max_history)
        self.context_stack: list[str] = []
        self.gan_ying_enabled = False

        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                get_bus,
            )

            self.gan_ying: Any = get_bus()
            self.gan_ying_enabled = True
            logger.debug("Tool discovery connected to Gan Ying bus")
        except Exception as e:
            logger.debug("Gan Ying bus not available: %s", e, exc_info=True)
            self.gan_ying = None

    def record_call(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
        context_tags: list[str] | None = None,
    ) -> None:
        """Record a tool call for pattern analysis."""
        now = datetime.now()

        if tool_name not in self.metrics:
            self.metrics[tool_name] = ToolUsageMetrics(tool_name=tool_name)

        metric = self.metrics[tool_name]

        # Update metrics
        metric.call_count += 1
        metric.last_called = now

        # Update rolling average latency
        if metric.avg_latency_ms == 0:
            metric.avg_latency_ms = latency_ms
        else:
            metric.avg_latency_ms = (metric.avg_latency_ms * 0.9) + (latency_ms * 0.1)

        # Update success rate
        if success:
            metric.success_rate = (metric.success_rate * 0.95) + 0.05
        else:
            metric.success_rate = metric.success_rate * 0.95

        # Update context tags
        if context_tags:
            metric.context_tags.update(context_tags)

        # Track sequential patterns
        if len(self.recent_calls) > 0:
            prev_tool, _ = self.recent_calls[-1]
            if prev_tool != tool_name:
                # Don't track self-loops
                # This tool follows prev_tool
                metric.precedes_tools[prev_tool] = (
                    metric.precedes_tools.get(prev_tool, 0) + 1
                )
                # prev_tool is followed by this tool
                if prev_tool in self.metrics:
                    self.metrics[prev_tool].follows_tools[tool_name] = (
                        self.metrics[prev_tool].follows_tools.get(tool_name, 0) + 1
                    )

        # Record in history
        self.recent_calls.append((tool_name, now))

        # Emit to Gan Ying bus
        if self.gan_ying_enabled and self.gan_ying:
            try:
                from whitemagic.core.resonance.gan_ying_enhanced import (
                    EventType,
                    ResonanceEvent,
                )

                event = ResonanceEvent(
                    source="tool_discovery",
                    event_type=EventType.SYSTEM_HEARTBEAT,  # Defaulting to heartbeat for usage
                    data={
                        "tool": tool_name,
                        "latency_ms": latency_ms,
                        "success": success,
                        "context": context_tags or [],
                    },
                    confidence=0.8,
                )
                self.gan_ying.emit(event, cascade=True)
            except (ImportError, AttributeError):
                pass

    def discover_by_category(self, category: str) -> list[dict[str, Any]]:
        """Discover tools by category."""
        try:
            from whitemagic.tools.tool_surface import get_callable_tool_definitions

            tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category.value,
                    "usage_count": self.metrics.get(
                        t.name, ToolUsageMetrics(t.name)
                    ).call_count,
                }
                for t in get_callable_tool_definitions()
                if t.category.value == category
            ]

            # Sort by usage count
            tools.sort(key=lambda x: x["usage_count"], reverse=True)  # type: ignore[arg-type, return-value]
            return tools
        except Exception as e:
            logger.error("Tool discovery failed: %s", e, exc_info=True)
            return []

    def discover_by_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Discover tools by search query."""
        try:
            from whitemagic.tools.tool_surface import get_callable_tool_definitions

            query_lower = query.lower()
            tools = []

            for t in get_callable_tool_definitions():
                score = 0
                if query_lower in t.name.lower():
                    score += 10
                if query_lower in t.description.lower():
                    score += 5

                # Boost by usage
                usage = self.metrics.get(t.name, ToolUsageMetrics(t.name))
                score += min(usage.call_count, 5)

                if score > 0:
                    tools.append(
                        {
                            "name": t.name,
                            "description": t.description,
                            "category": t.category.value,
                            "score": score,
                            "usage_count": usage.call_count,
                        }
                    )

            tools.sort(key=lambda x: x["score"], reverse=True)
            return tools[:limit]
        except Exception as e:
            logger.error("Tool search failed: %s", e, exc_info=True)
            return []

    def autocast_suggestions(
        self,
        current_context: list[str] | None = None,
        num_suggestions: int = 5,
        include_random: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate context-aware tool suggestions (autocast).

        Suggests tools based on:
        - Sequential patterns (what typically follows recent tools)
        - Context similarity
        - Underutilized tools (haven't been called recently)
        - Random exploration (for discovering new synergies)
        """
        suggestions = []
        now = datetime.now()

        # Strategy 1: Sequential patterns (40% weight)
        if len(self.recent_calls) > 0:
            last_tool, _ = self.recent_calls[-1]
            if last_tool in self.metrics:
                follows = self.metrics[last_tool].follows_tools
                if follows:
                    top_follows = sorted(
                        follows.items(), key=lambda x: x[1], reverse=True
                    )[:3]
                    for tool_name, count in top_follows:
                        suggestions.append(
                            {
                                "tool": tool_name,
                                "reason": f"Often follows {last_tool}",
                                "confidence": min(count / 10.0, 0.9),
                                "strategy": "sequential",
                            }
                        )

        # Strategy 2: Context similarity (30% weight)
        if current_context:
            context_set = set(current_context)
            for tool_name, metric in self.metrics.items():
                if metric.context_tags:
                    overlap = len(context_set & metric.context_tags)
                    if overlap > 0:
                        suggestions.append(
                            {
                                "tool": tool_name,
                                "reason": f"Matches {overlap} context tags",
                                "confidence": min(overlap / len(context_set), 0.8),
                                "strategy": "context",
                            }
                        )

        # Strategy 3: Underutilized tools (20% weight)
        underutilized = []
        for tool_name, metric in self.metrics.items():
            if metric.last_called:
                time_since = (now - metric.last_called).total_seconds()
                if time_since > 3600:
                    # Not called in last hour
                    underutilized.append(
                        {
                            "tool": tool_name,
                            "reason": f"Not used in {int(time_since / 3600)}h",
                            "confidence": 0.5,
                            "strategy": "underutilized",
                        }
                    )

        if underutilized:
            # Pick top 2 underutilized
            underutilized.sort(
                key=lambda x: (
                    self.metrics[cast(str, x["tool"])].last_called or datetime.min
                )
            )
            suggestions.extend(underutilized[:2])

        # Strategy 4: Random exploration (10% weight)
        if include_random:
            try:
                from whitemagic.tools.tool_surface import get_callable_tool_definitions

                # Pick 1-2 random tools not in recent calls
                recent_tool_names = {name for name, _ in self.recent_calls}
                available = [
                    t.name
                    for t in get_callable_tool_definitions()
                    if t.name not in recent_tool_names
                ]

                if available:
                    num_random = min(2, len(available))
                    random_tools = random.sample(available, num_random)
                    for tool_name in random_tools:
                        suggestions.append(
                            {
                                "tool": tool_name,
                                "reason": "Random exploration (discover new synergies)",
                                "confidence": 0.3,
                                "strategy": "random",
                            }
                        )
            except (ImportError, AttributeError):
                pass

        # Deduplicate and sort by confidence
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s["tool"] not in seen:
                seen.add(s["tool"])
                unique_suggestions.append(s)

        unique_suggestions.sort(
            key=lambda x: cast(float, x["confidence"]), reverse=True
        )

        return unique_suggestions[:num_suggestions]

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """Get detailed stats for a specific tool."""
        if tool_name not in self.metrics:
            return {"error": "Tool not found in metrics"}

        metric = self.metrics[tool_name]

        return {
            "tool": tool_name,
            "call_count": metric.call_count,
            "last_called": metric.last_called.isoformat()
            if metric.last_called
            else None,
            "avg_latency_ms": round(metric.avg_latency_ms, 2),
            "success_rate": round(metric.success_rate * 100, 1),
            "context_tags": list(metric.context_tags),
            "typically_follows": [
                {"tool": t, "count": c}
                for t, c in sorted(
                    metric.precedes_tools.items(), key=lambda x: x[1], reverse=True
                )[:5]
            ],
            "typically_followed_by": [
                {"tool": t, "count": c}
                for t, c in sorted(
                    metric.follows_tools.items(), key=lambda x: x[1], reverse=True
                )[:5]
            ],
        }

    def get_global_stats(self) -> dict[str, Any]:
        """Get global tool usage statistics."""
        total_calls = sum(m.call_count for m in self.metrics.values())

        # Most used tools
        most_used = sorted(
            self.metrics.items(), key=lambda x: x[1].call_count, reverse=True
        )[:10]

        # Fastest tools
        fastest = sorted(
            [(name, m) for name, m in self.metrics.items() if m.call_count > 0],
            key=lambda x: x[1].avg_latency_ms,
        )[:10]

        # Most reliable tools
        most_reliable = sorted(
            [(name, m) for name, m in self.metrics.items() if m.call_count > 5],
            key=lambda x: x[1].success_rate,
            reverse=True,
        )[:10]

        return {
            "total_tools_tracked": len(self.metrics),
            "total_calls": total_calls,
            "most_used": [
                {"tool": name, "calls": m.call_count} for name, m in most_used
            ],
            "fastest": [
                {"tool": name, "avg_latency_ms": round(m.avg_latency_ms, 2)}
                for name, m in fastest
            ],
            "most_reliable": [
                {"tool": name, "success_rate": round(m.success_rate * 100, 1)}
                for name, m in most_reliable
            ],
        }


# Global instance
_discovery = None


def get_tool_discovery() -> ToolDiscovery:
    """Get global tool discovery instance."""
    global _discovery
    if _discovery is None:
        _discovery = ToolDiscovery()
    return _discovery
