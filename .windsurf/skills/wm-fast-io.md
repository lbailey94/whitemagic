---
description: Fast file I/O techniques for WhiteMagic — cat heredocs, python3 batch writes, WM MCP code intelligence tools
---

# WM Fast File I/O

## When to Use What

### Writing

| Scenario | Command | Example |
|---|---|---|
| Full file rewrite (>10 lines) | `cat << 'EOF' > file.py` | `cat << 'EOF' > core/whitemagic/module.py` |
| Full file with backticks | `python3 << 'PYEOF'` | `python3 << 'PYEOF'\nfrom pathlib import Path\nPath("file.py").write_text(\"content with `backticks`\")\nPYEOF` |
| Multi-file batch | `python3 << 'PYEOF'` | `python3 << 'PYEOF'\nfiles = {"a.py": "...", "b.py": "..."}\nfor path, content in files.items():\n    Path(path).write_text(content)\nPYEOF` |
| Regex transform | `python3 -c` | `python3 -c "import re; ..."` |
| 1-3 line surgical edit | `edit` tool | Use Windsurf's built-in edit tool |

### Reading

| Scenario | Command |
|---|---|
| Batch read 3+ files | `head -50 file1.py file2.py file3.py` |
| Specific lines | `sed -n '100,120p' file.py` |
| Pattern + context | `grep -rn "pattern" path/ --include="*.py" -A 3` |
| Codebase survey | `wm(route='gana_chariot.strata.survey', args={'path': '/home/lucas/Desktop/WHITEMAGIC'})` |
| Static analysis | `wm(route='gana_chariot.strata.analyze', args={'path': '/home/lucas/Desktop/WHITEMAGIC'})` |
| Code chunk search | `wm(route='gana_winnowing_basket.fragment.search', args={'path': '/home/lucas/Desktop/WHITEMAGIC', 'query': 'authentication'})` |

### After Any Write

```bash
# Validate syntax
python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"

# Lint
ruff check file.py --select F401,I001,E999,G004,PLE1205
```

## Anti-Patterns

- **`sed -i` for multi-line changes** — use `python3 -c` instead
- **`edit` tool for >10 lines** — use `cat` heredoc instead
- **`write_to_file` for existing files** — use `cat` or `edit` instead
- **Multiple `read_file` calls** — batch with `head` or `sed` in one `run_command`
- **Skipping validation after writes** — always run `ast.parse` + `ruff check`

## WM MCP Integration

The WhiteMagic MCP server exposes tools that are faster than manual approaches:

- **`strata.survey`**: File metadata + git history in one call (replaces multiple `list_dir` + `git log` calls)
- **`strata.analyze`**: 10+ static analysis checkers with auto-fix proposals (replaces manual `ruff` + visual review)
- **`fragment.search`**: Rust-accelerated code chunk search (replaces multiple `grep_search` calls)
- **`codegenome.generate`**: Template-based code generation (replaces manual boilerplate writing)
- **`windsurf_read_conversation`**: Read prior Cascade sessions (replaces manual context recovery)
- **`batch_read_memories`**: Read N memories in one call (replaces N individual `wm` calls)

## Validation Checklist

After any batch write or transform:
1. `python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"` for each file
2. `ruff check path/ --select F401,I001,E999,G004,PLE1205` for the changed files
3. Run the relevant test suite: `python -m pytest tests/unit/test_module.py -q --timeout=30`
