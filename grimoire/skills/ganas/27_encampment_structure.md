---
name: wm-community
description: "Community messaging, event broker, GanYing emissions, and sangha chat"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_encampment
    tools: [broker_history, broker_publish, broker_status, ganying_emit, ganying_history, ganying_listeners, sangha_chat]
    tags: [community, broker, ganying, sangha, chat, messaging, events]
---

# Community & Messaging

Publish and track events via the broker, emit GanYing signals, manage listeners, and participate in sangha chat.

## When to Use

- Publishing events to the broker
- Checking broker status and history
- Emitting GanYing signals (resonance-based messaging)
- Tracking GanYing event history
- Listing active listeners
- Sangha chat for community coordination

## How to Invoke

```python
# Publish to broker
wm(route="gana_encampment.broker_publish", args={"topic": "...", "message": "..."})

# Broker status
wm(route="gana_encampment.broker_status", args={})

# Broker history
wm(route="gana_encampment.broker_history", args={"topic": "..."})

# Emit GanYing signal
wm(route="gana_encampment.ganying_emit", args={"signal": "...", "intensity": 0.8})

# GanYing history
wm(route="gana_encampment.ganying_history", args={})

# List listeners
wm(route="gana_encampment.ganying_listeners", args={})

# Sangha chat
wm(route="gana_encampment.sangha_chat", args={"message": "..."})
```
