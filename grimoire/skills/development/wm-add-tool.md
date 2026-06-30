---
name: wm-add-tool
description: "Add a new tool to WhiteMagic — registry, handler, dispatch, PRAT, tests"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [development, tool, registry, handler, dispatch, prat, tests]
---

# Add New Tool

Follow the safe change pattern for new WhiteMagic tools. Every tool needs 5 wiring points + tests.

## Steps

### 1. Define the Tool
Add `ToolDefinition` to `core/whitemagic/tools/registry_defs/<domain>.py`:
```python
ToolDefinition(
    name="my_new_tool",
    description="...",
    category=ToolCategory.BROWSER,
    safety=ToolSafety.READ,
    input_schema={"type": "object", "properties": {...}, "required": [...]},
)
```

### 2. Add the Handler
Create or add to `core/whitemagic/tools/handlers/<domain>.py`:
```python
def handle_my_new_tool(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", **result}
```

### 3. Register in Dispatch Table
Add to `core/whitemagic/tools/dispatch_table.py`:
```python
"my_new_tool": LazyHandler("domain", "handle_my_new_tool"),
```

### 4. Map to a Gana
Add to `core/whitemagic/tools/prat_mappings.py`:
```python
"my_new_tool": "gana_chariot",
```

### 5. Add NLU Routing (if using wm meta-tool)
Add patterns to `core/whitemagic/tools/handlers/meta_tool.py`:
```python
if any(p in intent_lower for p in ["my new tool", "do new thing"]):
    return _dispatch("my_new_tool", args)
```

### 6. Write Tests
Create `core/tests/unit/tools/test_my_new_tool.py`:
- Handler tests (params validation, success cases, error cases)
- Registry test (tool in registry)
- Dispatch test (tool in dispatch table)
- PRAT test (tool mapped to correct gana)

### 7. Verify
```bash
ruff check core/whitemagic/tools/handlers/<domain>.py
python -m pytest tests/unit/tools/test_my_new_tool.py -v --timeout=30
python -m pytest tests/unit/tools/ -q --timeout=30  # no regressions
```
