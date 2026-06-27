"""Workspace index health sensor for local WhiteMagic workspaces."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_WORKSPACES = (
    "WHITEMAGIC",
    "whitemagic-public",
    "Agent-SafetyBench",
    "reports",
    "archives",
    "vercel-deploy",
    "WHITEMAGIC-aux",
)

_INDEX_LINK_RE = re.compile(r"`([^`]*INDEX\.md)`")


@dataclass(frozen=True)
class WorkspaceIndexStatus:
    name: str
    root: str
    root_exists: bool
    index_exists: bool
    index_path: str
    index_lines: int = 0
    index_bytes: int = 0
    unresolved_index_links: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.root_exists and self.index_exists and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "root": self.root,
            "root_exists": self.root_exists,
            "index_exists": self.index_exists,
            "index_path": self.index_path,
            "index_lines": self.index_lines,
            "index_bytes": self.index_bytes,
            "unresolved_index_links": self.unresolved_index_links,
            "errors": self.errors,
            "warnings": self.warnings,
            "healthy": self.healthy,
        }


@dataclass(frozen=True)
class WorkspaceIndexHealthReport:
    root: str
    generated_at: str
    statuses: list[WorkspaceIndexStatus]

    @property
    def total_workspaces(self) -> int:
        return len(self.statuses)

    @property
    def indexes_present(self) -> int:
        return sum(1 for status in self.statuses if status.index_exists)

    @property
    def total_errors(self) -> int:
        return sum(len(status.errors) for status in self.statuses)

    @property
    def total_warnings(self) -> int:
        return sum(len(status.warnings) for status in self.statuses)

    @property
    def health_score(self) -> float:
        if not self.statuses:
            return 1.0
        missing_penalty = self.total_workspaces - self.indexes_present
        warning_penalty = self.total_warnings * 0.25
        error_penalty = self.total_errors
        raw = 1.0 - ((missing_penalty + warning_penalty + error_penalty) / self.total_workspaces)
        return max(0.0, min(1.0, raw))

    @property
    def status(self) -> str:
        if self.health_score >= 0.9:
            return "healthy"
        if self.health_score >= 0.75:
            return "advisory"
        return "degraded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "generated_at": self.generated_at,
            "total_workspaces": self.total_workspaces,
            "indexes_present": self.indexes_present,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "health_score": self.health_score,
            "status": self.status,
            "statuses": [status.to_dict() for status in self.statuses],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Workspace Index Health Report",
            "",
            f"**Generated**: {self.generated_at}",
            f"**Root**: `{self.root}`",
            f"**Status**: `{self.status}`",
            f"**Health Score**: {self.health_score:.0%}",
            "",
            "| Workspace | Root | INDEX.md | Lines | Warnings | Errors |",
            "|-----------|------|----------|-------|----------|--------|",
        ]
        for status in self.statuses:
            index_state = "present" if status.index_exists else "missing"
            lines.append(
                f"| `{status.name}` | `{status.root}` | {index_state} | "
                f"{status.index_lines} | {len(status.warnings)} | {len(status.errors)} |"
            )
        return "\n".join(lines) + "\n"


def default_workspace_root() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root.parent


def evaluate_workspace_index_health(
    workspace_root: str | Path | None = None,
    workspace_names: tuple[str, ...] = DEFAULT_WORKSPACES,
) -> WorkspaceIndexHealthReport:
    root = Path(workspace_root) if workspace_root is not None else default_workspace_root()
    statuses = [_inspect_workspace(root, name) for name in workspace_names]
    return WorkspaceIndexHealthReport(
        root=str(root),
        generated_at=datetime.now(UTC).isoformat(),
        statuses=statuses,
    )


def _inspect_workspace(root: Path, name: str) -> WorkspaceIndexStatus:
    workspace = root / name
    index_path = workspace / "INDEX.md"
    errors: list[str] = []
    warnings: list[str] = []
    unresolved: list[str] = []

    root_exists = workspace.exists()
    index_exists = index_path.exists()
    if not root_exists:
        errors.append("workspace root missing")
    if root_exists and not index_exists:
        errors.append("INDEX.md missing")

    index_lines = 0
    index_bytes = 0
    if index_exists:
        text = index_path.read_text(encoding="utf-8")
        index_lines = len(text.splitlines())
        index_bytes = len(text.encode("utf-8"))
        unresolved = _unresolved_index_links(index_path, text)
        warnings.extend(f"unresolved index link: {link}" for link in unresolved)

    return WorkspaceIndexStatus(
        name=name,
        root=str(workspace),
        root_exists=root_exists,
        index_exists=index_exists,
        index_path=str(index_path),
        index_lines=index_lines,
        index_bytes=index_bytes,
        unresolved_index_links=unresolved,
        errors=errors,
        warnings=warnings,
    )


def _unresolved_index_links(index_path: Path, text: str) -> list[str]:
    unresolved: list[str] = []
    for match in _INDEX_LINK_RE.finditer(text):
        raw = match.group(1)
        candidate = Path(raw)
        if candidate.name == raw and raw != "INDEX.md":
            continue
        resolved = candidate if candidate.is_absolute() else index_path.parent / candidate
        if not resolved.exists():
            unresolved.append(raw)
    return unresolved
