from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from whitemagic.harmony.workspace_index_health import evaluate_workspace_index_health


def test_workspace_index_health_all_present(tmp_path: Path) -> None:
    for name in ("WHITEMAGIC", "reports"):
        workspace = tmp_path / name
        workspace.mkdir()
        (workspace / "INDEX.md").write_text(f"# {name}\n", encoding="utf-8")

    report = evaluate_workspace_index_health(tmp_path, ("WHITEMAGIC", "reports"))

    assert report.indexes_present == 2
    assert report.total_errors == 0
    assert report.health_score == 1.0
    assert report.status == "healthy"


def test_workspace_index_health_missing_index(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()

    report = evaluate_workspace_index_health(tmp_path, ("reports",))

    assert report.indexes_present == 0
    assert report.total_errors == 1
    assert report.status == "degraded"
    assert report.statuses[0].errors == ["INDEX.md missing"]


def test_workspace_index_health_detects_unresolved_index_links(tmp_path: Path) -> None:
    workspace = tmp_path / "WHITEMAGIC"
    workspace.mkdir()
    (workspace / "INDEX.md").write_text(
        "# WhiteMagic\n\n| Workspace | Index |\n|---|---|\n| missing | `../missing/INDEX.md` |\n",
        encoding="utf-8",
    )

    report = evaluate_workspace_index_health(tmp_path, ("WHITEMAGIC",))

    assert report.total_errors == 0
    assert report.total_warnings == 1
    assert report.statuses[0].unresolved_index_links == ["../missing/INDEX.md"]
    assert report.status == "advisory"


def test_workspace_index_health_markdown_output(tmp_path: Path) -> None:
    workspace = tmp_path / "archives"
    workspace.mkdir()
    (workspace / "INDEX.md").write_text("# Archives\n", encoding="utf-8")

    report = evaluate_workspace_index_health(tmp_path, ("archives",))
    markdown = report.to_markdown()

    assert "# Workspace Index Health Report" in markdown
    assert "`archives`" in markdown
    assert "present" in markdown


def test_homeostatic_loop_workspace_index_check_healthy(tmp_path: Path) -> None:
    workspace = tmp_path / "reports"
    workspace.mkdir()
    (workspace / "INDEX.md").write_text("# Reports\n", encoding="utf-8")

    from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

    report = evaluate_workspace_index_health(tmp_path, ("reports",))
    with patch(
        "whitemagic.harmony.workspace_index_health.evaluate_workspace_index_health",
        return_value=report,
    ):
        actions = HomeostaticLoop()._check_workspace_indexes()

    assert actions == []


def test_homeostatic_loop_workspace_index_check_degraded(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()

    from whitemagic.harmony.homeostatic_loop import ActionLevel, HomeostaticLoop

    report = evaluate_workspace_index_health(tmp_path, ("reports",))
    with patch(
        "whitemagic.harmony.workspace_index_health.evaluate_workspace_index_health",
        return_value=report,
    ):
        actions = HomeostaticLoop()._check_workspace_indexes()

    assert len(actions) == 1
    assert actions[0].dimension == "workspace_indexes"
    assert actions[0].level == ActionLevel.CORRECT
