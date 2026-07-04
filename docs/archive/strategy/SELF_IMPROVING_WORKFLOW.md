# Self-Improving Workflow: WhiteMagic Managing WhiteMagic

**Date:** 2026-05-29
**Status:** Operational specification — all components exist, need orchestration
**Audience:** Developers, AI operators, system architects

---

## 1. The Premise

WhiteMagic is a cognitive operating system with:
- 479 callable tools across 451 dispatch entries + 28 Gana meta-tools
- 12 Zodiac cores with distinct personalities and capabilities
- Sangha multi-agent coordination (chat, locks, patterns, ethics, sessions)
- ConductorOrchestrator for autonomous task management
- Gan Ying event bus for resonant inter-module communication
- Pattern Federation for cross-session learning
- Community Dharma for collective ethical consensus
- Brier scoring for prescience tracking

**The system can manage itself.** Not as a gimmick — as a genuine operational pattern where WhiteMagic tools improve, audit, and extend WhiteMagic code.

This document specifies how to operationalize this.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Self-Improving Loop                        │
├─────────────────────────────────────────────────────────────┤
│  Sangha Chat          │  Coordination channel for all agents   │
│  Conductor            │  Task orchestrator and scheduler      │
│  Zodiac Cores         │  Specialized workers (Virgo, Libra...)│
│  Pattern Federation   │  Learned solutions → reusable assets  │
│  Community Dharma     │  Ethical guardrails on changes        │
│  Gan Ying Bus         │  Event-driven coordination            │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                    WhiteMagic Codebase                        │
│  (919 Python modules, 332 packages, tests, docs, polyglot)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Operational Patterns

### Pattern 1: Sangha-as-Project-Manager

**Use case:** Any significant codebase task (refactor, feature, bug fix) becomes a Sangha chat session with structured task tracking.

```bash
wm sangha_chat_send \
  --sender_id "Conductor" \
  --channel "polyglot_fix" \
  --content "Sprint: Fix all polyglot binaries.\n\nTasks:\n1) Fix Koka effects syntax (src/effects/prat.kk)\n2) Verify Rust bridge compilation\n3) Test Zig library loading\n4) Compile Mojo encoder\n\nAssigning: Virgo (1), Capricorn (2), Aries (3), Taurus (4)" \
  --priority "high"
```

**Why this works:**
- Persistent chat log survives IDE restarts
- Multiple agents (human + AI) can coordinate
- Task list is queryable and status-tracked
- Gan Ying events notify when tasks complete

### Pattern 2: Conductor-Driven Iteration

**Use case:** The ConductorOrchestrator manages multi-step improvements autonomously.

```python
from whitemagic.orchestration.conductor import ConductorOrchestrator
from whitemagic.gardens.sangha.chat import get_chat

conductor = ConductorOrchestrator()
chat = get_chat()

def completion_check() -> bool:
    """Sprint is done when all tasks are closed."""
    return len(chat.list_tasks(status="open")) == 0

conductor.run_iterative(
    objective="Fix all polyglot compilation issues and verify with tests",
    completion_check=completion_check,
    max_iterations=20,
    token_budget=500000,
)
```

**How it works:**
1. Conductor analyzes the objective
2. Spawns AsyncThoughtCloneArmy for parallel exploration
3. Each clone proposes a sub-task
4. Sub-tasks are posted to Sangha chat as structured tasks
5. Zodiac cores pick up tasks based on capability match
6. Results are validated against test suite
7. Pattern Federation stores successful approaches
8. Community Dharma assesses whether changes are safe

### Pattern 3: Pattern Federation for Code Solutions

**Use case:** When a fix works, it becomes a reusable pattern for future sessions.

```python
from whitemagic.gardens.sangha.pattern_federation import get_federation

pf = get_federation()

# After fixing GanYingMixin
pf.contribute_pattern(
    session_id="cascade_2026-05-29",
    name="GanYingMixin restoration after consolidation",
    problem=(
        "Milestone 4.3 Singleton Reduction removed integration_helpers.py "
        "and replaced GanYingMixin with empty deprecation stubs. "
        "SanghaGarden.__init__ called self.emit() which crashed because "
        "the mixin no longer wired the real GanYingBus."
    ),
    solution=(
        "1. Restore GanYingMixin to delegate emit() and listen() to the "
        "real GanYingBus from whitemagic.core.resonance.get_bus().\n"
        "2. Keep deprecation warnings to signal future migration.\n"
        "3. Add explicit GanYingMixin.__init__(self) call in "
        "SanghaGarden.__init__ because BaseGarden.__init__ does not "
        "call super() for mixin initialization."
    ),
    confidence=0.95,
    tags=["consolidation", "backward-compatibility", "event-bus", "mixin"],
)
```

