# ruff: noqa: BLE001
"""Durable Archive — Git-backed experiment persistence (v24.3.0).

Implements the 3-layer collaboration stack from Hyperspace AGI:
    Layer 1: GossipSub (real-time gossip) — via ExperimentSync
    Layer 2: Loro CRDT (convergent state) — via CRDTLeaderboard
    Layer 3: Git archive (durable) — THIS MODULE

The durable archive periodically snapshots experiment breakthroughs and
syntheses to a local git branch, ensuring provenance survives even if
the SQLite database is corrupted or lost.

Archive strategy:
    - Every 5 minutes (configurable), check for new breakthroughs/syntheses
    - Export them as structured markdown files
    - Commit to a dedicated `research-archive` branch
    - Push to remote if configured (optional)

Integration points:
    - ResearchDAG: source of breakthroughs and syntheses
    - ConsciousnessLoop: triggers archive via mesh_sync tick
    - MeshClient: optional remote push
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.core.evolution.research_dag import (
    Experiment,
    ExperimentStage,
    get_research_dag,
)

logger = logging.getLogger(__name__)


@dataclass
class ArchiveStats:
    """Statistics for the durable archive."""

    archive_runs: int = 0
    experiments_archived: int = 0
    syntheses_archived: int = 0
    commits_made: int = 0
    last_archive_time: float = 0.0
    last_error: str = ""


class DurableArchive:
    """Git-backed durable archive for experiment breakthroughs.

    Periodically snapshots breakthroughs and syntheses to a local git
    branch for durable provenance tracking.
    """

    _instance: DurableArchive | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._dag = get_research_dag()
        self._stats = ArchiveStats()
        self._stats_lock = threading.RLock()
        self._archived_ids: set[str] = set()
        self._archived_lock = threading.RLock()
        self._archive_dir = self._get_archive_dir()

    def _get_archive_dir(self) -> Path:
        """Get the archive directory path."""
        state_root = os.environ.get(
            "WM_STATE_ROOT", os.path.expanduser("~/.whitemagic")
        )
        archive_path = Path(state_root) / "research-archive"
        archive_path.mkdir(parents=True, exist_ok=True)
        return archive_path

    @classmethod
    def get_instance(cls) -> DurableArchive:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def archive_new(
        self,
        force: bool = False,
    ) -> dict[str, Any]:
        """Archive new breakthroughs and syntheses to the durable store.

        Args:
            force: If True, re-archive even already-archived experiments.

        Returns:
            Dict with archive results.
        """
        start = time.time()
        archived_experiments = 0
        archived_syntheses = 0
        errors: list[str] = []

        try:
            # Get breakthroughs
            breakthroughs = self._dag.get_breakthroughs(limit=50)
            # Get syntheses
            syntheses = self._dag.get_experiments(
                stage=ExperimentStage.SYNTHESIS,
                limit=50,
            )

            with self._archived_lock:
                for exp in breakthroughs:
                    if not force and exp.experiment_id in self._archived_ids:
                        continue
                    try:
                        self._write_experiment_file(exp, category="breakthrough")
                        self._archived_ids.add(exp.experiment_id)
                        archived_experiments += 1
                    except Exception as e:
                        errors.append(f"breakthrough {exp.experiment_id[:8]}: {e}")

                for exp in syntheses:
                    if not force and exp.experiment_id in self._archived_ids:
                        continue
                    try:
                        self._write_experiment_file(exp, category="synthesis")
                        self._archived_ids.add(exp.experiment_id)
                        archived_syntheses += 1
                    except Exception as e:
                        errors.append(f"synthesis {exp.experiment_id[:8]}: {e}")

            # Commit if we archived anything
            commits = 0
            if archived_experiments > 0 or archived_syntheses > 0:
                commits = self._git_commit(
                    f"Archive: {archived_experiments} breakthroughs, {archived_syntheses} syntheses"
                )

            # Update stats
            with self._stats_lock:
                self._stats.archive_runs += 1
                self._stats.experiments_archived += archived_experiments
                self._stats.syntheses_archived += archived_syntheses
                self._stats.commits_made += commits
                self._stats.last_archive_time = time.time()
                if errors:
                    self._stats.last_error = errors[0]

            duration = time.time() - start
            logger.info(
                "Durable archive: %d breakthroughs, %d syntheses, %d commits (%.2fs)",
                archived_experiments, archived_syntheses, commits, duration,
            )

            return {
                "status": "success",
                "breakthroughs_archived": archived_experiments,
                "syntheses_archived": archived_syntheses,
                "commits": commits,
                "errors": errors[:5],
                "duration_s": round(duration, 2),
            }

        except Exception as e:
            with self._stats_lock:
                self._stats.last_error = str(e)
            logger.error("Durable archive failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def _write_experiment_file(
        self,
        exp: Experiment,
        category: str = "breakthrough",
    ) -> None:
        """Write an experiment as a structured markdown file."""
        # Organize by domain and category
        domain_dir = self._archive_dir / exp.domain.value / category
        domain_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{exp.experiment_id[:16]}.md"
        filepath = domain_dir / filename

        # Build markdown content
        lines = [
            f"# {exp.hypothesis}",
            "",
            f"**Experiment ID**: {exp.experiment_id}",
            f"**Domain**: {exp.domain.value}",
            f"**Stage**: {exp.stage.value}",
            f"**Fitness Score**: {exp.fitness_score:.4f}",
            f"**Agent**: {exp.agent_id}",
            f"**Galactic Zone**: {exp.galactic_zone}",
            f"**Created**: {exp.created_at}",
            f"**Updated**: {exp.updated_at}",
            f"**Archived**: {datetime.now().isoformat()}",
            "",
        ]

        if exp.parameters:
            lines.append("## Parameters")
            lines.append("```json")
            lines.append(json.dumps(exp.parameters, indent=2, default=str))
            lines.append("```")
            lines.append("")

        if exp.metadata:
            lines.append("## Metadata")
            lines.append("```json")
            lines.append(json.dumps(exp.metadata, indent=2, default=str))
            lines.append("```")
            lines.append("")

        if exp.critiques:
            lines.append("## Critiques")
            for c in exp.critiques:
                lines.append(f"- **{c.get('critic_agent_id', 'unknown')}**: "
                             f"score={c.get('score', 'N/A')} — "
                             f"{c.get('notes', '')[:100]}")
            lines.append("")

        if exp.inspiration_ids:
            lines.append("## Inspirations")
            for insp_id in exp.inspiration_ids:
                lines.append(f"- {insp_id}")
            lines.append("")

        filepath.write_text("\n".join(lines), encoding="utf-8")

    def _git_commit(self, message: str) -> int:
        """Commit archived files to git. Returns 1 if committed, 0 if not."""
        try:
            # Check if git is initialized in archive dir
            git_dir = self._archive_dir / ".git"
            if not git_dir.exists():
                # Initialize git repo
                subprocess.run(
                    ["git", "init"],
                    cwd=str(self._archive_dir),
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["git", "checkout", "-b", "research-archive"],
                    cwd=str(self._archive_dir),
                    capture_output=True,
                    timeout=10,
                )

            # Add all files
            result = subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self._archive_dir),
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.debug("Git add failed: %s", result.stderr.decode())
                return 0

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(self._archive_dir),
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                # No changes
                return 0

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self._archive_dir),
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug("Git commit: %s", message)
                return 1
            else:
                logger.debug("Git commit failed: %s", result.stderr.decode())
                return 0

        except Exception as e:
            logger.debug("Git commit error: %s", e, exc_info=True)
            return 0

    def get_status(self) -> dict[str, Any]:
        """Get archive status."""
        with self._stats_lock:
            stats = {
                "archive_runs": self._stats.archive_runs,
                "experiments_archived": self._stats.experiments_archived,
                "syntheses_archived": self._stats.syntheses_archived,
                "commits_made": self._stats.commits_made,
                "last_archive_time": self._stats.last_archive_time,
                "last_error": self._stats.last_error,
            }

        with self._archived_lock:
            archived_count = len(self._archived_ids)

        # Count files in archive
        file_count = 0
        try:
            for root, _dirs, files in os.walk(self._archive_dir):
                file_count += sum(1 for f in files if f.endswith(".md"))
        except Exception:
            pass

        return {
            **stats,
            "archived_ids_tracked": archived_count,
            "archive_dir": str(self._archive_dir),
            "files_on_disk": file_count,
            "git_initialized": (self._archive_dir / ".git").exists(),
        }


def get_durable_archive() -> DurableArchive:
    """Get the singleton DurableArchive instance."""
    return DurableArchive.get_instance()
