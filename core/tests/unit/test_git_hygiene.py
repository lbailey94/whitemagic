from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from whitemagic.harmony.git_hygiene import (
    GitHygieneReport,
    GitRepoStatus,
    evaluate_git_hygiene,
)


def _mock_repo(porcelain_output: str, branch: str = "main") -> MagicMock:
    """Return a side_effect for subprocess.run that answers git status/branch."""
    def side_effect(cmd, **kwargs):
        result = MagicMock()
        if "branch" in cmd:
            result.stdout = branch + "\n"
            result.returncode = 0
        elif "status" in cmd:
            result.stdout = porcelain_output
            result.stderr = ""
            result.returncode = 0
        return result
    return side_effect


def test_git_hygiene_clean_repo(tmp_path: Path) -> None:
    workspace = tmp_path / "Agent-SafetyBench"
    workspace.mkdir()
    (workspace / ".git").mkdir()

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(""),
    ):
        report = evaluate_git_hygiene(tmp_path, ("Agent-SafetyBench",))

    assert report.total_repos == 1
    assert report.clean_repos == 1
    assert report.dirty_repos == 0
    assert report.health_score == 1.0
    assert report.status == "healthy"


def test_git_hygiene_detects_dirty_repo(tmp_path: Path) -> None:
    workspace = tmp_path / "WHITEMAGIC"
    workspace.mkdir()
    (workspace / ".git").mkdir()

    porcelain = (
        " M core/whitemagic/harmony/homeostatic_loop.py\n"
        " D core/scripts/legacy.sh\n"
        "?? core/whitemagic/harmony/git_hygiene.py\n"
    )

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(porcelain),
    ):
        report = evaluate_git_hygiene(tmp_path, ("WHITEMAGIC",))

    status = report.statuses[0]
    assert status.modified == ["core/whitemagic/harmony/homeostatic_loop.py"]
    assert status.deleted == ["core/scripts/legacy.sh"]
    assert status.untracked == ["core/whitemagic/harmony/git_hygiene.py"]
    assert status.total_changes == 3
    assert report.health_score == 0.97
    assert report.status == "healthy"


def test_git_hygiene_non_git_repo_is_neutral(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(""),
    ):
        report = evaluate_git_hygiene(tmp_path, ("reports",))

    status = report.statuses[0]
    assert not status.is_git_repo
    assert status.warnings == ["not a git repository"]
    assert report.total_repos == 0
    assert report.health_score == 1.0


def test_git_hygiene_markdown_output(tmp_path: Path) -> None:
    workspace = tmp_path / "WHITEMAGIC"
    workspace.mkdir()
    (workspace / ".git").mkdir()

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(" M README.md\n"),
    ):
        report = evaluate_git_hygiene(tmp_path, ("WHITEMAGIC",))

    markdown = report.to_markdown()
    assert "# Git Hygiene Report" in markdown
    assert "`WHITEMAGIC`" in markdown
    assert "1" in markdown


def test_git_hygiene_categorizes_changes(tmp_path: Path) -> None:
    workspace = tmp_path / "WHITEMAGIC"
    workspace.mkdir()
    (workspace / ".git").mkdir()

    porcelain = (
        " M core/whitemagic/harmony/git_hygiene.py\n"
        " M README.md\n"
        "?? tests/unit/test_git_hygiene.py\n"
        "?? core/scripts/git_hygiene.py\n"
    )

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(porcelain),
    ):
        report = evaluate_git_hygiene(tmp_path, ("WHITEMAGIC",))

    categorized = report.statuses[0].categorized_changes()
    assert "core/whitemagic/harmony/git_hygiene.py" in categorized["code"]
    assert "README.md" in categorized["docs"]
    assert "tests/unit/test_git_hygiene.py" in categorized["tests"]
    assert "core/scripts/git_hygiene.py" in categorized["scripts"]


def test_homeostatic_loop_git_hygiene_check_healthy(tmp_path: Path) -> None:
    from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

    workspace = tmp_path / "Agent-SafetyBench"
    report = GitHygieneReport(
        root=str(tmp_path),
        generated_at="2026-06-27T14:00:00",
        statuses=[
            GitRepoStatus(
                name="Agent-SafetyBench",
                root=str(workspace),
                is_git_repo=True,
                branch="main",
                modified=[],
                deleted=[],
                untracked=[],
                errors=[],
                warnings=[],
            )
        ],
    )
    with patch(
        "whitemagic.harmony.git_hygiene.evaluate_git_hygiene",
        return_value=report,
    ):
        actions = HomeostaticLoop()._check_git_hygiene()

    assert actions == []


def test_homeostatic_loop_git_hygiene_check_degraded(tmp_path: Path) -> None:
    workspace = tmp_path / "WHITEMAGIC"
    workspace.mkdir()
    (workspace / ".git").mkdir()

    from whitemagic.harmony.homeostatic_loop import ActionLevel, HomeostaticLoop

    with patch(
        "whitemagic.harmony.git_hygiene.subprocess.run",
        side_effect=_mock_repo(" M README.md\n" * 50),
    ):
        report = evaluate_git_hygiene(tmp_path, ("WHITEMAGIC",))

    with patch(
        "whitemagic.harmony.git_hygiene.evaluate_git_hygiene",
        return_value=report,
    ):
        actions = HomeostaticLoop()._check_git_hygiene()

    assert len(actions) == 1
    assert actions[0].dimension == "git_hygiene"
    assert actions[0].level == ActionLevel.CORRECT
    assert "Git hygiene issues" in actions[0].action_taken