**Future sessions query before reinventing:**

```python
patterns = pf.search_patterns(
    query="gan ying mixin broken after consolidation",
    min_confidence=0.8
)
# Returns the exact solution above
```

**Why this matters:** WhiteMagic currently has **zero TODO comments** but had 41 structural stubs. Pattern Federation is the antidote — every recovered stub becomes a warning pattern.

### Pattern 4: Community Dharma for Code Ethics

**Use case:** Establish norms for what constitutes safe vs. dangerous changes.

```python
from whitemagic.gardens.sangha.community_dharma import get_community_dharma

cd = get_community_dharma()

# Record the lesson from Milestone 4.3
cd.contribute_assessment(
    session_id="cascade",
    action="Remove deprecated module without updating all inheritors",
    assessment="violation",
    score=0.2,
    reasoning=(
        "Milestone 4.3 broke SanghaGarden, multiple gardens, and any "
        "downstream code using GanYingMixin. Deprecation warnings are "
        "insufficient when emit() is a runtime dependency. Rule: "
        "before removing any module, grep for all inheritors and callers."
    ),
)
```

**Future refactor assessment:**

```python
result = cd.assess_with_community(
    session_id="cascade",
    action="Remove whitemagic.core.resonance.gan_ying shim module",
    context={"affected_modules": ["sangha", "dharma", "zodiac"]},
)
# Returns: "Avoid - Community considers this problematic"
```

**The community consensus becomes a living, queryable code of conduct.**

### Pattern 5: Zodiac Core Specialization

**Use case:** Assign specific improvement tasks to cores best suited for them.

| Task | Best Core | Why |
|------|-----------|-----|
| Code review, hygiene audit | **Virgo** | Mutable earth, detail-oriented, perfectionist |
| Ethical assessment of change | **Libra** | Cardinal air, balance, governance |
| Threat modeling, security | **Scorpio** | Fixed water, depth, investigation |
| Rapid prototyping, spikes | **Aries** | Cardinal fire, initiative, speed |
| Architecture design | **Capricorn** | Cardinal earth, systems, structure |
| Creative solutions, novel approaches | **Aquarius** | Fixed air, innovation, disruption |
| Documentation, clarity | **Gemini** | Mutable air, communication, multi-path |
| Emotional safety, harm review | **Cancer** | Cardinal water, protection, care |

**Example workflow:**

```python
from whitemagic.zodiac import get_core

virgo = get_core("virgo")
libra = get_core("libra")

# Virgo reviews the fix
review = virgo.process({
    "task": "code_review",
    "file": "core/whitemagic/core/resonance/integration_helpers.py",
    "focus": ["backward_compatibility", "type_safety", "test_coverage"]
})

# Libra assesses ethical impact
ethics = libra.process({
    "task": "ethical_assessment",
    "change": "Restore deprecated mixin functionality",
    "stakeholders": ["downstream_gardens", "future_maintainers"]
})
```

### Pattern 6: Prescience-Driven Prioritization

**Use case:** Use the prescience track record to decide what to build next.

```python
from whitemagic.forecasting.brier import brier_skill_score
from whitemagic.temporal_db import query_claims

# Query: what predicted trends are becoming urgent?
urgent = query_claims(
    domain="economy",
    validation_status="pending",
    predicted_window_months=6,
)

# If "Agent identity coherence" is predicted to validate soon,
# prioritize building identity verification into Sangha
```

**This closes the loop:** WhiteMagic doesn't just manage code. It uses its own foresight to **predict what code will be needed**.

---

## 4. Daily Operational Flow

### Morning: Standup via Sangha Chat

```
[cascade] 09:00 #general
"Daily standup. Current open tasks: 3. Test baseline: 2282 passed. 
Priority: Fix Koka effects syntax. Virgo, you're on code review. 
Aries, spike the Mojo compilation path."

[virgo] 09:05 #general
"Acknowledged. Reviewing src/effects/prat.kk. Preliminary finding: 
'context' keyword is Koka 2.x syntax, incompatible with Koka 3.2.2. 
Recommend mapping to Koka 3 effect handlers."

[aries] 09:07 #general
"Spike complete. Mojo compiler available at /usr/local/bin/mojo. 
Build script needs update for Mojo 0.26.1. Ready to proceed."
```

### Midday: Pattern Contribution

When a fix is verified:
1. Run full test suite (2,282 tests)
2. If green, contribute pattern to federation
3. Community Dharma assesses if change was safe
4. Update prescience timeline if relevant

