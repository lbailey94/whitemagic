"""Goal Graph — Intentional memory that persists across sessions.

Tracks goals (decisions), their dependencies, outcomes, and status.
This is the "intentional memory" layer that connects "decided to pursue X"
→ "working on Y" → "X and Y related because Z".

The goal graph is persisted to WM_STATE_ROOT/goal_graph.json and loaded
on session start, providing cross-session continuity of intention.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config import paths as paths_mod

logger = logging.getLogger(__name__)

class GoalStatus(Enum):
    """Lifecycle states for a goal."""
    PROPOSED = "proposed"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    DEFERRED = "deferred"


class GoalType(Enum):
    """Types of goals mapped to the 7+1 directive taxonomy."""
    BUILD = "build"
    FIX = "fix"
    RESEARCH = "research"
    IMPROVE = "improve"
    AUDIT = "audit"
    TEST = "test"
    DISCUSS = "discuss"
    CONNECT = "connect"
    EXPLORE = "explore"


@dataclass
class Goal:
    """A single goal node in the goal graph."""
    id: str
    title: str
    goal_type: GoalType
    status: GoalStatus = GoalStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    dependencies: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    related_sessions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "goal_type": self.goal_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "dependencies": self.dependencies,
            "blocks": self.blocks,
            "outcomes": self.outcomes,
            "related_sessions": self.related_sessions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Goal:
        return cls(
            id=data["id"],
            title=data["title"],
            goal_type=GoalType(data.get("goal_type", "build")),
            status=GoalStatus(data.get("status", "proposed")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            completed_at=data.get("completed_at"),
            dependencies=data.get("dependencies", []),
            blocks=data.get("blocks", []),
            outcomes=data.get("outcomes", []),
            related_sessions=data.get("related_sessions", []),
            metadata=data.get("metadata", {}),
        )


class GoalGraph:
    """Persistent goal graph for cross-session intention tracking.

    Goals are created from decisions, updated with outcomes, and
    connected via dependencies. The graph is persisted to disk and
    loaded on session start.
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        if persist_path is None:
            persist_path = paths_mod.WM_ROOT / "goal_graph.json"
        self._path = persist_path
        self._goals: dict[str, Goal] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for goal_data in data.get("goals", []):
                    goal = Goal.from_dict(goal_data)
                    self._goals[goal.id] = goal
            except (json.JSONDecodeError, OSError, KeyError):
                logger.debug("Ignored OSError, KeyError in goal_graph.py:121")

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "goals": [g.to_dict() for g in self._goals.values()],
            "updated_at": time.time(),
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_goal(
        self,
        goal_id: str,
        title: str,
        goal_type: GoalType | str = GoalType.BUILD,
        dependencies: list[str] | None = None,
        session_id: str | None = None,
    ) -> Goal:
        if isinstance(goal_type, str):
            goal_type = GoalType(goal_type)
        goal = Goal(
            id=goal_id,
            title=title,
            goal_type=goal_type,
            dependencies=dependencies or [],
            related_sessions=[session_id] if session_id else [],
        )
        self._goals[goal_id] = goal
        self._save()
        return goal

    def update_status(
        self,
        goal_id: str,
        status: GoalStatus | str,
        outcome: str | None = None,
    ) -> Goal | None:
        if isinstance(status, str):
            status = GoalStatus(status)
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        goal.status = status
        goal.updated_at = time.time()
        if status == GoalStatus.COMPLETED:
            goal.completed_at = time.time()
        if outcome:
            goal.outcomes.append(outcome)
        self._save()
        return goal

    def add_dependency(self, goal_id: str, depends_on: str) -> None:
        goal = self._goals.get(goal_id)
        if goal and depends_on not in goal.dependencies:
            goal.dependencies.append(depends_on)
            goal.updated_at = time.time()
            self._save()
        dep = self._goals.get(depends_on)
        if dep and goal_id not in dep.blocks:
            dep.blocks.append(goal_id)
            self._save()

    def get_active_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def get_proposed_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.PROPOSED]

    def get_blocked_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.BLOCKED]

    def get_all_goals(self) -> list[Goal]:
        return list(self._goals.values())

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def get_goals_by_type(self, goal_type: GoalType | str) -> list[Goal]:
        if isinstance(goal_type, str):
            goal_type = GoalType(goal_type)
        return [g for g in self._goals.values() if g.goal_type == goal_type]

    def get_completion_rate(self) -> float:
        total = len(self._goals)
        if total == 0:
            return 0.0
        completed = sum(1 for g in self._goals.values() if g.status == GoalStatus.COMPLETED)
        return completed / total

    def get_summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for g in self._goals.values():
            status_counts[g.status.value] = status_counts.get(g.status.value, 0) + 1
            type_counts[g.goal_type.value] = type_counts.get(g.goal_type.value, 0) + 1
        return {
            "total_goals": len(self._goals),
            "active": len(self.get_active_goals()),
            "proposed": len(self.get_proposed_goals()),
            "blocked": len(self.get_blocked_goals()),
            "completed": status_counts.get("completed", 0),
            "abandoned": status_counts.get("abandoned", 0),
            "completion_rate": round(self.get_completion_rate(), 3),
            "by_type": type_counts,
            "by_status": status_counts,
        }

    def clear(self) -> None:
        self._goals.clear()
        self._save()


_singleton: GoalGraph | None = None


def get_goal_graph() -> GoalGraph:
    global _singleton
    if _singleton is None:
        _singleton = GoalGraph()
    return _singleton
