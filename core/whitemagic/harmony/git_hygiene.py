"""Git hygiene sensor for local WhiteMagic project workspaces."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_GIT_WORKSPACES = (
    "WHITEMAGIC",
    "whitemagic-public",
    "Agent-SafetyBench",
    "reports",
    "archives",
    "vercel-deploy",
    "WHITEMAGIC-aux",
)

_CHANGE_THRESHOLD = 100.0


def _categorize(path: str) -> str:
    lowered = path.lower()
    if "test" in lowered or path.startswith("tests/"):
        return "tests"
    if lowered.endswith(".md") or "docs/" in lowered or "grimoire/" in lowered:
        return "docs"
    if "scripts/" in lowered or lowered.endswith(".sh"):
        return "scripts"
    if any(
        lowered.endswith(ext)
        for ext in (".toml", ".json", ".yaml", ".yml", ".ini", ".cfg")
    ):
        return "config"
    if any(
        lowered.endswith(ext)
        for ext in (
            ".py",
            ".rs",
            ".ts",
            ".js",
            ".go",
            ".jl",
            ".hs",
            ".ex",
            ".zig",
            ".koka",
            ".c",
            ".h",
            ".cpp",
        )
    ):
        return "code"
    return "other"


@dataclass(frozen=True)
class GitRepoStatus:
    """Status of one local workspace from a git hygiene perspective."""

    name: str
    root: str
    is_git_repo: bool
    branch: str
    modified: list[str]
    deleted: list[str]
    untracked: list[str]
    errors: list[str]
    warnings: list[str]

    @property
    def total_changes(self) -> int:
        return len(self.modified) + len(self.deleted) + len(self.untracked)

    @property
    def healthy(self) -> bool:
        return self.is_git_repo and not self.errors and self.total_changes == 0

    def categorized_changes(self) -> dict[str, list[str]]:
        """Group changed paths by broad category."""
        result = {
            "code": [],
            "docs": [],
            "tests": [],
            "scripts": [],
            "config": [],
            "other": [],
        }
        for path in self.modified + self.deleted + self.untracked:
            result[_categorize(path)].append(path)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "root": self.root,
            "is_git_repo": self.is_git_repo,
            "branch": self.branch,
            "modified": self.modified,
            "deleted": self.deleted,
            "untracked": self.untracked,
            "total_changes": self.total_changes,
            "errors": self.errors,
            "warnings": self.warnings,
            "healthy": self.healthy,
        }


@dataclass(frozen=True)
class GitHygieneReport:
    """Aggregated git hygiene report across multiple workspaces."""

    root: str
    generated_at: str
    statuses: list[GitRepoStatus]

    @property
    def total_repos(self) -> int:
        return sum(1 for status in self.statuses if status.is_git_repo)

    @property
    def clean_repos(self) -> int:
        return sum(
            1
            for status in self.statuses
            if status.is_git_repo and status.total_changes == 0
        )

    @property
    def dirty_repos(self) -> int:
        return self.total_repos - self.clean_repos

    @property
    def total_modified(self) -> int:
        return sum(
            len(status.modified) for status in self.statuses if status.is_git_repo
        )

    @property
    def total_deleted(self) -> int:
        return sum(
            len(status.deleted) for status in self.statuses if status.is_git_repo
        )

    @property
    def total_untracked(self) -> int:
        return sum(
            len(status.untracked) for status in self.statuses if status.is_git_repo
        )

    @property
    def health_score(self) -> float:
        git_statuses = [status for status in self.statuses if status.is_git_repo]
        if not git_statuses:
            return 1.0
        scores = []
        for status in git_statuses:
            if status.errors:
                scores.append(0.0)
            elif status.total_changes == 0:
                scores.append(1.0)
            else:
                penalty = min(1.0, status.total_changes / _CHANGE_THRESHOLD)
                scores.append(1.0 - penalty)
        return sum(scores) / len(scores)

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
            "total_repos": self.total_repos,
            "clean_repos": self.clean_repos,
            "dirty_repos": self.dirty_repos,
            "total_modified": self.total_modified,
            "total_deleted": self.total_deleted,
            "total_untracked": self.total_untracked,
            "health_score": self.health_score,
            "status": self.status,
            "statuses": [status.to_dict() for status in self.statuses],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Git Hygiene Report",
            "",
            f"**Generated**: {self.generated_at}",
            f"**Root**: `{self.root}`",
            f"**Status**: `{self.status}`",
            f"**Health Score**: {self.health_score:.0%}",
            "",
            "| Workspace | Git Repo | Branch | Modified | Deleted | Untracked |",
            "|-----------|----------|--------|----------|---------|-----------|",
        ]
        for status in self.statuses:
            git_repo = "yes" if status.is_git_repo else "no"
            lines.append(
                f"| `{status.name}` | {git_repo} | `{status.branch}` | "
                f"{len(status.modified)} | {len(status.deleted)} | {len(status.untracked)} |"
            )
        return "\n".join(lines) + "\n"

    def action_summary(self) -> str:
        """Return a concise, human-readable summary of dirty trees and git errors."""
        errored = [
            status for status in self.statuses if status.is_git_repo and status.errors
        ]
        dirty = [
            status
            for status in self.statuses
            if status.is_git_repo and status.total_changes > 0
        ]
        if not dirty and not errored:
            return "All git workspaces are clean."
        parts = []
        for status in errored:
            parts.append(f"{status.name}: {len(status.errors)} git error(s)")
        for status in dirty:
            parts.append(
                f"{status.name}: {status.total_changes} changes "
                f"({len(status.modified)} modified, {len(status.deleted)} deleted, "
                f"{len(status.untracked)} untracked)"
            )
        return (
            "Git hygiene issues: "
            + "; ".join(parts)
            + ". Run core/scripts/git_hygiene.py."
        )


def default_workspace_root() -> Path:
    """Resolve the parent of the WHITEMAGIC repository root."""
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root.parent


def _run_git_status(repo: Path) -> tuple[str, str, int]:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-uall"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result.stdout, result.stderr, result.returncode


def _run_git_branch(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def evaluate_git_hygiene(
    workspace_root: str | Path | None = None,
    workspace_names: tuple[str, ...] = DEFAULT_GIT_WORKSPACES,
) -> GitHygieneReport:
    """Evaluate git hygiene across the configured local workspaces."""
    root = (
        Path(workspace_root) if workspace_root is not None else default_workspace_root()
    )
    statuses = [_inspect_repo(root, name) for name in workspace_names]
    return GitHygieneReport(
        root=str(root),
        generated_at=datetime.now(UTC).isoformat(),
        statuses=statuses,
    )


def _inspect_repo(root: Path, name: str) -> GitRepoStatus:
    repo = root / name
    errors: list[str] = []
    warnings: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    untracked: list[str] = []
    branch = ""
    is_git_repo = (repo / ".git").is_dir()

    if not repo.exists():
        errors.append("workspace root missing")
        is_git_repo = False
    elif not is_git_repo:
        warnings.append("not a git repository")

    if is_git_repo:
        try:
            branch = _run_git_branch(repo)
            stdout, stderr, returncode = _run_git_status(repo)
            if returncode != 0:
                errors.append(f"git status failed: {stderr.strip()}")
            else:
                for line in stdout.splitlines():
                    if not line:
                        continue
                    code = line[:2]
                    path = line[3:]
                    if code == "??":
                        untracked.append(path)
                    elif "D" in code:
                        deleted.append(path)
                    else:
                        modified.append(path)
        except subprocess.SubprocessError as e:
            errors.append(f"git subprocess error: {e}")
        except FileNotFoundError:
            errors.append("git executable not found")

    return GitRepoStatus(
        name=name,
        root=str(repo),
        is_git_repo=is_git_repo,
        branch=branch,
        modified=modified,
        deleted=deleted,
        untracked=untracked,
        errors=errors,
        warnings=warnings,
    )
