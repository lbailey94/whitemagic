# Chapter 23: Enduring Watch

**Gana**: OxGana (Chinese: 牛, Pinyin: Niú)
**Garden**: sangha
**Quadrant**: Northern (Black Tortoise)
**Element**: Water
**Phase**: Yin Peak
**I Ching Hexagram**: 52. 艮 Gèn (Keeping Still) - Steady watchfulness

---

## 🎯 Purpose

Chapter 23 maintains **enduring watch**—steady monitoring, reliable presence, patient vigilance. The Ox endures, watches, supports through all conditions. Like an ox plowing fields for seasons, sustained effort yields abundance.

Use this chapter when you need to:
- **Monitor systems** continuously over time
- **Maintain steady presence** during long work
- **Support community** (sangha) with reliability
- **Watch for anomalies** patiently
- **Endure through challenges** with resilience
- **Provide watchdog services** for critical systems
- **Sustain long-running processes** without fatigue

---

## 🔧 Primary Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `swarm.decompose` | Break complex objectives into sub-tasks | Campaign planning |
| `swarm.route` | Route sub-tasks to available workers | Task distribution |
| `swarm.plan` | Create execution plan for swarm | Strategy |
| `swarm.resolve` | Resolve conflicts between workers | Consensus |
| `swarm.vote` | Vote on proposals within swarm | Democratic decisions |
| `swarm.status` | Check swarm health and progress | Monitoring |
| `swarm.complete` | Mark swarm task as complete | Completion |
| `war_room.campaigns` | List active campaigns | Overview |
| `war_room.execute` | Execute a campaign phase | Action |
| `war_room.hierarchy` | Show command hierarchy | Organization |
| `war_room.phase` | Get/set current campaign phase | Phase tracking |
| `war_room.plan` | Create war room plan | Strategy |
| `war_room.status` | War room overall status | Health check |
| `worker.status` | Individual worker health and stats | Worker monitoring |

---

## 📋 Workflow

### 1. Continuous Health Monitoring

Watchful presence over extended periods:

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ContinuousHealthMonitor:
    """Enduring health monitoring - the ox's steady watch"""

    def __init__(self, check_interval: int = 300):
        self.check_interval = check_interval  # 5 minutes default
        self.start_time = datetime.now()
        self.checks_performed = 0
        self.issues_detected = 0
        self.running = False

    async def watch_forever(self):
        """Maintain watch indefinitely"""
        self.running = True
        logger.info(f"🐂 Ox watch beginning (interval: {self.check_interval}s)")

        try:
            while self.running:
                # Perform health check
                await self._perform_check()

                # Wait for next interval
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("🐂 Ox watch ending gracefully")
            raise

        finally:
            self._log_watch_summary()

    async def _perform_check(self):
        """Single health check iteration"""
        self.checks_performed += 1

        try:
            from whitemagic.tools import check_system_health

            # Check system health
            health = check_system_health(component="system")

            # Track status
            if health.get('status') != 'healthy':
                self.issues_detected += 1
                logger.warning(
                    f"⚠️ Ox detected issue (check #{self.checks_performed}): "
                    f"{health.get('status')}"
                )

                # Emit alert event
                from whitemagic.core.resonance import emit_event
                emit_event("health.degraded", {
                    "status": health.get('status'),
                    "check_number": self.checks_performed,
                    "issues": health.get('issues', [])
                })

            # Send heartbeat (silent)
            await self._send_heartbeat()

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.issues_detected += 1

    async def _send_heartbeat(self):
        """Send liveness signal"""
        from whitemagic.core.resonance import emit_event

        emit_event("monitor.heartbeat", {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "checks_performed": self.checks_performed,
            "issues_detected": self.issues_detected
        })

    def _log_watch_summary(self):
        """Log summary when watch ends"""
        duration = datetime.now() - self.start_time
        logger.info(
            f"🐂 Ox watch summary: {self.checks_performed} checks over "
            f"{duration.total_seconds():.0f}s, {self.issues_detected} issues"
        )

    def stop(self):
        """Stop the watch"""
        self.running = False

# Usage - runs indefinitely until stopped
monitor = ContinuousHealthMonitor(check_interval=300)
# await monitor.watch_forever()
```

### 2. Circuit Breaker Pattern

Fail fast, recover gracefully:

```python
from enum import Enum
from datetime import datetime, timedelta
from collections import deque

