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
Path("/path/to/file.py").write_text("""content with backticks and $vars""")
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
Use `python3 << 'PYEOF'` (heredoc) for regex-based transforms across files.

**CRITICAL**: Avoid `python3 -c "..."` with strings containing backslash escapes
like `\b`, `\n`, `\t` inside triple-quoted strings. The outer non-raw string
interprets these before the inner `r"..."` raw prefix can protect them, causing
silent corruption (e.g. `\b` becomes `\x08` backspace).

**Wrong** (corrupts `\b` to backspace):

    python3 -c "
    new = '''r\"(pattern)\b\"'''  # \b becomes \x08 here!
    "

**Right** (use heredoc):

    python3 << 'PYEOF'
    import re, pathlib
    for f in pathlib.Path('whitemagic/').rglob('*.py'):
        content = f.read_text()
        fixed = re.sub(r'pattern', 'replacement', content)
        if fixed != content:
            f.write_text(fixed)
            print(f'Fixed {f}')
    PYEOF

**If you must use `python3 -c`**, double-escape backslashes: `\\b` not `\b`.

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

## Appendix: Known Pitfalls

### Backslash Corruption in `python3 -c`

**Symptom**: Regex patterns containing `\b` (word boundary) silently become `\x08`
(backspace character) when written via `python3 -c "..."`.

**Root cause**: In `python3 -c "..."`, triple-quoted strings are **not** raw strings.
The `\b` inside the outer triple-quoted string is interpreted as backspace before
the inner `r"..."` raw string prefix can protect it.

**Fix**: Use `python3 << 'PYEOF'` (heredoc) instead of `python3 -c "..."` whenever
the content contains backslash escapes. The heredoc delimiter (quoted) prevents
shell interpretation, and Python processes the content correctly.

**Detection**: Check for `\x08` bytes in written files:

    python3 -c "data = open('file.py','rb').read(); print(f'backspace count: {data.count(8)}')"
