#!/usr/bin/env python3
"""Immortal Clone - Shadow clone with persistent execution loops.

Based on Geoff Huntley's insights on agent loops:
- Simple loops with error feedback
- Persistence until success (not one-shot)
- Real subprocess execution (not simulated)
- ~300 lines of code for the core loop
"""

import logging
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions a Ralph clone can execute."""
    ANALYZE = "analyze"
    EDIT = "edit"
    COMPILE = "compile"
    TEST = "test"
    BENCHMARK = "benchmark"
    BASH = "bash"
    VERIFY = "verify"


@dataclass
class Action:
    """An action to be executed by a Ralph clone."""
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
    """A task for a Ralph clone to execute."""
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


class ImmortalClone:
    """Shadow clone with persistent execution loops.

    Key features:
    - Real subprocess execution (not simulated)
    - Error feedback loop (persistent until success)
    - Context management (prevent context rot)
    - Victory condition verification
    """

    def __init__(
        self,
        clone_id: int,
        task: Task,
        max_iterations: int = 100,
        tools: list[str] | None = None
    ):
        self.clone_id = clone_id
        self.task = task
        self.max_iterations = max_iterations
        self.tools = tools or ['read', 'edit', 'bash', 'compile', 'test']
        self.context: list[dict[str, Any]] = []
        self.iteration = 0

    def execute_persistent_loop(self) -> ActionResult:
        """Persistent execution loop: persist until success.

        Core insight from Geoff Huntley:
        "It's 300 lines of code allocating array with some tools like
        read file, edit file, bash tool, and then you just loop."
        """
        logger.info(f"🥷 Immortal Clone {self.clone_id} starting loop for task {self.task.id}")

        for self.iteration in range(self.max_iterations):
            try:
                # 1. Generate action from current context
                action = self.generate_action()

                # 2. Execute action (real subprocess)
                result = self.execute_action(action)

                # 3. Feed result back into context (errors and all)
                # This is the persistent loop: failures become learning context
                self.context.append({
                    'iteration': self.iteration,
                    'action': action,
                    'result': result,
                    'success': result.success,
                    'error': result.error if not result.success else None,
                    'timestamp': time.time()
                })

                # 4. Check victory conditions
                if self.check_victory_conditions():
                    logger.info(f"✅ Immortal Clone {self.clone_id} achieved victory at iteration {self.iteration}")
                    return ActionResult(
                        success=True,
                        data={'context': self.context, 'iterations': self.iteration + 1}
                    )

                # 5. If failed, context now includes error for next iteration
                if not result.success:
                    logger.debug(f"🔄 Immortal Clone {self.clone_id} iteration {self.iteration} failed, feeding error back")

            except Exception as e:
                logger.error(f"❌ Immortal Clone {self.clone_id} exception at iteration {self.iteration}: {e}")
                self.context.append({
                    'iteration': self.iteration,
                    'exception': str(e),
                    'timestamp': time.time()
                })

        logger.warning(f"⚠️ Immortal Clone {self.clone_id} reached max iterations ({self.max_iterations})")
        return ActionResult(
            success=False,
            error=f"Max iterations ({self.max_iterations}) reached",
            data={'context': self.context, 'iterations': self.max_iterations}
        )

    def generate_action(self) -> Action:
        """Generate next action based on current context.

        In a full implementation, this would use an LLM to analyze context
        and decide the next action. For now, we use heuristics.
        """
        # Simple heuristic: cycle through task types
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
                    duration=time.time() - start_time
                )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )

    def compile(self, action: Action) -> ActionResult:
        """Actually compile code (Rust, Zig, etc.)."""
        start_time = time.time()
        target = Path(action.target)

        # Detect language and compile
        if (target / "Cargo.toml").exists():
            result = subprocess.run(
                ['cargo', 'build', '--release'],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=action.timeout
            )
        elif (target / "build.zig").exists():
            result = subprocess.run(
                ['zig', 'build'],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=action.timeout
            )
        else:
            return ActionResult(
                success=False,
                error=f"No build system found in {target}",
                duration=time.time() - start_time
            )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None
        )

    def run_tests(self, action: Action) -> ActionResult:
        """Actually run tests."""
        start_time = time.time()

        result = subprocess.run(
            ['pytest', str(action.target), '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=action.timeout
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None,
            data={
                'passed': result.stdout.count(' PASSED'),
                'failed': result.stdout.count(' FAILED')
            }
        )

    def benchmark(self, action: Action) -> ActionResult:
        """Actually run benchmarks with hyperfine."""
        start_time = time.time()

        cmd = action.command or [str(action.target)]
        result = subprocess.run(
            ['hyperfine', '--warmup', '3', '--runs', '30', '--export-json', '/tmp/bench.json'] + cmd,
            capture_output=True,
            text=True,
            timeout=action.timeout
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None
        )

    def bash(self, action: Action) -> ActionResult:
        """Execute arbitrary bash command."""
        start_time = time.time()

        result = subprocess.run(
            action.command or [str(action.target)],
            shell=isinstance(action.command, str),
            capture_output=True,
            text=True,
            timeout=action.timeout
        )

        return ActionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.time() - start_time,
            error=result.stderr if result.returncode != 0 else None
        )

    def analyze(self, action: Action) -> ActionResult:
        """Analyze code (placeholder for now)."""
        start_time = time.time()
        # In full implementation, would use tree-sitter, AST analysis, etc.
        return ActionResult(
            success=True,
            data={'analyzed': str(action.target)},
            duration=time.time() - start_time
        )

    def edit(self, action: Action) -> ActionResult:
        """Edit file (placeholder for now)."""
        start_time = time.time()
        # In full implementation, would apply actual edits
        return ActionResult(
            success=True,
            data={'edited': str(action.target)},
            duration=time.time() - start_time
        )

    def verify(self, action: Action) -> ActionResult:
        """Verify victory conditions."""
        start_time = time.time()
        met = self.check_victory_conditions()
        return ActionResult(
            success=met,
            data={'victory_conditions_met': met},
            duration=time.time() - start_time
        )

    def check_victory_conditions(self) -> bool:
        """Check if task victory conditions are met."""
        # In full implementation, would check actual VCs
        # For now, simple heuristic: success if we've compiled and tested
        has_compile = any(c.get('action', {}).type == ActionType.COMPILE and c.get('success')
                         for c in self.context if isinstance(c.get('action'), Action))
        has_test = any(c.get('action', {}).type == ActionType.TEST and c.get('success')
                      for c in self.context if isinstance(c.get('action'), Action))
        return has_compile and has_test


class GasTownOrchestrator:
    """Kubernetes-style orchestration for Immortal clones.

    Based on Steve Yegge's Gas Town concept:
    - MEOW (Molecular Expression of Work) decomposition
    - Ephemeral workers
    - Parallel execution at scale
    - Coordination is the bottleneck, not individual agents
    """

    def __init__(self, campaign: Any, max_workers: int | None = None):
        from multiprocessing import cpu_count
        self.campaign = campaign
        self.max_workers = max_workers or cpu_count()
        self.work_queue: list[MEOW] = []
        self.completed_work: list[tuple[MEOW, ActionResult]] = []
        self.active_clones: dict[int, ImmortalClone] = {}

    def decompose_to_meow(self) -> list[MEOW]:
        """Break campaign into Molecular Expression of Work units.

        Key insight: Tasks must be granular enough that ephemeral workers
        can pick up, execute, and hand off without context loss.
        """
        meows = []

        # Each victory condition becomes multiple MEOW units
        for i, vc in enumerate(self.campaign.get('victory_conditions', [])):
            target = vc.get('target', f'target_{i}')

            # Analyze phase
            meows.append(MEOW(
                type='analyze',
                target=target,
                dependencies=[],
                estimated_tokens=5000,
                priority=1
            ))

            # Implement phase (depends on analysis)
            meows.append(MEOW(
                type='implement',
                target=target,
                dependencies=[f'analyze:{target}'],
                estimated_tokens=20000,
                priority=2
            ))

            # Test phase (depends on implementation)
            meows.append(MEOW(
                type='test',
                target=target,
                dependencies=[f'implement:{target}'],
                estimated_tokens=10000,
                priority=3
            ))

            # Verify phase (depends on test)
            meows.append(MEOW(
                type='verify',
                target=target,
                dependencies=[f'test:{target}'],
                estimated_tokens=5000,
                priority=4
            ))

        return meows

    def deploy_gas_town(self) -> list[ActionResult]:
        """Deploy ephemeral Immortal clones to execute MEOW units.

        This is the Gas Town assembly line:
        - Workers are ephemeral (spawn, execute, collect)
        - Work is granular (MEOW-sized)
        - Coordination via work queue
        - Parallel execution at scale
        """
        self.work_queue = self.decompose_to_meow()
        results = []

        logger.info(f"🏭 Gas Town deploying {len(self.work_queue)} MEOW units with {self.max_workers} workers")

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Any, tuple[ImmortalClone, MEOW]] = {}
            clone_id = 0

            while self.work_queue or futures:
                # Deploy new clones for available work
                while len(futures) < self.max_workers and self.work_queue:
                    meow = self.work_queue.pop(0)

                    # Check dependencies
                    if not self._dependencies_met(meow):
                        self.work_queue.append(meow)  # Re-queue for later
                        continue

                    # Create Immortal clone for this MEOW
                    task = Task(
                        id=f"{meow.type}:{meow.target}",
                        type=meow.type,
                        target=meow.target,
                        victory_conditions=[],
                        dependencies=meow.dependencies
                    )
                    clone = ImmortalClone(clone_id=clone_id, task=task, max_iterations=50)

                    # Deploy clone
                    future = executor.submit(clone.execute_persistent_loop)
                    futures[future] = (clone, meow)
                    clone_id += 1

                # Collect completed work
                if futures:
                    done, pending = wait(futures.keys(), timeout=1.0, return_when=FIRST_COMPLETED)
                    for future in done:
                        clone, meow = futures.pop(future)
                        result = future.result()

                        self.completed_work.append((meow, result))
                        results.append(result)

                        logger.info(f"✅ MEOW {meow.type}:{meow.target} completed by clone {clone.clone_id}")

        logger.info(f"🏁 Gas Town completed {len(results)} MEOW units")
        return results

    def _dependencies_met(self, meow: MEOW) -> bool:
        """Check if MEOW dependencies are satisfied."""
        if not meow.dependencies:
            return True

        completed_ids = {f"{m.type}:{m.target}" for m, r in self.completed_work if r.success}
        return all(dep in completed_ids for dep in meow.dependencies)


def immortal_clone_deploy(campaign: dict[str, Any], max_clones: int = 50000) -> list[ActionResult]:
    """Deploy Immortal clones with persistent error feedback.

    Simple interface for deploying Immortal clones to a campaign.
    Uses Gas Town orchestration under the hood.
    """
    orchestrator = GasTownOrchestrator(campaign, max_workers=min(max_clones, 64))
    return orchestrator.deploy_gas_town()
