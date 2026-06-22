# PRAT Dispatch Pipeline Guide v1.0.0

**Purpose:** How to add a tool, register it, write a handler, add tests, and wire it into the dispatch table.

---

## 1. Architecture Overview

The PRAT dispatch pipeline is an **8-stage middleware chain** that routes 479 callable tools through 451 dispatch entries, backed by 28 Gana meta-tools.

### Key Numbers
| Metric | Count |
|--------|-------|
| Callable tools | 479 |
| Dispatch entries | 451 |
| Gana meta-tools | 28 |
| Handler modules | 73 |
| Registry definition files | 33 |
| Dispatch domain slices | 5 |

### The 8-Stage Pipeline
```
request → OTEL trace start → Zodiac phase awareness → Tool resolution → 
  Dharma gate (ethics check) → Handler dispatch → Karma ledger recording → 
  OTEL trace end → response envelope
```

### The 28 Gana Meta-Tools

Each Gana is one of the 28 lunar mansions (Chinese asterisms), organized into 4 quadrants:

| # | Gana | Garden | Quadrant |
|---|------|--------|----------|
| 1 | Horn (角) | courage | East (Spring) |
| 2 | Neck (亢) | stillness | East (Spring) |
| 3 | Root (氐) | healing | East (Spring) |
| 4 | Room (房) | sanctuary | East (Spring) |
| 5 | Heart (心) | love | East (Spring) |
| 6 | Tail (尾) | courage | East (Spring) |
| 7 | Winnowing Basket (箕) | wisdom | East (Spring) |
| 8 | Ghost (鬼) | grief | South (Summer) |
| 9 | Willow (柳) | humor | South (Summer) |
| 10 | Star (星) | voice | South (Summer) |
| 11 | Extended Net (張) | sangha | South (Summer) |
| 12 | Wings (翼) | beauty | South (Summer) |
| 13 | Chariot (軫) | adventure | South (Summer) |
| 14 | Abundance (豐) | joy | South (Summer) |
| 15 | Straddling Legs (奎) | awe | West (Autumn) |
| 16 | Mound (婁) | gratitude | West (Autumn) |
| 17 | Stomach (胃) | creation | West (Autumn) |
| 18 | Hairy Head (昴) | presence | West (Autumn) |
| 19 | Net (畢) | play | West (Autumn) |
| 20 | Turtle Beak (觜) | practice | West (Autumn) |
| 21 | Three Stars (參) | reverence | West (Autumn) |
| 22 | Dipper (斗) | dharma | North (Winter) |
| 23 | Ox (牛) | patience | North (Winter) |
| 24 | Girl (女) | connection | North (Winter) |
| 25 | Void (虚) | mystery | North (Winter) |
| 26 | Roof (危) | protection | North (Winter) |
| 27 | Encampment (室) | transformation | North (Winter) |
| 28 | Wall (壁) | truth | North (Winter) |

---

## 2. Adding a New Tool — Step by Step

### Step 1: Define in Registry

Create or edit a file in `core/whitemagic/tools/registry_defs/<domain>.py`:

```python
# registry_defs/my_domain.py
MY_TOOLS = {
    "my_tool": {
        "description": "Does something useful",
        "params": {"input": "str", "mode": "str (optional)"},
        "returns": "dict",
        "gana": "dharma",       # Which Gana does this belong to?
        "since_version": "22.3.0",
    }
}
```

### Step 2: Add Handler

Create or edit a file in `core/whitemagic/tools/handlers/<domain>.py`:

```python
# handlers/my_domain.py
from whitemagic.tools.envelope import success, error

def handle_my_tool(params: dict, request_id: str) -> dict:
    input_val = params.get("input")
    if not input_val:
        return error("my_tool", request_id, "invalid_params",
                     "Missing required param: input")
    result = do_something(input_val)
    return success("my_tool", request_id, result)
```

### Step 3: Register in Dispatch Table

Add to `core/whitemagic/tools/dispatch_table.py`:

```python
# In the appropriate DISPATCH_* dict or domain slice
"my_tool": LazyHandler("whitemagic.tools.handlers.my_domain", "handle_my_tool"),
```

### Step 4: Add Tests

Create or update `core/tests/unit/test_my_domain.py`:

```python
from whitemagic.tools.unified_api import call_tool

def test_my_tool_success():
    result = call_tool("my_tool", {"input": "test"})
    assert result["status"] == "success"
    assert result["tool"] == "my_tool"

def test_my_tool_missing_params():
    result = call_tool("my_tool", {})
    assert result["status"] == "error"
    assert result["error_code"] == "invalid_params"
```

### Step 5: Update Grimoire (if applicable)

If the tool maps to a Gana, update `grimoire/TRUTH_TABLE.md` and the corresponding chapter in `grimoire/`.

### Step 6: Verify

```bash
cd core
python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q
python scripts/check_doc_drift.py
```

---

## 3. The Stable JSON Envelope

Every tool returns this structure:

```python
# Success
{
    "status": "success",
    "tool": "tool_name",
    "request_id": "uuid",
    "data": { ... },
    "timestamp": "ISO-8601",
}

# Error
{
    "status": "error",
    "tool": "tool_name",
    "request_id": "uuid",
    "error_code": "tool_not_found" | "invalid_params" | "handler_error" | ...,
    "details": { ... },
    "retryable": bool,
    "timestamp": "ISO-8601",
}
```

Use `from whitemagic.tools.envelope import success, error` — never construct these manually.

---

## 4. LazyHandler Pattern

Most dispatch entries use `LazyHandler` to avoid importing all 73 handler modules at startup:

```python
LazyHandler("whitemagic.tools.handlers.memory", "handle_memory_write")
```

This resolves to importing `whitemagic.tools.handlers.memory` and calling `handle_memory_write` only when the tool is actually invoked.

---

## 5. Dispatch Domain Slices

The 451 dispatch entries are organized into 5 domain slice modules:

| Slice | File | Scope |
|-------|------|-------|
| Core | `dispatch_core.py` | Primitives, audit, write tools |
| Memory | `dispatch_memory.py` | Memory, galaxy, living-graph, OMS, hologram |
| Intelligence | `dispatch_intelligence.py` | Knowledge graph, embeddings, dream, cognition |
| Agents | `dispatch_agents.py` | Session, swarm, agent registry, mesh, voting, pipeline |
| Security | `dispatch_security.py` | Security, sandbox, shelter, dharma, watcher, forge |

Plus `_DISPATCH_OPERATIONAL` (138 entries) for inline operational tools.

---

## 6. Gana Meta-Tool Usage Examples

### Invoke a Gana tool
```python
from whitemagic.core.bridge.gana import gana_invoke
result = gana_invoke("dharma.get_debt")
# → {"status": "success", "tool": "gana_invoke", ...}
```

### List available Ganas
```python
call_tool("gana_list")
# → Returns all 28 Gana entries with descriptions
```

### Query PRAT status
```python
call_tool("prat_status")
# → {"status": "success", "data": {"ganas": 28, "fusions_active": 23, ...}}
```

---

## 7. Common Pitfalls

1. **Forgetting the envelope** — Always use `success()` / `error()`, never return raw dicts.
2. **Missing LazyHandler** — Adding a tool to the registry but forgetting the dispatch table entry causes `tool_not_found`.
3. **Handler module doesn't exist** — LazyHandler references a module that hasn't been created. Check `handlers/` first.
4. **Skipping Gana mapping** — If your tool belongs to a Gana, update `prat_mappings.py` and `grimoire/TRUTH_TABLE.md`.
5. **No tests** — Every tool needs at minimum: success path, missing params, invalid params.

---

## 8. Verification Commands

```bash
# Full test suite
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q

# Doc drift (must pass after any registry/dispatch change)
python scripts/check_doc_drift.py

# Dispatch table count check
python -c "from whitemagic.tools.dispatch_table import DISPATCH_TABLE; print(len(DISPATCH_TABLE))"
# → Should return 451
```
