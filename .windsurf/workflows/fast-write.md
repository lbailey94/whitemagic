---
description: Fast file I/O via cat shell writes and fragment reads — primary method for >10 line changes and batch exploration
---

# Fast I/O Protocol

## When to Use

- **Any file write >10 lines**: Use cat shell write (heredoc or `python3 -c`)
- **Any file overwrite/rewrite**: Use cat shell write (the `write_to_file` tool refuses existing files)
- **Multi-file batch writes**: Use `python3 -c` with multiple file operations in one command
- **Surgical 1-3 line edits**: Use the `edit` tool (it's fine for small changes)
- **Reading 3+ files**: Use fragment reads (batch `head`/`sed` in one command)
- **Scanning for patterns across files**: Use `grep -rn` via `run_command` instead of multiple `read_file` calls

## Write Techniques

### 1. Heredoc (for new files or full rewrites)

Use `'EOF'` (quoted) to prevent variable expansion. Use `>>` for append mode.

**WARNING**: Heredocs break when content contains backticks (markdown code blocks).
For any file containing backticks, use the Python -c method below instead.

### 2. Python -c (for atomic writes with logic)

Read file, make replacements, write back — all in one command.

### 3. Multi-file batch (write several files in one command)

Use a dict of paths to content in a single `python3 << 'PYEOF'` block.

## Read Techniques

### 4. Fragment reads (batch read multiple files in one command)

Read first N lines of multiple files using a for loop with `head -N`.

### 5. Pattern scan (find relevant code across files)

Use `grep -rn "pattern" path/ --include="*.py" -A 3` to find definitions with context.

### 6. Selective reads (specific line ranges)

Use `sed -n 'START,ENDp' /path/to/file.py` to read specific line ranges.

## Safety Harnesses

### After writing Python files, always validate syntax:

`python3 -c "import ast; ast.parse(open('file').read()); print('OK')"`

### After writing multiple files, run ruff on all changed files:

`ruff check path1.py path2.py --select F401,I001,E999`

### For test files, run the test immediately:

`pytest tests/unit/test_file.py -v --timeout=10 --tb=short`

## Why This Is Faster

- `edit` tool: Read file, craft exact old_string match, apply edit, handle uniqueness errors, repeat for each edit
- `write_to_file`: Refuses existing files, forcing you to use `edit` instead
- Cat shell write: Write entire file content in one command, no matching needed, no existence checks
- Fragment reads: Read 5 files in one command vs 5 separate `read_file` calls
- Pattern scan: Find relevant code across the entire codebase in one grep vs multiple search tool calls
- Even with 3x retries, cat shell writes are still 10x faster than a single `edit` call for >10 lines

## Anti-Patterns to Avoid

- Do NOT switch to `edit`/`multi_edit` mid-session after using cat shell writes successfully
- Do NOT use `write_to_file` for existing files (it will error)
- Do NOT use `edit` for full file rewrites (use heredoc instead)
- Do NOT forget the safety harness — always validate after writing
- Do NOT use multiple `read_file` calls when a single `grep -rn` or `head` batch would suffice
- Do NOT use `code_search` for simple pattern matching when `grep -rn` is faster and more precise
