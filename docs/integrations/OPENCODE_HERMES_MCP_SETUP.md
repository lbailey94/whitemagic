# WhiteMagic MCP Setup for OpenCode & Hermes

**Date:** 2026-05-30
**Status:** Verified — 28/28 Ganas passing, Rust backend live, Redis connected
**Prerequisites:** Python 3.12+, WhiteMagic venv activated, Redis running (for `broker.status`)

---

## Quick Start

```bash
cd <WHITEMAGIC_ROOT>
source .venv/bin/activate
python -m whitemagic.run_mcp_lean  # stdio mode (default)
```

Verify the server starts cleanly:
```bash
python -c "from whitemagic.run_mcp_lean import server; print('OK')"
```

---

## OpenCode (stdio) — VERIFIED

OpenCode uses `~/.config/opencode/opencode.jsonc` (global) or project-local `opencode.jsonc`.

### Config file

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "whitemagic": {
      "type": "local",
      "command": [
        "<WHITEMAGIC_ROOT>/.venv/bin/python",
        "-m",
        "whitemagic.run_mcp_lean"
      ],
      "enabled": true,
      "environment": {
        "WM_SILENT_INIT": "1",
        "PYTHONPATH": "<WHITEMAGIC_ROOT>/core"
      }
    }
  }
}
```

**Note:** `command` must be an **array**. `environment` (not `env`) sets env vars.

**Verify:**
```bash
opencode mcp list
# → ✓ whitemagic connected
```

**Test tool invocation:**
```bash
opencode run "Call whitemagic gana_root health_report"
# → Health Report — v22.2.0 ...
```

### Option C: Inline in `AGENTS.md`
OpenCode reads project-local `AGENTS.md`. Add:

```markdown
## MCP Tools Available
- `gana_root/health_report` — System health check before risky operations
- `gana_straddling_legs/get_dharma_guidance` — Ethical/policy review before tool use
- `gana_neck/create_memory` — Log decisions to the Karma Ledger
- `gana_three_stars/think` — Structured reasoning / debate
- `gana_ghost/capabilities` — Introspect available governance primitives
```

---

## Hermes (stdio) — VERIFIED

Hermes MCP uses a wrapper script (env vars cannot be passed directly via CLI).

### 1. Create wrapper script

```bash
cat > /tmp/whitemagic_mcp.sh << 'EOF'
#!/bin/bash
export WM_SILENT_INIT=1
export PYTHONPATH=<WHITEMAGIC_ROOT>/core
exec <WHITEMAGIC_ROOT>/.venv/bin/python -m whitemagic.run_mcp_lean
EOF
chmod +x /tmp/whitemagic_mcp.sh
```

### 2. Add to Hermes

```bash
hermes mcp add whitemagic --command /tmp/whitemagic_mcp.sh
# → Enable all 28 tools? [Y/n/select]: Y
```

**Verify:**
```bash
hermes mcp list
# → whitemagic  /tmp/whitemagic_mcp.sh  all  ✓ enabled

hermes mcp test whitemagic
# → ✓ Connected (1467ms)
# → ✓ Tools discovered: 28
```

**Test tool invocation:**
```bash
hermes chat -q "Call whitemagic gana_root health_report" -Q --accept-hooks
# → Health Report — v22.2.0 ...
```

---

## Hermes (ACP Mode)

If running Hermes in ACP mode (`hermes acp`), WhiteMagic registers automatically as an external tool provider:

```bash
hermes acp --mcp-command "<WHITEMAGIC_ROOT>/.venv/bin/python -m whitemagic.run_mcp_lean"
```

---

## HTTP Mode (for remote / messaging gateway)

Start the HTTP transport:
```bash
python -m whitemagic.run_mcp_lean --http --port 8770
```

Then point any MCP HTTP client to:
```
http://127.0.0.1:8770/mcp
```

---

## Governance Workflow (Recommended Agent Pattern)

A well-behaved agent runtime should follow this pattern when using WhiteMagic:

1. **DISCOVER** — `tools/list` to see available governance primitives
2. **AUDIT** — `gana_root/health_report` before session start
3. **DECIDE** — `gana_straddling_legs/get_dharma_guidance` before risky tool calls
4. **ACT** — Execute the planned operation
5. **LOG** — `gana_neck/create_memory` to append to the Karma Ledger
6. **VERIFY** — `gana_winnowing_basket/memory_search` to confirm audit trail

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: No module named whitemagic` | `PYTHONPATH` not set | Add `"PYTHONPATH": "/path/to/WHITEMAGIC/core"` to env |
| `broker.status` returns `missing_dependency` | Redis Python package not installed | `pip install redis` |
| `view_hologram` returns `degraded` | Rust backend not built | `cd core/whitemagic-rust && maturin develop --release` |
| Server takes >5s to start | Full subsystem init | Set `WM_SILENT_INIT=1` in env |
| Only 27 tools visible | One Gana failed to load | Check `wm_mcp` logs for ImportError |

---

## Verification Commands

```bash
# 1. Full 28-Gana smoke test (through MCP layer)
cd core && python -m pytest tests/integration/test_opencode_hermes_bridge.py -v

# 2. All 28 Ganas via standalone JSON report
cd core && python tests/integration/test_all_ganas_mcp.py

# 3. Rust backend check
python -c "from whitemagic.core.intelligence.hologram.engine import get_hologram_engine; print(get_hologram_engine().enabled)"

# 4. Redis broker check
python -c "import redis.asyncio as r; import asyncio; asyncio.run(r.Redis().ping())"

# 5. Doc drift & version checks
python scripts/check_doc_drift.py && python scripts/check_versions.py
```

---

## Test Baseline (2026-05-30)

| Check | Result |
|-------|--------|
| Full Python suite | 2403 passed, 61 skipped, 1 pre-existing archive failure |
| Bridge tests | 40 passed (11 original + 28 Gana smoke + 1 workflow) |
| All-ganas MCP | 28/28 success, 0 crashes, avg latency 102ms |
| OpenCode integration | ✅ Connected, 28 tools discovered, tool invocation works |
| Hermes integration | ✅ Connected (1467ms), 28/28 tools enabled, tool invocation works |
| Rust SpatialIndex5D | 1.14M ops/s (batch add), 57K queries/s |
| Doc drift | ✅ Pass |
| Version check | ✅ Pass |
