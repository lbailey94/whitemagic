# CLI Architecture Documentation

**Version**: 21.0.0  
**Status**: Current (Target: Entry-point pattern migration)

---

## Current State

The CLI (`whitemagic/cli/cli_app.py`) uses import-time try/except blocks to handle optional dependencies:

```python
# Current pattern (15+ occurrences)
try:
    from whitemagic.cli.cli_local import local_cli
    HAS_LOCAL = True
except ImportError:
    HAS_LOCAL = False
```

This creates:
- Slow startup (all imports attempted at module load time)
- Unclear error messages when features are missing
- Complex conditional command registration
- Difficult to test (mocking required for each optional import)

---

## Target Architecture: Entry-Point Pattern

### 1. Lazy Command Groups

Use Click's lazy-loaded command groups instead of import-time checks:

```python
# Target pattern
@click.group()
def main():
    """WhiteMagic CLI"""
    pass

# Lazy-loaded subcommand group
@main.group(cls=LazyGroup, invoke_without_command=True)
def local():
    """Local ML inference commands"""
    # Import happens when command is invoked, not at module load
    from whitemagic.cli.cli_local import register_commands
    return register_commands()
```

### 2. Core vs Optional CLI

| Tier | Commands | Import Pattern |
|------|----------|----------------|
| Core | status, health, init, help | Direct import |
| Standard | memory, search, garden | Lazy import |
| Optional | local, tui, rust | Entry-point + graceful fallback |

### 3. Graceful Degradation

```python
# Target pattern for optional commands
@main.command()
def galaxy():
    """Launch Galaxy TUI (requires [tui] extra)"""
    try:
        from whitemagic.interfaces.tui import GalaxyTUI
    except ImportError as e:
        click.echo("ERROR: Galaxy TUI requires 'pip install whitemagic[tui]'")
        raise click.ClickException(str(e))
    
    app = GalaxyTUI()
    app.run()
```

---

## Migration Plan

### Phase 1: Document Current State ✅ (Current)
- [x] Create this architecture document
- [x] Map all 15+ optional imports

### Phase 2: Implement Lazy Groups
- [ ] Create `cli/lazy_groups.py` with LazyGroup implementation
- [ ] Migrate `gardens`, `prat`, `zodiac` commands to lazy groups
- [ ] Test startup time improvement

### Phase 3: Migrate Optional Commands
- [ ] Convert `local`, `rust`, `tui`, `sangha` to entry-point pattern
- [ ] Add unified error messages for missing extras
- [ ] Update command help text to indicate required extras

### Phase 4: Clean Up
- [ ] Remove HAS_* flag pattern
- [ ] Add CLI contract tests
- [ ] Document breaking changes (if any)

---

## Optional Import Inventory

| Feature | Module | HAS_* Flag | Tier | Migration Priority |
|---------|--------|------------|------|-------------------|
| Rich | rich | HAS_RICH | Core | Keep direct (core UX) |
| Voice | (various) | HAS_VOICE | Optional | Entry-point |
| Graph | (various) | HAS_GRAPH | Optional | Entry-point |
| Exec | (various) | HAS_EXEC | Optional | Entry-point |
| Core | memory.unified | HAS_CORE | Core | Keep direct |
| Plugins | plugins | HAS_PLUGINS | Optional | Entry-point |
| Extensions | various | HAS_EXTENSIONS | Standard | Lazy group |
| Reasoning | cli_reasoning | HAS_REASONING | Standard | Lazy group |
| Inference | infer_commands | HAS_INFERENCE | Standard | Lazy group |
| Hardware | hardware_commands | HAS_HARDWARE_CLI | Optional | Entry-point |
| Rust | cli_rust | HAS_RUST_CLI | Optional | Entry-point |
| Archaeology | cli_archaeology | HAS_ARCHAEOLOGY | Optional | Entry-point |
| Watcher | cli_watcher | HAS_WATCHER | Optional | Entry-point |
| Autonomous | cli_autonomous | HAS_AUTONOMOUS | Labs | Entry-point |
| Sangha | cli_sangha | HAS_SANGHA | Standard | Lazy group |
| Local | cli_local | HAS_LOCAL | Optional | Entry-point |
| Scratch | cli_scratchpad | HAS_SCRATCH | Labs | Entry-point |
| New Infra | various | HAS_NEW_INFRA | Standard | Lazy group |

---

## CLI Contract Tests

See `tests/verify/test_cli_contract.py` for validation.

### Required Contracts

1. **Core commands always available**: status, health, init, help work without optional deps
2. **Graceful degradation**: Optional commands show clear error when deps missing
3. **Fast startup**: CLI help loads in < 1 second
4. **Consistent errors**: All missing-dep errors follow same format

---

## Implementation Details

### LazyGroup Implementation

```python
# cli/lazy_groups.py
import click
from typing import Any, Callable

class LazyGroup(click.Group):
    """Click group that defers subcommand loading until invoked."""
    
    def __init__(self, loader: Callable[[], Any], **kwargs):
        self._loader = loader
        self._loaded = False
        super().__init__(**kwargs)
    
    def get_commands(self, ctx):
        if not self._loaded:
            self._loader()
            self._loaded = True
        return super().get_commands(ctx)
```

### Usage

```python
# cli_app.py
from .lazy_groups import LazyGroup

@main.group(cls=LazyGroup, invoke_without_command=True)
def rust():
    """Rust bridge commands (requires whitemagic-rust)"""
    from .cli_rust import register_rust_commands
    return register_rust_commands(main)
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Import-time try/except blocks | 15+ | 3-5 (core only) |
| CLI startup time | ~2-3s | <1s |
| Optional dep error clarity | Mixed | Unified format |
| Test complexity | High (many mocks) | Low (clean imports) |

---

## Changelog

- **2026-04-07**: Created architecture document (v21.0.0)
- **Next**: Implement LazyGroup for standard tier commands
