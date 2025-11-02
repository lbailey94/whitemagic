# Core Refactoring Implementation Plan

**File**: `whitemagic/core.py`  
**Source**: `memory_manager.py` (1,601 lines)  
**Strategy**: Incremental refactoring with continuous testing

---

## Refactoring Chunks

### Chunk 1: Constructor & Metadata (Priority: CRITICAL)

**Lines**: 30-180  
**Methods**:
- `__init__()`
- `_load_metadata()`
- `_save_metadata()`
- `_normalise_index_entry()`
- `_directory_for_type()`
- `_prune_missing_files()`
- `_touch_entry()`

**Changes**:
- Import constants from `whitemagic.constants`
- Use `Path` types consistently
- Add type hints everywhere
- Validate with Pydantic where appropriate

**Test**: Can initialize MemoryManager, load/save metadata

---

### Chunk 2: Memory CRUD (Priority: HIGH)

**Lines**: 187-326  
**Methods**:
- `create_memory()`
- `read_recent_memories()`
- `search_memories()`

**Changes**:
- Return `Memory` models instead of dicts
- Use `MemoryCreate` for input validation
- Use `MemorySearchQuery` for search
- Raise exceptions instead of error dicts

**Test**: Can create, read, and search memories

---

### Chunk 3: Context Generation (Priority: HIGH)

**Lines**: 331-393  
**Methods**:
- `generate_context_summary()`
- `_format_body_for_context()`

**Changes**:
- Use utils for markdown cleaning
- Return `ContextResponse` model
- Validate tier with `ContextRequest`

**Test**: Can generate context for all tiers

---

### Chunk 4: Consolidation (Priority: MEDIUM)

**Lines**: 397-533  
**Methods**:
- `consolidate_short_term()`

**Changes**:
- Use `ConsolidateRequest` for input
- Return `ConsolidateResponse`
- Use utils for date calculations

**Test**: Consolidation works (dry-run and actual)

---

### Chunk 5: Tag & Update Operations (Priority: HIGH)

**Lines**: 538-804  
**Methods**:
- `_normalize_tags()`
- `delete_memory()`
- `update_memory()`
- `restore_memory()`
- `normalize_legacy_tags()`

**Changes**:
- Move `_normalize_tags()` to use utils.normalize_tags()
- Use `MemoryUpdate` for updates
- Use `RestoreRequest`, `NormalizeTagsRequest`
- Raise exceptions for errors

**Test**: All v2.0.1 operations work

---

### Chunk 6: Listing & Stats (Priority: MEDIUM)

**Lines**: 809-876  
**Methods**:
- `list_all_memories()`
- `list_all_tags()`

**Changes**:
- Return typed responses
- Use `TagsResponse` model

**Test**: Listing and stats accurate

---

### Chunk 7: Internal Helpers (Priority: LOW)

**Lines**: 880-960  
**Methods**:
- `_entries()`
- `_read_memory_file()`
- `_split_frontmatter()`
- `_parse_frontmatter()`
- `_create_frontmatter()`
- `_slugify()`
- `_summarise_text()`
- `_truncate_text()`
- `_clean_markdown()`
- `_create_preview()`
- `_serialise_for_listing()`
- `_unique_archive_path()`

**Changes**:
- Many moved to `utils.py`
- Simplify remaining methods
- Add type hints

**Test**: All helpers work correctly

---

## Implementation Order

1. ✅ Create utils.py with all helper functions
2. 🚧 Chunk 1 (Constructor & Metadata) - **START HERE**
3. ⏳ Test Chunk 1
4. ⏳ Chunk 2 (CRUD)
5. ⏳ Test Chunk 2  
6. ⏳ Chunk 5 (Updates - needed for v2.0.1 tests)
7. ⏳ Test all v2.0.1 functionality
8. ⏳ Chunk 3 (Context)
9. ⏳ Chunk 4 (Consolidation)
10. ⏳ Chunk 6 (Listing)
11. ⏳ Chunk 7 (Cleanup)
12. ⏳ Final test suite

---

## Code Style Guidelines

### Imports
```python
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .constants import *
from .exceptions import *
from .models import *
from .utils import *
```

### Type Hints
- All parameters typed
- All return types specified
- Use `Optional[T]` for nullable
- Use `List[T]`, `Dict[K, V]` for collections

### Error Handling
```python
# Old style (BAD)
return {"success": False, "error": "Not found"}

# New style (GOOD)
raise MemoryNotFoundError(filename)
```

### Models
```python
# Old style (BAD)
def create_memory(title: str, content: str, ...) -> Path:
    ...

# New style (GOOD)
def create_memory(data: MemoryCreate) -> Memory:
    ...
```

---

## Testing Strategy

### After Each Chunk
1. Import in test file
2. Run subset of tests
3. Fix any failures
4. Continue to next chunk

### After Complete Refactoring
1. Run full test suite (18 tests)
2. All must pass
3. Add new tests for edge cases

### Regression Prevention
- Keep `memory_manager.py` as reference
- Compare outputs between old and new
- Ensure identical behavior

---

## Backward Compatibility Plan

### Option 1: Wrapper (Recommended)
```python
# memory_manager.py becomes:
from whitemagic import MemoryManager
# ... rest of CLI code ...
```

### Option 2: Proxy
```python
# memory_manager.py keeps:
class MemoryManager:
    def __init__(self, *args, **kwargs):
        from whitemagic import MemoryManager as CoreManager
        self._core = CoreManager(*args, **kwargs)
    
    def create_memory(self, *args, **kwargs):
        return self._core.create_memory(*args, **kwargs)
```

**Decision**: Use Option 1 (simpler, cleaner)

---

## Success Criteria

- [ ] All 18 existing tests pass
- [ ] No performance regression (benchmark key operations)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (no new warnings)
- [ ] Documentation updated
- [ ] CLI still works identically

---

**Status**: Ready to begin Chunk 1  
**Next**: Implement constructor & metadata management