### Evening: Handoff

```python
from whitemagic.gardens.sangha.session_handoff import get_handoff

handoff = get_handoff()
handoff.end_session(
    session_id="cascade_2026-05-29",
    context_summary="Fixed GanYingMixin. 2,282 tests passing. 3 new patterns federated. 1 ethical guideline established.",
    next_steps=[
        "Fix Koka effects syntax",
        "Compile Rust bridge",
        "Build Mojo encoder",
    ],
    files_modified=[
        "core/whitemagic/core/resonance/integration_helpers.py",
        "core/whitemagic/gardens/sangha/__init__.py",
    ],
)
```

**The next session auto-resumes with full context.**

---

## 5. Integration with Human Oversight

Self-improving does **not** mean autonomous deployment. The human remains the sovereign.

| Automation Level | What the system does | What the human does |
|------------------|----------------------|---------------------|
| **Level 1: Assisted** | Suggests fixes, runs tests, reports results | Reviews and approves every change |
| **Level 2: Semi-Autonomous** | Fixes obvious issues (type errors, import fixes), runs tests | Reviews architectural changes, ethical assessments |
| **Level 3: Autonomous (safe)** | Auto-fixes Level 1 issues, contributes patterns, posts to chat | Monitors dashboard, intervenes on flagged items |
| **Level 4: Fully Autonomous** | *(Not recommended)* | *(Not recommended)* |

**Current recommendation:** Operate at **Level 2** for the codebase. Let Virgo handle code review, Libra handle ethics, and the human approve anything that touches:
- Payment endpoints
- Ethical consensus thresholds
- Public API contracts
- Database schemas

---

## 6. Metrics and Dashboard

### System Health

```python
from whitemagic.gardens.sangha import get_sangha_garden
from whitemagic.forecasting.brier import brier_index

health = {
    "tests": {"passed": 2282, "skipped": 61, "failed": 0},
    "patterns_federated": len(get_federation()._load_all_patterns()),
    "ethical_guidelines": len(get_community_dharma().get_community_guidelines()),
    "prescience_brier_index": brier_index(current_brier_score),
    "sangha_members_active": len(get_sangha_garden().community_members),
    "gan_ying_events_today": len([e for e in get_bus()._history if e.timestamp.date() == today]),
}
```

### Improvement Velocity

- Patterns contributed per session
- Tests added per fix
- Time from bug detection to pattern federation
- Community consensus score trends

---

## 7. Risks and Safeguards

| Risk | Safeguard |
|------|-----------|
| Runaway changes | Community Dharma threshold: ≥ 3 votes, ≥ 0.8 score for auto-approval |
| Pattern pollution | Minimum confidence 0.7 for federation. Virgo reviews all contributions. |
| Test regression | Full suite (2,282 tests) is gate. No exceptions. |
| Ethical drift | Libra assessment required for any governance module change. |
| Session loss | SessionHandoff auto-persistence. Auto-resume on next boot. |

---

## 8. Getting Started (Today)

**Step 1:** Start a Sangha chat for today's session.

```bash
wm sangha_chat_send \
  --sender_id "cascade" \
  --channel "self_improve_$(date +%Y-%m-%d)" \
  --content "Session goal: Fix polyglot binaries. Conductor running iterative mode." \
  --priority "high"
```

**Step 2:** Run Conductor with completion check.

```python
from whitemagic.orchestration.conductor import ConductorOrchestrator

conductor = ConductorOrchestrator()
conductor.run_iterative(
    objective="Fix Koka effects syntax, compile Rust bridge, verify Zig lib, build Mojo encoder",
    completion_check=lambda: all([
        koka_compiles(),
        rust_imports(),
        zig_loads(),
        mojo_binary_exists(),
    ]),
    max_iterations=20,
)
```

**Step 3:** When done, contribute the pattern.

```python
get_federation().contribute_pattern(...)
get_community_dharma().contribute_assessment(...)
get_handoff().end_session(...)
```

---

## 9. The Vision

WhiteMagic managing WhiteMagic is not a parlor trick. It is a **demonstration of the system's own claims:**

- **Sangha** proves multi-agent coordination works.
- **Pattern Federation** proves cross-session learning works.
- **Community Dharma** proves ethical self-governance works.
- **Conductor** proves autonomous orchestration works.
- **Prescience** proves the system can predict its own needs.

When an external agent evaluates WhiteMagic and sees that **WhiteMagic uses itself to improve itself**, the credibility of the entire ecosystem increases. This is not marketing. This is **operational proof**.

---

**Next step:** Start today's self-improving session using the Step 1–3 sequence above.
