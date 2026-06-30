---
name: wm-prompts
description: "Prompt management, karma chain verification, and prompt rendering"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_net
    tools: [prompt_render, prompt_list, prompt_reload, karma_verify_chain]
    tags: [prompts, karma, chain, verification, rendering, templates]
---

# Prompts & Karma Chain

Manage prompt templates, verify karma chains for action integrity, and render prompts with context injection.

## When to Use

- Rendering a prompt template with context
- Listing available prompt templates
- Reloading prompt definitions after changes
- Verifying karma chain integrity for an action sequence
- Debugging prompt rendering issues

## How to Invoke

```python
# Render a prompt
wm(route="gana_net.prompt_render", args={"template": "...", "context": {...}})

# List available prompts
wm(route="gana_net.prompt_list", args={})

# Reload prompts
wm(route="gana_net.prompt_reload", args={})

# Verify karma chain
wm(route="gana_net.karma_verify_chain", args={"action_id": "..."})
```
