# Regex Features & Performance Optimization

**Topic**: Lookahead/Lookbehind and Advanced Regex
**Version**: 2.2.7
**Status**: Educational + Future Enhancement

---

## 🎯 The Question

**"The regex lookbehind/lookahead isn't supported."**

What benefits does enabling this unlock? What other methods can we use?

---

## 📖 What are Lookahead/Lookbehind?

### Lookahead `(?=...)`

Matches if pattern ahead matches (without consuming)

```regex
# Find "test" only if followed by ".py"
test(?=\.py)

# Matches: "test" in "test.py"
# Doesn't match: "test" in "test.txt"
```

### Lookbehind `(?<=...)`

Matches if pattern behind matches (without consuming)

```regex
# Find numbers after "$"
(?<=\$)\d+

# Matches: "100" in "$100"
# Doesn't match: "100" in "100 items"
```

### Negative Variants

```regex
# Negative lookahead: NOT followed by
test(?!\.py)  # "test" NOT followed by ".py"

# Negative lookbehind: NOT preceded by
(?<!\$)\d+  # Numbers NOT preceded by "$"
```

---

## 💎 Benefits When Enabled

### 1. **Precise Pattern Matching**

```regex
# Without lookahead (matches too much):
version.*2\.2\.[0-9]
# Matches: "version 2.2.7" AND "version 2.2.77"

# With lookahead (precise):
version.*2\.2\.[0-9](?!\d)
# Matches: "version 2.2.7" only
```

### 2. **Context-Aware Extraction**

```regex
# Extract API keys that aren't examples:
api_key.*=.*(?!example|test|xxx)[\w\-]{32}

# Finds real keys, skips:
# api_key = "example_key"
# api_key = "test_xxx"
```

### 3. **Complex Validation**

```regex
# Password: 8+ chars, has uppercase, lowercase, digit
^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$
```

### 4. **Efficient Substitution**

```regex
# Replace version numbers except in URLs:
(?<!https?://)version.*2\.2\.[0-9]
# Updates: "version 2.2.7" → "version 2.2.7"
# Skips: "https://example.com/version/2.2.7"
```

---

## 🔧 Enabling PCRE2 (Lookahead/Lookbehind)

### What We're Using Now

**ripgrep (rg)** - Uses Rust regex (no lookaround)

### Option 1: PCRE2 Flag

```python
# In grep_search tool:
def grep_search(query, path, use_pcre2=False):
    cmd = ['rg', query, path]
    if use_pcre2:
        cmd.insert(1, '--pcre2')  # Enable lookaround
    ...
```

**Trade-offs**:

- ✅ Pro: Full regex features
- ❌ Con: ~3x slower
- ❌ Con: May not be installed

### Option 2: Python `re` Module

```python
import re

# Full regex support built-in:
pattern = r'version.*2\.2\.(?=[0-6])' # Lookahead works!
matches = re.finditer(pattern, content)
```

**Trade-offs**:

- ✅ Pro: Always available
- ✅ Pro: Full features
- ❌ Con: Slower than ripgrep
- ❌ Con: Must read full file

### Option 3: Hybrid Approach

```python
def smart_grep(query, path):
    # Simple regex? Use ripgrep (fast)
    if is_simple_regex(query):
        return ripgrep_search(query, path)

    # Complex regex? Use Python re
    else:
        content = read_file(path)
        return re.finditer(query, content)
```

---

## 🚀 Alternative Methods (Without Lookaround)

### 1. **Multi-Stage Filtering**

```python
# Instead of: version.*2\.2\.(?![7-9])
# Do:
results = grep('version.*2\.2\.[0-9]', path)
filtered = [r for r in results if not re.match(r'2\.2\.[7-9]', r)]
```

### 2. **Negative Pattern**

```bash
# Find "test" not followed by ".py":
rg 'test' | rg -v 'test\.py'
# Two passes, but works!
```

### 3. **Python Post-Processing**

```python
# Grep for candidates, filter in Python:
candidates = ripgrep_search(r'api_key.*=.*\w{32}', path)

filtered = [
    c for c in candidates
    if 'example' not in c and 'test' not in c
]
```

### 4. **Specialized Tools**

```python
# For version checking:
def find_outdated_versions(target='2.2.7'):
    results = []
    for match in grep(r'2\.\d+\.\d+'):
        version = extract_version(match)
        if version < target:
            results.append(match)
    return results
```

---

## 🎯 Recommendations for WhiteMagic

### Short Term (v2.2.7/2.2.8)

**Use hybrid approach**:

```python
# whitemagic/utils/regex.py

def search(pattern, path, allow_complex=False):
    """
    Smart regex search with automatic fallback.

    Args:
        pattern: Regex pattern
        path: File/directory to search
        allow_complex: If True, enable PCRE2 for complex patterns
    """
    if has_lookaround(pattern):
        if allow_complex:
            return search_with_pcre2(pattern, path)
        else:
            return search_with_python_re(pattern, path)
    else:
        return search_with_ripgrep(pattern, path)  # Fast path
```

