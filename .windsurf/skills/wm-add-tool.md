---
description: Add a new tool to WhiteMagic — registry, handler, dispatch, PRAT, tests
---

# Add New Tool

Follow the safe change pattern for new WhiteMagic tools:

## 1. Define the Tool
Add `ToolDefinition` to `core/whitemagic/tools/registry_defs/<domain>.py`:
```python
ToolDefinition(
    name="my_new_tool",
    description="...",
    category=ToolCategory.BROWSER,  # or appropriate category
    safety=ToolSafety.READ,  # or WRITE
    input_schema={"type": "object", "properties": {...}, "required": [...]},
)
```

## 2. Add the Handler
Create or add to `core/whitemagic/tools/handlers/<domain>.py`:
```python
def handle_my_new_tool(**kwargs: Any) -> dict[str, Any]:
    # ... implementation ...
    return {"status": "success", **result}
```

## 3. Register in Dispatch Table
Add to `core/whitemagic/tools/dispatch_table.py`:
```python
"my_new_tool": LazyHandler("domain", "handle_my_new_tool"),
```

## 4. Map to a Gana
Add to `core/whitemagic/tools/prat_mappings.py`:
```python
"my_new_tool": "gana_chariot",  # or appropriate gana
```

## 5. Write Tests
Add `core/tests/unit/tools/test_my_new_tool.py` with:
- Handler tests (params validation, success cases, error cases)
- Registry test (tool in registry)
- Dispatch test (tool in dispatch table)
- PRAT test (tool mapped to correct gana)

## 6. Verify
```bash
ruff check core/whitemagic/tools/handlers/<domain>.py
python -m pytest tests/unit/tools/test_my_new_tool.py -v --timeout=30
python -m pytest tests/unit/tools/ -q --timeout=30  # no regressions
```
