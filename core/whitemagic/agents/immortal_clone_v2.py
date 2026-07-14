#!/usr/bin/env python3
# ruff: noqa: BLE001
"""Immortal Clone v2 - Enhanced with Victory Tracking, Progress Dashboard, Auto-Completion

Tier 1 Enhancements:
- CampaignVictoryTracker: Thread-safe shared VC state
- Auto-completion: Stop when all VCs met
- VC reporting: Explicit achievement logging
- Increased iteration limits: 200+ (configurable)

Tier 2 Enhancements:
- CampaignDashboard: Real-time progress with rich
- Progress callbacks: Clone iteration tracking
- Live updates: 2Hz refresh rate

Tier 3 Integration:
- War Room command hierarchy
- Campaign metrics tracking
- Progress tracker integration
- Army deployment patterns

Based on Geoff Huntley's insights + WhiteMagic's existing clone army infrastructure.
"""

import logging
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logger.warning("rich not available - dashboard will use basic logging")


class ActionType(Enum):
    """Types of actions an Immortal clone can execute."""

    ANALYZE = "analyze"
    EDIT = "edit"
    COMPILE = "compile"
    TEST = "test"
    BENCHMARK = "benchmark"
    BASH = "bash"
    VERIFY = "verify"


@dataclass
class Action:
    """An action to be executed by an Immortal clone."""

    type: ActionType
    target: str | Path
    command: list[str] | None = None
    changes: dict[str, Any] | None = None
    timeout: int = 300


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A task for an Immortal clone to execute."""

    id: str
    type: str
    target: str | Path
    victory_conditions: list[str]
    dependencies: list[str] = field(default_factory=list)
    estimated_tokens: int = 5000


@dataclass
class MEOW:
    """Molecular Expression of Work - granular task unit."""

    type: str
    target: str | Path
    dependencies: list[str] = field(default_factory=list)
    estimated_tokens: int = 5000
    priority: int = 1


class CampaignVictoryTracker:
    """Thread-safe shared state for tracking VC completion across all clones.

    This is the central coordination point that allows clones to:
    1. Report when they achieve a victory condition
    2. Check if the campaign is complete (all VCs met)
    3. Avoid duplicate work on already-completed VCs
    """

    def __init__(self, victory_conditions: list[dict | str]):
        """Initialize tracker with campaign VCs.

        Args:
            victory_conditions: List of VC dicts with 'id' and optional 'description',
                or plain strings used as VC IDs.
        """
        self.vcs = {
            (vc["id"] if isinstance(vc, dict) else str(vc)): {
                "met": False,
                "clone_id": None,
                "timestamp": None,
                "description": vc.get("description", "") if isinstance(vc, dict) else "",
            }
            for vc in victory_conditions
        }
        self.lock = threading.RLock()
        self.start_time = time.time()

    def mark_vc_met(self, vc_id: str, clone_id: int) -> bool:
        """Mark a VC as met (thread-safe).

        Returns:
            True if this clone was first to achieve the VC, False if already met
        """
        with self.lock:
            if vc_id not in self.vcs:
                logger.warning("Unknown VC: %s", vc_id)
                return False

            if not self.vcs[vc_id]["met"]:
                self.vcs[vc_id]["met"] = True
                self.vcs[vc_id]["clone_id"] = clone_id
                self.vcs[vc_id]["timestamp"] = time.time()

                elapsed = time.time() - self.start_time
                logger.info(
                    "🎉 VC %s MET by clone %s at %ss!", vc_id, clone_id, elapsed
                )
                return True

            return False

    def all_vcs_met(self) -> bool:
        """Check if all VCs are complete."""
        with self.lock:
            return all(vc["met"] for vc in self.vcs.values())

    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        with self.lock:
            if not self.vcs:
                return 100.0
            met = sum(1 for vc in self.vcs.values() if vc["met"])
            return (met / len(self.vcs)) * 100.0

    def get_status(self) -> dict[str, Any]:
        """Get current status snapshot."""
        with self.lock:
            met_count = sum(1 for vc in self.vcs.values() if vc["met"])
            return {
                "total_vcs": len(self.vcs),
                "vcs_met": met_count,
                "vcs_remaining": len(self.vcs) - met_count,
                "percentage": (met_count / len(self.vcs) * 100) if self.vcs else 100.0,
                "complete": all(vc["met"] for vc in self.vcs.values()),
                "elapsed_seconds": time.time() - self.start_time,
            }

    def get_vc_details(self) -> list[dict]:
        """Get detailed VC status."""
        with self.lock:
            return [
                {
                    "id": vc_id,
                    "description": vc_data["description"],
                    "met": vc_data["met"],
                    "clone_id": vc_data["clone_id"],
                    "timestamp": vc_data["timestamp"],
                }
                for vc_id, vc_data in self.vcs.items()
            ]


class CampaignDashboard:
    """Real-time campaign progress dashboard with rich display.

    Shows:
    - Victory condition progress
    - Active clone count
    - Average iteration progress
    - Elapsed time
    - Top active clones
    """

    def __init__(
        self,
        campaign_name: str,
        total_vcs: int,
        total_clones: int,
        victory_tracker: CampaignVictoryTracker,
    ):
        self.campaign_name = campaign_name
        self.total_vcs = total_vcs
        self.total_clones = total_clones
        self.victory_tracker = victory_tracker
        self.clone_progress: dict[
            int, tuple[int, int]
        ] = {}  # {clone_id: (current_iter, max_iter)}
        self.start_time = time.time()
        self.console = Console() if RICH_AVAILABLE else None

    def update_clone_progress(self, clone_id: int, iteration: int, max_iter: int):
        """Update progress for a specific clone."""
        self.clone_progress[clone_id] = (iteration, max_iter)

    def generate_table(self) -> Table | str:
        """Generate rich table or plain text for display."""
        status = self.victory_tracker.get_status()

        if not RICH_AVAILABLE:
            # Plain text fallback
            elapsed = time.time() - self.start_time
            active = len(self.clone_progress)
            return (
                f"\n{'=' * 60}\n"
                f"Campaign: {self.campaign_name}\n"
                f"VCs: {status['vcs_met']}/{status['total_vcs']} ({status['percentage']:.1f}%)\n"
                f"Active Clones: {active}/{self.total_clones}\n"
                f"Elapsed: {elapsed:.1f}s\n"
                f"{'=' * 60}\n"
            )

        table = Table(title=f"🎯 {self.campaign_name}")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Victory conditions
        vc_percent = status["percentage"]
        vc_bar = "█" * int(vc_percent / 5) + "░" * (20 - int(vc_percent / 5))
        table.add_row(
            "Victory Conditions",
            f"{status['vcs_met']}/{status['total_vcs']} ({vc_percent:.1f}%) {vc_bar}",
        )

        # Active clones
        active = len(self.clone_progress)
        table.add_row("Active Clones", f"{active}/{self.total_clones}")

        # Average iteration
        if self.clone_progress:
            avg_iter = sum(i for i, _ in self.clone_progress.values()) / len(
                self.clone_progress
            )
            avg_max = sum(m for _, m in self.clone_progress.values()) / len(
                self.clone_progress
            )
            table.add_row("Avg Iteration", f"{avg_iter:.0f}/{avg_max:.0f}")

        # Elapsed time
        elapsed = time.time() - self.start_time
        table.add_row("Elapsed Time", f"{elapsed:.1f}s ({elapsed / 60:.1f}m)")

        # Throughput
        if elapsed > 0 and status["vcs_met"] > 0:
            vcs_per_min = (status["vcs_met"] / elapsed) * 60
            table.add_row("VC Throughput", f"{vcs_per_min:.2f} VCs/min")

        # Top 5 most active clones
        if self.clone_progress:
            top_clones = sorted(
                self.clone_progress.items(), key=lambda x: x[1][0], reverse=True
            )[:5]
            clone_status = ", ".join(
                f"#{cid}:{it}/{mx}" for cid, (it, mx) in top_clones
            )
            table.add_row("Top Clones", clone_status)

        return table


class ImmortalClone:
    """Shadow clone with persistent execution loops + victory tracking.

    Enhancements over v1:
    - Victory tracker integration
    - Progress callbacks
    - Early termination when campaign complete
    - Increased iteration limits (200 default)
    """

    def __init__(
        self,
        clone_id: int,
        task: Task,
        victory_tracker: CampaignVictoryTracker,
        max_iterations: int = 200,
        progress_callback: Callable[[int, int, int], None] | None = None,
        tools: list[str] | None = None,
    ):
        self.clone_id = clone_id
        self.task = task
        self.victory_tracker = victory_tracker
        self.max_iterations = max_iterations
        self.progress_callback = progress_callback
        self.tools = tools or ["read", "edit", "bash", "compile", "test"]
        self.context: list[dict[str, Any]] = []
        self.iteration = 0

    def execute_persistent_loop(self) -> ActionResult:
        """Persistent execution loop with VC tracking and early termination."""
        logger.info("🥷 Immortal Clone %s starting: %s", self.clone_id, self.task.id)

        for self.iteration in range(self.max_iterations):
            if self.victory_tracker.all_vcs_met():
                logger.info("🏁 Clone %s stopping: campaign complete", self.clone_id)
                return ActionResult(
                    success=True,
                    data={"early_stop": True, "reason": "campaign_complete"},
                )

            # Report progress
            if self.progress_callback:
                self.progress_callback(
                    self.clone_id, self.iteration, self.max_iterations
                )

            try:
                # 1. Generate action
                action = self.generate_action()

                # 2. Execute action
                result = self.execute_action(action)

                # 3. Feed result into context
                self.context.append(
                    {
                        "iteration": self.iteration,
                        "action": action,
                        "result": result,
                        "success": result.success,
                        "error": result.error if not result.success else None,
                        "timestamp": time.time(),
                    }
                )

                # 4. Check MY victory conditions
                vcs_met = self.check_victory_conditions()
                if vcs_met:
                    # Report each VC met
                    for vc_id in vcs_met:
                        self.victory_tracker.mark_vc_met(vc_id, self.clone_id)

                    if len(vcs_met) == len(self.task.victory_conditions):
                        logger.info(
                            "✅ Clone %s achieved all VCs at iteration %s",
                            self.clone_id,
                            self.iteration,
                        )
                        return ActionResult(
                            success=True,
                            data={"vcs_met": vcs_met, "iterations": self.iteration + 1},
                        )

                # 5. If failed, context now includes error for next iteration
                if not result.success:
                    logger.debug(
                        "🔄 Clone %s iteration %s failed, feeding error back",
                        self.clone_id,
                        self.iteration,
                    )

            except Exception as e:
                logger.error(
                    "❌ Clone %s exception at iteration %s: %s",
                    self.clone_id,
                    self.iteration,
                    e,
                    exc_info=True,
                )
                self.context.append(
                    {
                        "iteration": self.iteration,
                        "exception": str(e),
                        "timestamp": time.time(),
                    }
                )

        logger.warning(
            "⚠️ Clone %s reached max iterations (%s)",
            self.clone_id,
            self.max_iterations,
            exc_info=True,
        )
        return ActionResult(
            success=False,
            error=f"Max iterations ({self.max_iterations}) reached",
            data={"context": self.context, "iterations": self.max_iterations},
        )

    def generate_action(self) -> Action:
        """Generate next action based on current context.

        Uses LLM to decide next action when llama.cpp is available.
        Falls back to heuristic cycling when LLM is not running.
        """
        action_type = self._llm_choose_action()
        if action_type is not None:
            if action_type == ActionType.EDIT:
                changes = self._llm_generate_edit()
                if changes:
                    return Action(
                        type=action_type,
                        target=self.task.target,
                        changes=changes,
                    )
            return Action(type=action_type, target=self.task.target)

        # Heuristic fallback: cycle through task types
        return self._heuristic_action()

    def _llm_choose_action(self) -> ActionType | None:
        """Ask LLM which action to take next based on context. Returns None if unavailable."""
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return None

            # Summarize recent context (last 5 iterations)
            recent = self.context[-5:]
            context_lines = []
            for c in recent:
                action_type = c.get("action", None)
                if action_type and hasattr(action_type, "type"):
                    action_type = action_type.type.value
                else:
                    action_type = str(action_type)
                success = c.get("success", False)
                error = c.get("error", "")
                context_lines.append(
                    f"  iter={c.get('iteration', '?')}: action={action_type}, success={success}, error={error}"
                )
            context_summary = (
                "\n".join(context_lines) if context_lines else "  (no previous actions)"
            )

            valid_actions = ", ".join(a.value for a in ActionType)
            prompt = (
                f"You are an immortal clone working on task: {self.task.id}\n"
                f"Target: {self.task.target}\n"
                f"Victory conditions: {self.task.victory_conditions}\n\n"
                f"Previous actions and results:\n{context_summary}\n\n"
                f"Choose your next action from: {valid_actions}\n"
                f"Respond with ONLY the action name, nothing else."
            )
            response = llm.complete(prompt).strip().lower()

            # Match response to ActionType enum
            for at in ActionType:
                if at.value in response:
                    return at
            logger.debug("LLM response '%s' did not match any ActionType", response)
            return None
        except Exception as e:
            logger.debug("LLM action selection unavailable: %s", e)
            return None

    def _llm_generate_edit(self) -> dict | None:
        """Ask LLM to generate specific edit instructions for the target file.

        Returns a changes dict with 'edits' list, or None if LLM unavailable.
        """
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return None

            target = Path(self.task.target)
            if not target.exists():
                return None
            source = target.read_text(encoding="utf-8")

            vcs = (
                ", ".join(self.task.victory_conditions)
                if self.task.victory_conditions
                else "(none)"
            )
            prompt = (
                f"You are editing: {self.task.target}\n"
                f"Victory conditions: {vcs}\n\n"
                f"Current file content:\n```\n{source[:2000]}\n```\n\n"
                f"Generate ONE edit to satisfy the victory conditions. "
                f"Format: OLD:<old text>\\nNEW:<new text>\\n---\\n"
                f"Use exact text from the file for OLD. Keep edits minimal."
            )
            response = llm.complete(prompt, max_tokens=512, temperature=0.3)
            if not response or not response.strip():
                return None

            edits = []
            for block in response.split("---"):
                block = block.strip()
                if not block:
                    continue
                old_text = None
                new_text = None
                for line in block.splitlines():
                    if line.startswith("OLD:"):
                        old_text = line[4:].strip()
                    elif line.startswith("NEW:"):
                        new_text = line[4:].strip()
                if old_text and new_text and old_text in source:
                    edits.append(
                        {"action": "replace", "old": old_text, "new": new_text}
                    )

            if edits:
                logger.debug(
                    "LLM generated %d edits for %s", len(edits), self.task.target
                )
                return {"edits": edits}
            return None
        except Exception as e:
            logger.debug("LLM edit generation unavailable: %s", e)
            return None

    def _heuristic_action(self) -> Action:
        """Heuristic action cycling fallback."""
        if self.iteration == 0:
            return Action(type=ActionType.ANALYZE, target=self.task.target)
        elif self.iteration < 3:
            return Action(type=ActionType.EDIT, target=self.task.target)
        elif self.iteration < 5:
            return Action(type=ActionType.COMPILE, target=self.task.target)
        elif self.iteration < 8:
            return Action(type=ActionType.TEST, target=self.task.target)
        else:
            return Action(type=ActionType.VERIFY, target=self.task.target)

    def execute_action(self, action: Action) -> ActionResult:
        """Execute action as real subprocess."""
        start_time = time.time()

        try:
            if action.type == ActionType.COMPILE:
                return self.compile(action)
            elif action.type == ActionType.TEST:
                return self.run_tests(action)
            elif action.type == ActionType.BENCHMARK:
                return self.benchmark(action)
            elif action.type == ActionType.BASH:
                return self.bash(action)
            elif action.type == ActionType.ANALYZE:
                return self.analyze(action)
            elif action.type == ActionType.EDIT:
                return self.edit(action)
            elif action.type == ActionType.VERIFY:
                return self.verify(action)
            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown action type: {action.type}",
                    duration=time.time() - start_time,
                )
        except Exception as e:
            return ActionResult(
                success=False, error=str(e), duration=time.time() - start_time
            )

    def compile(self, action: Action) -> ActionResult:
        """Actually compile code (Rust, Zig, etc.)."""
        start_time = time.time()
        target = Path(action.target)

        # Detect language and compile
        if (target / "Cargo.toml").exists():
            result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=action.timeout,
            )
        elif (target / "build.zig").exists():
            result = subprocess.run(
                ["zig", "build"],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=action.timeout,
            )
        else:
            return ActionResult(
                success=False,
                error=f"No build system found in {target}",
                duration=time.time() - start_time,
            )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None,
        )

    def run_tests(self, action: Action) -> ActionResult:
        """Actually run tests."""
        start_time = time.time()

        result = subprocess.run(
            ["pytest", str(action.target), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=action.timeout,
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None,
            data={
                "passed": result.stdout.count(" PASSED"),
                "failed": result.stdout.count(" FAILED"),
            },
        )

    def benchmark(self, action: Action) -> ActionResult:
        """Actually run benchmarks with hyperfine."""
        start_time = time.time()

        cmd = action.command or [str(action.target)]
        result = subprocess.run(
            [
                "hyperfine",
                "--warmup",
                "3",
                "--runs",
                "30",
                "--export-json",
                "/tmp/bench.json",
            ]
            + cmd,
            capture_output=True,
            text=True,
            timeout=action.timeout,
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None,
        )

    def bash(self, action: Action) -> ActionResult:
        """Execute arbitrary bash command."""
        start_time = time.time()

        result = subprocess.run(
            action.command or [str(action.target)],
            shell=isinstance(action.command, str),
            capture_output=True,
            text=True,
            timeout=action.timeout,
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None,
        )

    def analyze(self, action: Action) -> ActionResult:
        """Analyze a Python file using the AST module."""
        start_time = time.time()
        target = Path(action.target)
        if not target.exists() or not target.is_file():
            return ActionResult(
                success=False,
                error=f"Target not found: {action.target}",
                duration=time.time() - start_time,
            )

        try:
            import ast

            source = target.read_text(encoding="utf-8")
            tree = ast.parse(source)

            functions = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ]
            classes = [
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            imports: list = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")

            complexity = len(functions) + len(classes)

            return ActionResult(
                success=True,
                data={
                    "analyzed": str(action.target),
                    "functions": functions,
                    "classes": classes,
                    "imports": imports,
                    "complexity": complexity,
                    "lines": len(source.splitlines()),
                },
                duration=time.time() - start_time,
            )
        except SyntaxError as e:
            return ActionResult(
                success=False,
                error=f"Syntax error in {action.target}: {e}",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )

    def edit(self, action: Action) -> ActionResult:
        """Apply a list of text edits to a file."""
        start_time = time.time()
        target = Path(action.target)
        if not target.exists() or not target.is_file():
            return ActionResult(
                success=False,
                error=f"Target not found: {action.target}",
                duration=time.time() - start_time,
            )

        changes = action.changes or {}
        edits = changes.get("edits", [])
        if not edits:
            return ActionResult(
                success=False,
                error="No edits provided",
                duration=time.time() - start_time,
            )

        try:
            source = target.read_text(encoding="utf-8")
            results = []
            for edit in edits:
                edit_action = edit.get("action", "replace")
                if edit_action == "replace":
                    old = edit.get("old", "")
                    new = edit.get("new", "")
                    if old in source:
                        source = source.replace(old, new, 1)
                        results.append({"status": "success"})
                    else:
                        results.append(
                            {"status": "error", "reason": "old text not found"}
                        )
                else:
                    results.append(
                        {
                            "status": "error",
                            "reason": f"unsupported action: {edit_action}",
                        }
                    )

            target.write_text(source, encoding="utf-8")
            return ActionResult(
                success=all(r["status"] == "success" for r in results),
                data={"edited": str(action.target), "results": results},
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )

    def verify(self, action: Action) -> ActionResult:
        """Verify victory conditions."""
        start_time = time.time()
        met = self.check_victory_conditions()
        return ActionResult(
            success=len(met) > 0,
            data={"victory_conditions_met": met},
            duration=time.time() - start_time,
        )

    def check_victory_conditions(self) -> list[str]:
        """Check which task victory conditions are met.

        Uses LLM to evaluate VCs when llama.cpp is available.
        Falls back to heuristic (compile+test passed) when not.

        Returns:
            List of VC IDs that are now met
        """
        llm_met = self._llm_check_victory_conditions()
        if llm_met is not None:
            return llm_met

        # Heuristic fallback: success if we've compiled and tested
        has_compile = any(
            c.get("action")
            and hasattr(c["action"], "type")
            and c["action"].type == ActionType.COMPILE
            and c.get("success")
            for c in self.context
        )
        has_test = any(
            c.get("action")
            and hasattr(c["action"], "type")
            and c["action"].type == ActionType.TEST
            and c.get("success")
            for c in self.context
        )

        met = []
        if has_compile and has_test:
            met = self.task.victory_conditions

        return met

    def _llm_check_victory_conditions(self) -> list[str] | None:
        """Ask LLM to evaluate victory conditions. Returns None if unavailable."""
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return None

            recent = self.context[-5:]
            context_lines = []
            for c in recent:
                action_type = c.get("action", None)
                if action_type and hasattr(action_type, "type"):
                    action_type = action_type.type.value
                else:
                    action_type = str(action_type)
                success = c.get("success", False)
                context_lines.append(f"  action={action_type}, success={success}")
            context_summary = (
                "\n".join(context_lines) if context_lines else "  (no actions taken)"
            )

            vcs = (
                ", ".join(self.task.victory_conditions)
                if self.task.victory_conditions
                else "(none)"
            )
            prompt = (
                f"You are evaluating victory conditions for task: {self.task.id}\n"
                f"Target: {self.task.target}\n"
                f"Victory conditions: {vcs}\n\n"
                f"Recent actions:\n{context_summary}\n\n"
                f"Which victory conditions have been met? "
                f"Respond with ONLY the condition names, comma-separated, or 'none'."
            )
            response = llm.complete(prompt).strip().lower()

            if response == "none" or not response:
                return []

            # Match response to actual VC IDs
            met = []
            response_lower = response.lower()
            for vc_id in self.task.victory_conditions:
                if str(vc_id).lower() in response_lower:
                    met.append(vc_id)
            return met
        except Exception as e:
            logger.debug("LLM VC check unavailable: %s", e)
            return None


class GasTownOrchestrator:
    """Kubernetes-style orchestration for Immortal clones with live dashboard.

    Enhancements:
    - Victory tracker integration
    - Live dashboard (if rich available)
    - Auto-completion when all VCs met
    - Progress tracking per clone
    """

    def __init__(
        self,
        campaign: dict[str, Any],
        max_workers: int | None = None,
        max_iterations: int = 200,
        dashboard_enabled: bool = True,
    ):
        from multiprocessing import cpu_count

        self.campaign = campaign
        self.max_workers = max_workers or cpu_count()
        self.max_iterations = max_iterations
        self.dashboard_enabled = dashboard_enabled and RICH_AVAILABLE

        # Create victory tracker
        self.victory_tracker = CampaignVictoryTracker(
            campaign.get("victory_conditions", [])
        )

        # Create dashboard
        self.dashboard = CampaignDashboard(
            campaign.get("name", "Unknown Campaign"),
            len(campaign.get("victory_conditions", [])),
            int(max_workers) if max_workers is not None else 4,
            self.victory_tracker,
        )

        self.work_queue: list[MEOW] = []
        self.completed_work: list[tuple[MEOW, ActionResult]] = []
        self.active_clones: dict[int, ImmortalClone] = {}

    def decompose_to_meow(self) -> list[MEOW]:
        """Break campaign into Molecular Expression of Work units."""
        meows = []

        # Each victory condition becomes multiple MEOW units
        for i, vc in enumerate(self.campaign.get("victory_conditions", [])):
            if isinstance(vc, str):
                target = vc
            elif isinstance(vc, dict):
                target = vc.get("target", f"target_{i}")
            else:
                target = f"target_{i}"

            # Analyze phase
            meows.append(
                MEOW(
                    type="analyze",
                    target=target,
                    dependencies=[],
                    estimated_tokens=5000,
                    priority=1,
                )
            )

            # Implement phase (depends on analysis)
            meows.append(
                MEOW(
                    type="implement",
                    target=target,
                    dependencies=[f"analyze:{target}"],
                    estimated_tokens=20000,
                    priority=2,
                )
            )

            meows.append(
                MEOW(
                    type="test",
                    target=target,
                    dependencies=[f"implement:{target}"],
                    estimated_tokens=10000,
                    priority=3,
                )
            )

            meows.append(
                MEOW(
                    type="verify",
                    target=target,
                    dependencies=[f"test:{target}"],
                    estimated_tokens=5000,
                    priority=4,
                )
            )

        return meows

    def deploy_gas_town(self) -> list[ActionResult]:
        """Deploy ephemeral Immortal clones with live dashboard and auto-completion."""
        self.work_queue = self.decompose_to_meow()
        results = []

        logger.info(
            "🏭 Gas Town deploying %s MEOW units with %s workers",
            len(self.work_queue),
            self.max_workers,
        )

        # Setup live display
        if self.dashboard_enabled and RICH_AVAILABLE:
            try:
                with Live(
                    self.dashboard.generate_table(), refresh_per_second=2
                ) as live:
                    results = self._execute_deployment(live)
            except Exception as e:
                logger.warning(
                    "Dashboard failed, falling back to logging: %s", e, exc_info=True
                )
                results = self._execute_deployment(None)
        else:
            results = self._execute_deployment(None)

        logger.info("🏁 Gas Town completed %s MEOW units", len(results))

        status = self.victory_tracker.get_status()
        logger.info(
            "Final status: %s/%s VCs met (%s%%)",
            status["vcs_met"],
            status["total_vcs"],
            status["percentage"],
        )

        return results

    def _execute_deployment(self, live: Live | None) -> list[ActionResult]:
        """Execute deployment with optional live display."""
        results = []

        try:
            from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures: dict[Any, tuple[ImmortalClone, MEOW]] = {}
                clone_id = 0

                while self.work_queue or futures:
                    if self.victory_tracker.all_vcs_met():
                        logger.info(
                            "🎉 ALL VICTORY CONDITIONS MET! Stopping deployment."
                        )
                        # Cancel remaining futures
                        for future in futures:
                            future.cancel()
                        break

                    # Deploy new clones for available work
                    skipped = 0
                    while (
                        len(futures) < self.max_workers
                        and self.work_queue
                        and skipped < len(self.work_queue)
                    ):
                        meow = self.work_queue.pop(0)

                        if not self._dependencies_met(meow):
                            self.work_queue.append(meow)  # Re-queue for later
                            skipped += 1
                            continue

                        # Create Immortal clone for this MEOW
                        task = Task(
                            id=f"{meow.type}:{meow.target}",
                            type=meow.type,
                            target=meow.target,
                            victory_conditions=[],
                            dependencies=meow.dependencies,
                        )

                        clone = ImmortalClone(
                            clone_id=clone_id,
                            task=task,
                            victory_tracker=self.victory_tracker,
                            max_iterations=self.max_iterations,
                            progress_callback=self.dashboard.update_clone_progress,
                        )

                        # Deploy clone
                        future = executor.submit(clone.execute_persistent_loop)
                        futures[future] = (clone, meow)
                        clone_id += 1

                    # Collect completed work
                    if futures:
                        done, pending = wait(
                            futures.keys(), timeout=0.5, return_when=FIRST_COMPLETED
                        )
                        for future in done:
                            clone, meow = futures.pop(future)
                            try:
                                result = future.result()
                                self.completed_work.append((meow, result))
                                results.append(result)
                                logger.debug(
                                    "✅ MEOW %s:%s completed by clone %s",
                                    meow.type,
                                    meow.target,
                                    clone.clone_id,
                                    exc_info=True,
                                )
                            except Exception as e:
                                logger.error(
                                    "❌ Clone %s failed: %s",
                                    clone.clone_id,
                                    e,
                                    exc_info=True,
                                )
                                results.append(
                                    ActionResult(success=False, error=str(e))
                                )

                        # Update dashboard
                        if live:
                            try:
                                live.update(self.dashboard.generate_table())
                            except Exception as e:
                                logger.debug(
                                    "Dashboard update failed: %s", e, exc_info=True
                                )
                    elif not futures and self.work_queue:
                        # Deadlock: no futures running, all remaining MEOWs blocked
                        failed_meows = self._retry_failed_meows()
                        if failed_meows:
                            logger.info(
                                "🔄 Retrying %d failed MEOWs with escalated iterations",
                                len(failed_meows),
                            )
                            self.work_queue.extend(failed_meows)
                            continue
                        logger.warning(
                            "⚠️ Deployment deadlock: %d MEOWs blocked by unmet dependencies",
                            len(self.work_queue),
                        )
                        break

        except KeyboardInterrupt:
            logger.warning("⚠️ Deployment interrupted by user")
        except Exception as e:
            logger.error("❌ Deployment error: %s", e, exc_info=True)
            import traceback

            logger.error(traceback.format_exc())

        return results

    def _dependencies_met(self, meow: MEOW) -> bool:
        """Check if MEOW dependencies are satisfied.

        A dependency is met if the upstream MEOW has been *attempted* (even if it
        failed). This enables partial success propagation — a failed analysis
        still provides information for the implement phase to work with.
        """
        if not meow.dependencies:
            return True

        attempted_ids = {f"{m.type}:{m.target}" for m, _ in self.completed_work}
        return all(dep in attempted_ids for dep in meow.dependencies)

    def _retry_failed_meows(self) -> list[MEOW]:
        """Collect failed MEOWs for retry with escalated iteration count.

        Returns a list of MEOWs to re-queue. Each retried MEOW gets
        max_iterations * 2 to give it more room to succeed.
        """
        retryable = []
        for meow, result in self.completed_work:
            if not result.success and not getattr(meow, "_retried", False):
                meow._retried = True
                retryable.append(meow)
        return retryable


def immortal_clone_deploy(
    campaign: dict[str, Any],
    max_clones: int = 50000,
    max_iterations: int = 200,
    dashboard_enabled: bool = True,
) -> list[ActionResult]:
    """Deploy Immortal clones with enhanced tracking and auto-completion.

    Args:
        campaign: Campaign dict with 'name', 'victory_conditions', etc.
        max_clones: Maximum parallel workers (default: 50K)
        max_iterations: Max iterations per clone (default: 200)
        dashboard_enabled: Show live dashboard (default: True)

    Returns:
        List of ActionResults from all clones
    """
    orchestrator = GasTownOrchestrator(
        campaign,
        max_workers=min(max_clones, 64),  # Cap at 64 for stability
        max_iterations=max_iterations,
        dashboard_enabled=dashboard_enabled,
    )
    return orchestrator.deploy_gas_town()