class CircuitState(Enum):
    CLOSED = "closed"      # Operating normally
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker for resilient operations"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.recent_calls = deque(maxlen=100)

    async def call(self, operation):
        """Execute operation through circuit breaker"""

        # Check if circuit should transition
        self._check_state_transition()

        if self.state == CircuitState.OPEN:
            raise Exception("Circuit breaker is OPEN - operation rejected")

        try:
            result = await operation()
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _check_state_transition(self):
        """Check if state should change"""

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker: OPEN → HALF_OPEN (testing recovery)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0

    def _on_success(self):
        """Record successful operation"""
        self.recent_calls.append(("success", datetime.now()))

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker: HALF_OPEN → CLOSED (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0

    def _on_failure(self):
        """Record failed operation"""
        self.recent_calls.append(("failure", datetime.now()))
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: HALF_OPEN → OPEN (recovery failed)")
            self.state = CircuitState.OPEN

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error("Circuit breaker: CLOSED → OPEN (too many failures)")
                self.state = CircuitState.OPEN

# Usage
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
# result = await breaker.call(risky_operation)
```

### 3. Long-Running Process Management

Sustain work over hours or days:

```python
import signal
from pathlib import Path
import json

class LongRunningProcess:
    """Manage long-duration processes with resilience"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = datetime.now()
        self.should_stop = False
        self.checkpoints_dir = Path.home() / ".whitemagic" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    async def run(self, work_func, checkpoint_interval: int = 1800):
        """Run long process with periodic checkpointing"""

        logger.info(f"🐂 Starting long-running process: {self.name}")
        iteration = 0
        last_checkpoint = datetime.now()

        try:
            while not self.should_stop:
                iteration += 1

                # Do work
                await work_func(iteration)

                # Checkpoint periodically (every 30 min)
                if (datetime.now() - last_checkpoint).total_seconds() >= checkpoint_interval:
                    await self._checkpoint(iteration)
                    last_checkpoint = datetime.now()

                # Brief pause between iterations
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Long-running process failed: {e}")
            await self._checkpoint(iteration, failed=True)
            raise

        finally:
            logger.info(
                f"🐂 Process {self.name} ending after {iteration} iterations, "
                f"duration: {(datetime.now() - self.start_time).total_seconds():.0f}s"
            )

    async def _checkpoint(self, iteration: int, failed: bool = False):
        """Save checkpoint"""
        checkpoint_file = self.checkpoints_dir / f"{self.name}_checkpoint.json"

        checkpoint_data = {
            "name": self.name,
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "failed": failed
        }

        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        logger.info(f"Checkpoint saved: iteration {iteration}")

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown signals"""
        logger.info(f"Received shutdown signal ({signum}), stopping gracefully...")
        self.should_stop = True
```

---

## 🔬 v22.2: Swarm Endurance Architecture

The OxGana provides the backbone for long-running swarm campaigns that span hours, days, or weeks. Where individual workers might falter under sustained load, the Ox ensures that the collective endures through careful pacing, health monitoring, and strategic rest cycles.

In a swarm campaign, endurance is not merely about keeping processes alive—it is about maintaining coherent progress toward a strategic objective while preserving the health of every participant. The Ox coordinates with the war room subsystem to translate high-level mission goals into sustained tactical execution.

Key war room tools that enable swarm endurance:

- `war_room.plan` — Defines campaign phases, milestones, and resource budgets.
- `war_room.execute` — Dispatches work to the swarm with Ox-monitored pacing.
- `war_room.status` — Provides real-time visibility into campaign health, worker vitality, and completion velocity.

A typical endurance campaign cycles between active execution, health checkpointing, and brief consolidation periods. The Ox moderates these transitions to prevent thermal or cognitive overload across the swarm.

```python
# Campaign monitoring with Ox endurance
from whitemagic.tools import war_room

async def monitor_campaign(campaign_id: str):
    """Ox-style watch over a long-running swarm campaign."""
    while True:
        status = war_room.status(campaign_id)

        # Check swarm vitality
        if status["worker_failure_rate"] > 0.15:
            await war_room.execute(
                campaign_id,
                action="reduce_load",
                target="swarm",
                reason="Endurance threshold breached"
            )

        # Checkpoint progress every 100 iterations
        if status["iterations"] % 100 == 0:
            war_room.plan(
                campaign_id,
                phase=f"checkpoint_{status['iterations']}",
                metadata=status["metrics"]
            )

        await asyncio.sleep(60)
```

---

## ⚠️ Common Pitfalls

Endurance work appears simple until it fails catastrophically. The Ox teaches that steady progress requires awareness of subtle failure modes.

| Pitfall | Symptom | Remedy |
|---------|---------|--------|
| **Premature optimization** | Tuning throughput before stability is proven. | Measure baseline health for 24h before optimizing. |
| **Monitoring blindness** | Alert fatigue causes operators to ignore warnings. | Use tiered alerts; reserve critical signals for action-required events. |
| **Swarm exhaustion** | Workers degrade gradually, output becomes erratic. | Enforce mandatory rest cycles via `war_room.execute` pause commands. |
| **Checkpoint amnesia** | Recovering from a crash loses hours of progress. | Write checkpoints to `WM_STATE_ROOT` after every milestone. |
| **False recovery** | Circuit breaker flaps between OPEN and HALF_OPEN. | Increase `recovery_timeout` and require `success_threshold >= 3`. |

Avoiding these pitfalls requires the same patience the Ox brings to plowing: observe, adjust, and never rush the field.

---

## 🔗 Integration with Other Ganas

The Ox does not endure in isolation. Its strength multiplies when paired with complementary Ganas across the quadrants.

### Ox ↔ Dipper (Chapter 22)

The Dipper governs strategy, stewardship, and resource allocation. The Ox translates Dipper directives into sustained execution. Where the Dipper decides *which* fields to plow and *when* the season turns, the Ox walks the furrows day after day. Use the Dipper's `war_room.plan` to set campaign boundaries, then rely on the Ox's monitoring loops to hold those boundaries against entropy.

### Ox ↔ Willow (Chapter 5)

The Willow (WeiGana) bends under load but does not break. When the Ox detects stress in a subsystem, the Willow provides the resilience pattern—load shedding, backpressure, and graceful degradation. In high-throughput campaigns, the Ox tracks health metrics while the Willow shapes the traffic. Together they ensure that endurance does not become rigidity.

### Ox ↔ Girl (Chapter 24)

The Girl (NuGana) nurtures workers, gardens, and relationships. Long-running swarms require more than mechanical uptime; they require care. The Girl's `manage_gardens` and community tools ensure that workers are rotated, rested, and mentally sustained. The Ox provides the heartbeat; the Girl provides the healing. Integrate both by scheduling Girl-managed rest cycles inside Ox-monitored campaigns.

---

## 📊 Metrics & Observability

What gets measured gets maintained. The Ox relies on concrete metrics to distinguish healthy endurance from silent degradation.

### Worker-Level Metrics

Track these fields via `worker.status` for every swarm participant:

- `uptime_seconds` — Total active time since last restart.
- `tasks_completed` — Counter for finished work units.
- `error_rate_5m` — Rolling window error percentage.
- `memory_pressure` — RSS vs. allocated limit.
- `last_heartbeat` — Timestamp of most recent liveness signal.

### Swarm-Level Metrics

Aggregate across the collective using `swarm.status`:

- `active_workers` / `total_workers` — Participation ratio.
- `mean_task_latency` — Average time from dispatch to completion.
- `checkpoint_age_seconds` — Time since last successful checkpoint.
- `campaign_progress_pct` — Milestone completion percentage.
- `alert_count_by_severity` — Histogram of emitted events.

Surface these metrics through the war room dashboard or stream them to external observability stacks. The Ox prefers slow, reliable trends over noisy instantaneous values. When in doubt, widen the aggregation window and trust the long slope.

---

## 🛠️ Troubleshooting

### Worker Heartbeat Loss

**Symptom**: `worker.status` reports `last_heartbeat` older than expected threshold.

**Diagnosis**: The worker may be blocked on a long-running task, crashed without cleanup, or network-partitioned from the swarm coordinator.

**Fix**:
1. Check `swarm.status` for the worker's `error_rate_5m` — if climbing, the worker is alive but struggling.
2. If `memory_pressure` is high, the worker needs task rebalancing — call `swarm.route` to redistribute.
3. If heartbeat is truly stale (> 3× check interval), declare the worker dead: `swarm.resolve` with a `worker_failed` conflict type.
4. The Girl (Ch 24) should then handle worker deregistration and replacement.

### Swarm Deadlock

**Symptom**: `swarm.status` shows `active_workers > 0` but `campaign_progress_pct` is not advancing.

**Diagnosis**: Workers may be waiting on each other (circular dependency) or all waiting on a single bottleneck resource.

**Fix**:
1. Call `war_room.hierarchy` to inspect the command tree — look for a single node blocking all children.
2. Use `swarm.vote` to break ties — if quorum is unreachable, the Dipper (Ch 22) can force a decision via `doctrine.force`.
3. If the deadlock is resource-based, the Mound (Ch 16) can release cached resources via `cache.flush`.

### Campaign Phase Regression

**Symptom**: `war_room.phase` reports a lower phase number than previously achieved.

**Diagnosis**: A phase was rolled back due to quality gate failure or external intervention.

**Fix**:
1. Check `war_room.status` for the `rollback_reason` field.
2. If quality gates failed, the Hairy Head (Ch 18) should have logged the specific assertion in `anomaly.history`.
3. Re-enter the phase with `war_room.execute` only after the root cause is addressed — the Ox does not skip phases.

---

## 🧭 Navigation

**Next**: [Chapter 24: Nurturing Profile](24_GIRL_NURTURE.md)
**Previous**: [Chapter 22: Well Stewardship](22_DIPPER_GOVERNANCE.md)
**Quadrant**: Northern (Winter/Water) - Position 2/7
