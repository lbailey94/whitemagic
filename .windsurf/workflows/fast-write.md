---
description: Fast file I/O — cat heredocs, python3 batch writes, and WM MCP code intelligence tools for rapid development
---

# Fast Write Workflow

Use the fastest safe technique for each file operation. Never default to slow tools when fast ones are available.

## Step 1: Classify the Change

- **1-3 lines, surgical** → Use `edit` tool (Windsurf built-in)
- **4-10 lines, one file** → Use `multi_edit` tool (Windsurf built-in)
- **>10 lines or full rewrite** → Go to Step 2
- **Multi-file batch** → Go to Step 3
- **Regex transform** → Go to Step 4

## Step 2: Large Single-File Write

// turbo
Use `cat << 'EOF' > file.py` via `run_command`:

```bash
cat << 'EOF' > /path/to/file.py
# file content here
EOF
```

If the content contains backticks or `$()`, use `python3 << 'PYEOF'` instead:

```bash
python3 << 'PYEOF'
from pathlib import Path
Path("/path/to/file.py").write_text('''content with `backticks` and $vars''')
PYEOF
```

## Step 3: Multi-File Batch Write

// turbo
Use `python3 << 'PYEOF'` with a dict of paths:

```bash
python3 << 'PYEOF'
from pathlib import Path
files = {
    "file1.py": "content1",
    "file2.py": "content2",
}
for path, content in files.items():
    Path(path).write_text(content)
    print(f"Wrote {path}")
PYEOF
```

## Step 4: Regex Transform

// turbo
Use `python3 -c` for regex-based transforms across files:

```bash
python3 -c "
import re, pathlib
for f in pathlib.Path('whitemagic/').rglob('*.py'):
    content = f.read_text()
    fixed = re.sub(r'pattern', 'replacement', content)
    if fixed != content:
        f.write_text(fixed)
        print(f'Fixed {f}')
"
```

## Step 5: Validate

// turbo
After any write, validate syntax and lint:

```bash
python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"
ruff check file.py --select F401,I001,E999,G004,PLE1205
```

## Step 6: WM MCP Code Intelligence (Optional)

For codebase analysis before or after writes:
- `wm(route='gana_chariot.strata.survey')` — surface survey
- `wm(route='gana_chariot.strata.analyze')` — static analysis with auto-fix
- `wm(route='gana_winnowing_basket.fragment.search')` — Rust-accelerated code search
