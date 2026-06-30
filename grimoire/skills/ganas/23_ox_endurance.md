---
name: wm-swarm
description: "Swarm orchestration, war room planning, worker management, and task decomposition"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_ox
    tools: [swarm_complete, swarm_decompose, swarm_plan, swarm_resolve, swarm_route, swarm_status, swarm_vote, worker_create, worker_assign, worker_status]
    tags: [swarm, war_room, worker, decompose, plan, resolve, vote, endurance]
---

# Swarm & Endurance

Orchestrate multi-agent swarms, plan in war rooms, decompose complex tasks, manage workers, and vote on solutions.

## When to Use

- Decomposing complex tasks into subtasks
- Planning multi-agent execution
- Routing subtasks to appropriate workers
- Voting on competing solutions
- Resolving conflicts between workers
- Tracking swarm execution status

## How to Invoke

```python
# Decompose a task
wm(route="gana_ox.swarm_decompose", args={"task": "...", "max_subtasks": 5})

# Plan execution
wm(route="gana_ox.swarm_plan", args={"task": "...", "workers": 3})

# Route subtask
wm(route="gana_ox.swarm_route", args={"subtask": "...", "capability": "..."})

# Vote on solution
wm(route="gana_ox.swarm_vote", args={"proposal": "...", "options": [...]})

# Resolve conflict
wm(route="gana_ox.swarm_resolve", args={"conflict_id": "..."})

# Swarm status
wm(route="gana_ox.swarm_status", args={})
```
