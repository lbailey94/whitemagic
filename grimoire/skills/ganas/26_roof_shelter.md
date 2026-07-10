---
name: wm-llama-cpp
description: "Local LLM management via llama.cpp — list, generate, chat, agent mode, model signing"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_roof
    tools: [model_hash, model_list, model_register, model_signing_status, model_verify, llama_cpp_models, llama_cpp_generate, llama_cpp_chat, llama_cpp_agent, shelter_create, shelter_execute, shelter_inspect, shelter_destroy]
    tags: [llama_cpp, llm, local, model, signing, shelter, sandbox, generate, chat]
---

# Shelter & Local LLMs

Manage local LLMs via llama.cpp, sign and verify models, and create sovereign sandbox environments for isolated execution.

## When to Use

- Listing available llama.cpp models
- Generating text with a local LLM
- Chatting with a local model in agent mode
- Registering and signing models for integrity
- Creating sovereign sandboxes for isolated execution
- Verifying model authenticity

## How to Invoke

```python
# List llama.cpp models
wm(thought="list available local models")
wm(route="gana_roof.llama_cpp_models", args={})

# Generate text
wm(route="gana_roof.llama_cpp_generate", args={"model": "qwen3-4b", "prompt": "..."})

# Chat in agent mode
wm(route="gana_roof.llama_cpp_agent", args={"model": "...", "messages": [...]})

# Register a model
wm(route="gana_roof.model_register", args={"name": "...", "path": "..."})

# Sign a model
wm(route="gana_roof.model_signing_status", args={"model": "..."})

# Create a sovereign sandbox
wm(route="gana_roof.shelter_create", args={"name": "..."})
```
