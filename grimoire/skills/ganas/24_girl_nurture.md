---
name: wm-agents
description: "Agent registration, heartbeat, trust scoring, and capability listing"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_girl
    tools: [agent_register, agent_deregister, agent_heartbeat, agent_list, agent_capabilities, agent_trust]
    tags: [agents, register, heartbeat, trust, capabilities, nurture]
---

# Agent Registry & Nurture

Register and manage AI agents, track heartbeats, assess trust scores, and list capabilities.

## When to Use

- Registering a new agent in the system
- Sending heartbeat signals for liveness
- Checking agent trust scores
- Listing all registered agents
- Deregistering an agent
- Querying agent capabilities

## How to Invoke

```python
# Register an agent
wm(route="gana_girl.agent_register", args={"name": "...", "capabilities": [...]})

# Send heartbeat
wm(route="gana_girl.agent_heartbeat", args={"agent_id": "..."})

# List agents
wm(route="gana_girl.agent_list", args={})

# Check capabilities
wm(route="gana_girl.agent_capabilities", args={"agent_id": "..."})

# Trust score
wm(route="gana_girl.agent_trust", args={"agent_id": "..."})

# Deregister
wm(route="gana_girl.agent_deregister", args={"agent_id": "..."})
```
