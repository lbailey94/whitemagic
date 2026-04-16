# Polyglot Superseded Archive

Python files moved here when their hot paths have been translated to a faster
polyglot implementation. The Python file remains for reference, fallback, and
historical record — it is NOT deleted.

## Naming Convention

`{original_module_name}.py.superseded_by_{language}_{date}.py`

## Index

| Original File | Superseded By | Language | Date | Notes |
|--------------|---------------|----------|------|-------|
| (none yet — V019 Tier 1 in progress) | | | | |

## Policy

1. **Never delete** — archive only. Python fallback paths remain in the live bridges.
2. **Document the translation** — note which functions moved where.
3. **Keep tests** — the Python version's tests still run as regression checks.
4. **LOC tracking** — `scripts/codebase_census.py` excludes this directory from active counts.

## Candidates for Next Archive (V019 Tier 2+)

| File | Hot Path | Target Language | Status |
|------|----------|-----------------|--------|
| `core/memory/graph_walker.py` (BFS inner loop) | parallel BFS | Zig `parallel_walk.zig` | Tier 1 |
| `core/acceleration/simd_cosine.py` (batch cosine) | batch cosine | Zig `simd_similarity.zig` | Already wired |
| `core/intelligence/synthesis/rrf_fusion.py` | RRF merge | Julia `graph_rrf.jl` | Already wired |
| `core/agents/deploy_shadow_clones.py` (orchestration) | clone dispatch | Elixir `CascadeExecutor` | Tier 2 |