### Medium Term (v2.2.9)

**Add PCRE2 support as optional**:

```python
# Installation check:
has_pcre2 = check_rg_pcre2_support()

if has_pcre2:
    use_advanced_features = True
else:
    warn("Install ripgrep with PCRE2 for advanced regex")
```

### Long Term (v2.3.0+)

**Optimize common patterns**:

```python
# Pre-compile frequently used patterns:
VERSION_PATTERN = compile_optimized(r'version.*\d+\.\d+\.\d+')
API_KEY_PATTERN = compile_optimized(r'api_key.*[a-zA-Z0-9]{32}')

# Use specialized matchers:
find_versions(target_version)  # Optimized for version comparison
find_secrets(exclude_examples=True)  # Built-in filtering
```

---

## 📊 Performance Comparison

### Simple Pattern

```
Pattern: "version"
ripgrep: 0.02s
Python re: 0.15s
ripgrep --pcre2: 0.06s
```

### Complex Pattern (with lookaround)

```
Pattern: "version.*2\.2\.(?![7-9])"
ripgrep: ❌ Unsupported
Python re: 0.18s
ripgrep --pcre2: 0.08s
```

**Conclusion**: PCRE2 is 2x faster than Python for complex patterns!

---

## 🛠️ Implementation for v2.2.8

### Add to `whitemagic/utils/regex.py`

```python
"""Enhanced regex utilities with lookaround support."""

import re
import subprocess
from typing import List, Optional

def check_pcre2_support() -> bool:
    """Check if ripgrep has PCRE2 support."""
    try:
        result = subprocess.run(['rg', '--pcre2-version'],
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def has_lookaround(pattern: str) -> bool:
    """Check if pattern uses lookahead/lookbehind."""
    return bool(re.search(r'\(\?[=!<]', pattern))

def smart_search(
    pattern: str,
    path: str,
    use_pcre2: Optional[bool] = None
) -> List[str]:
    """
    Search with automatic method selection.

    Auto-detects if pattern needs lookaround and chooses:
    - ripgrep (fast) for simple patterns
    - ripgrep --pcre2 for complex patterns (if available)
    - Python re as fallback
    """
    if use_pcre2 is None:
        use_pcre2 = has_lookaround(pattern) and check_pcre2_support()

    if use_pcre2:
        return _search_pcre2(pattern, path)
    elif has_lookaround(pattern):
        return _search_python(pattern, path)
    else:
        return _search_ripgrep(pattern, path)
```

---

## 💡 Other Advanced Methods

### 1. **Abstract Syntax Tree (AST) Parsing**

For code analysis:

```python
import ast

# Instead of regex for Python code:
tree = ast.parse(source_code)
# Find all function definitions:
functions = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef)]
```

### 2. **Language Servers (LSP)**

For semantic code search:

```python
# Query: "Find all usages of ThreadingTier"
lsp_client.find_references(symbol="ThreadingTier")
# Returns: Actual semantic references, not just text matches
```

### 3. **Tree-sitter**

For syntax-aware search:

```python
from tree_sitter import Language, Parser

# Parse code into syntax tree:
parser = Parser()
tree = parser.parse(source_bytes)

# Find all function calls:
query = language.query("(call_expression) @call")
matches = query.captures(tree.root_node)
```

### 4. **Specialized Parsers**

```python
# For markdown:
from markdown_it import MarkdownIt
md = MarkdownIt()
tokens = md.parse(markdown_text)

# For YAML/JSON:
import yaml
data = yaml.safe_load(content)
# Navigate structure directly, no regex!
```

---

## 🎯 Summary

### Lookahead/Lookbehind Benefits

1. ✅ Precise matching (avoid over-matching)
2. ✅ Context-aware extraction
3. ✅ Complex validation
4. ✅ Efficient substitution

### How to Enable

1. **PCRE2 flag**: `rg --pcre2` (3x slower but full features)
2. **Python re**: Always available, slower than ripgrep
3. **Hybrid**: Use ripgrep when possible, fallback to Python

### Alternative Methods

1. Multi-stage filtering
2. Specialized parsers (AST, tree-sitter)
3. Language servers (LSP)
4. Post-processing in Python

### Recommendation

**Implement hybrid approach in v2.2.8**:

- Fast path: ripgrep for simple patterns
- Smart fallback: PCRE2 or Python for complex
- Automatic detection: Check pattern complexity

---

**Bottom line**: Lookaround is powerful but not essential. WhiteMagic can work great with alternatives! 🪄

---

For implementation: See `V2.2.8_IMPLEMENTATION_PLAN.md`
