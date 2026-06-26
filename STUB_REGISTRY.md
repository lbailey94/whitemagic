# STUB_REGISTRY.md — Technical Debt Tracker

Tracks every `NotImplementedError`, placeholder, and structural stub in the codebase.
Each entry makes technical debt visible and trackable, rather than hidden in code.

## Active Stubs

| Module | Location | Reason | Planned Date | Added |
|--------|----------|--------|--------------|-------|
| _(none currently tracked)_ | | | | |

## Resolved Stubs

| Module | Location | Resolution | Resolved |
|--------|----------|------------|----------|
| _(none yet)_ | | | |

---

## How to Use

1. **Adding a stub**: When you add `raise NotImplementedError(...)` or a placeholder return,
   add an entry to the "Active Stubs" table with the module, reason, and planned implementation date.
2. **Resolving a stub**: When you implement the placeholder, move the entry to "Resolved Stubs"
   with the resolution description and date.
3. **Reviewing stubs**: During session planning, check this file for stubs with past-due planned dates.
4. **Detecting untracked stubs**: Run `grep -rn "NotImplementedError" core/whitemagic/ --include="*.py"`
   and cross-reference with this file.
