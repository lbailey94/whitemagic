# WhiteMagic Contributor Guide

**Version**: 25.0.1

## Getting Started

```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
cd core && uv sync --all-extras --dev
uv run pytest tests/ -n auto --timeout=60 -q
```

## Repository Layout

```
whitemagic/
├── core/                    # Python package (whitemagic)
│   ├── whitemagic/          # Source code
│   ├── tests/               # Test suite (unit, integration, verify)
│   ├── scripts/             # CI/verification scripts
│   └── pyproject.toml       # Package definition
├── benchmarks/              # Performance benchmarks and metrics
├── docs/                    # Documentation
├── .github/workflows/       # CI workflows (4 lanes: A/B/C/D)
├── app/                     # Next.js website
├── polyglot/                # Polyglot acceleration (Rust, Go, Zig, etc.)
└── sdk/                     # SDK packages (TypeScript, Python WASM)
```

## CI Lanes

- **Lane A (PR fast, <10 min)**: Lint, typecheck, version/fact drift, stub audit
- **Lane B (PR integration, <25 min)**: Full test suite, security tests, package build, WASM build
- **Lane C (Nightly)**: Coverage, reproducible build, live smoke, Slither
- **Lane D (Release)**: CI gate, PyPI publish, Docker, SBOM, sigstore

## Code Style

- **Ruff** is the hard gate: `ruff check whitemagic/ tests/`
- **Mypy** is advisory: `mypy whitemagic/ --ignore-missing-imports`
- **Blind-except (BLE001)**: Add `# ruff: noqa: BLE001` with a comment explaining why
- **No new `except Exception`** without explicit noqa and justification

## Test Tiers

| Tier | Location | Runs in | Timeout |
|------|----------|---------|---------|
| Unit | `tests/unit/` | Lane A/B | 60s |
| Integration | `tests/integration/` | Lane B | 120s |
| Verify (contract) | `tests/verify/` | Lane A/B | 30s |
| Benchmarks | `tests/benchmarks/` | Lane C | unlimited |
| Archive | `tests/archive_*/` | Not run | — |

## Adding a New Tool

1. **Define** the tool in `registry_defs/<domain>.py` (ToolDefinition with safety, stability, annotations)
2. **Handle** the tool in `handlers/<domain>.py` (handler function with typed args)
3. **Register** the handler in `dispatch_security.py` (handler mapping)
4. **Map** to a Gana in `prat_mappings.py` (PRAT routing)
5. **Add NLU patterns** in `handlers/meta_tool.py` (natural language routing)
6. **Test** in `tests/unit/test_<domain>.py`
7. **Verify** contract in `tests/verify/`

## Adding a New Galaxy

1. Add to `galaxy.canonical_taxonomy` in `galactic_map.py`
2. Assign a zone (CORE, INNER_RIM, MID_BAND, OUTER_RIM, FAR_EDGE)
3. Update `GALAXY_6D_STRATEGY.md` with language assignment
4. Add migration mapping if replacing a deprecated galaxy
5. Test with `galaxy.list` and `galaxy.stats` tools

## Commit Discipline

- Atomic commits: one logical change per commit
- Commit message format: `<scope>: <imperative description>`
- Examples:
  - `memory: fix FTS5 stopword flooding in OR queries`
  - `ci: remove false-green gates from security-ci.yml`
  - `docs: add public profiles and compatibility policy`

## Release Process

1. Update `VERSION` file
2. Update `CHANGELOG.md`
3. Update `AGENTS.md` version and changelog
4. Run `scripts/generate_facts.py` to refresh `PROJECT_STATE.md`
5. Tag: `git tag v<MAJOR>.<MINOR>.<PATCH>`
6. Push tag: `git push origin v<MAJOR>.<MINOR>.<PATCH>`
7. Release workflow (Lane D) handles PyPI, Docker, SBOM, sigstore
