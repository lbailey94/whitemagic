---
name: wm-tasks
description: "Task distribution, pipeline management, and work routing"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_stomach
    tools: [pipeline, pipeline_create, pipeline_list, pipeline_status, task_distribute, task_route, task_status, task_complete]
    tags: [tasks, pipeline, distribution, routing, work, management]
---

# Tasks & Pipeline

Create and manage task pipelines, distribute work across agents, route tasks to appropriate handlers, and track completion.

## When to Use

- Creating a multi-step task pipeline
- Distributing work across multiple agents
- Routing tasks to the appropriate handler
- Tracking task completion status
- Managing work queues

## How to Invoke

```python
# Create a pipeline
wm(route="gana_stomach.pipeline_create", args={"name": "...", "steps": [...]})

# List pipelines
wm(route="gana_stomach.pipeline_list", args={})

# Pipeline status
wm(route="gana_stomach.pipeline_status", args={"pipeline_id": "..."})

# Distribute a task
wm(route="gana_stomach.task_distribute", args={"task": "..."})

# Route a task
wm(route="gana_stomach.task_route", args={"task": "...", "capability": "..."})

# Complete a task
wm(route="gana_stomach.task_complete", args={"task_id": "..."})
```
