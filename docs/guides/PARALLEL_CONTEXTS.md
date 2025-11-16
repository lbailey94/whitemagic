# Parallel Memory Contexts

**Feature**: Multiple independent memory spaces running simultaneously  
**Status**: Available in v2.2.2+

---

## Overview

Parallel contexts allow you to work on multiple projects simultaneously, each with its own isolated memory space. Perfect for:
- Multi-project workflows
- Team collaboration (each member = separate context)
- Background operations (consolidation, search)
- Testing vs production separation

---

## Quick Start

### Method 1: CLI Flag
```bash
# Project A
whitemagic --base-dir ~/.whitemagic/projectA create --title "Feature X" --content "..."

# Project B (different terminal)
whitemagic --base-dir ~/.whitemagic/projectB create --title "Bugfix Y" --content "..."
```

### Method 2: Environment Variable
```bash
# Terminal 1: Project A
export WHITEMAGIC_BASE_DIR=~/.whitemagic/projectA
whitemagic create --title "Feature X" --content "..."

# Terminal 2: Project B
export WHITEMAGIC_BASE_DIR=~/.whitemagic/projectB
whitemagic create --title "Bugfix Y" --content "..."
```

### Method 3: Shell Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias wm-projectA='whitemagic --base-dir ~/.whitemagic/projectA'
alias wm-projectB='whitemagic --base-dir ~/.whitemagic/projectB'

# Usage
wm-projectA create --title "Feature X" --content "..."
wm-projectB create --title "Bugfix Y" --content "..."
```

---

## Use Cases

### 1. Multi-Project Development
```bash
# Client project
WHITEMAGIC_BASE_DIR=~/work/client-project whitemagic create ...

# Side project
WHITEMAGIC_BASE_DIR=~/work/side-project whitemagic create ...

# Personal notes
WHITEMAGIC_BASE_DIR=~/personal whitemagic create ...
```

**Benefits**:
- No memory cross-contamination
- Project-specific tags and organization
- Independent consolidation schedules

### 2. Team Collaboration
```bash
# Alice's memories
WHITEMAGIC_BASE_DIR=~/team/alice whitemagic create ...

# Bob's memories
WHITEMAGIC_BASE_DIR=~/team/bob whitemagic create ...

# Shared team memories
WHITEMAGIC_BASE_DIR=~/team/shared whitemagic create ...
```

**Benefits**:
- Individual memory spaces
- Shared context when needed
- Git-friendly (sync via repository)

### 3. Testing vs Production
```bash
# Production memories
whitemagic --base-dir ~/.whitemagic/prod create ...

# Test memories (don't pollute production)
whitemagic --base-dir ~/.whitemagic/test create ...
```

**Benefits**:
- Safe testing environment
- Can delete test context without affecting production
- Verify changes before committing

### 4. Background Operations
```bash
# Terminal 1: Interactive work
whitemagic create --title "Active work" ...

# Terminal 2: Background consolidation
whitemagic consolidate --dry-run false &
```

**Benefits**:
- Non-blocking operations
- Continue working while consolidating
- Parallel search operations

---

## Resource Usage

**Per context**:
- **Memory**: ~50-100MB (Python process)
- **CPU**: ~10-20% (idle), ~50-100% (active operations)
- **Disk I/O**: Minimal (markdown files are tiny)

**Scalability**:
- Can run 10-20 contexts comfortably on modern hardware
- Each context is independent (no shared state)
- File system handles concurrent reads naturally

---

## File Locking

**Write operations are safe**:
- Atomic writes prevent corruption
- File locking prevents race conditions
- Concurrent reads are fine (no locking needed)

**Example** (safe):
```bash
# Terminal 1
whitemagic create --title "Memory 1" ...

# Terminal 2 (same base-dir)
whitemagic create --title "Memory 2" ...
# Both will succeed safely
```

---

## Best Practices

### 1. Consistent Naming
```bash
# Good: Clear, consistent
~/.whitemagic/project-name/
~/.whitemagic/client-name/
~/.whitemagic/feature-branch/

# Avoid: Unclear, inconsistent
~/.whitemagic/temp/
~/.whitemagic/stuff/
~/.whitemagic/old2/
```

### 2. Environment Management
```bash
# .envrc (for direnv)
export WHITEMAGIC_BASE_DIR="$(pwd)/.whitemagic"

# Automatically switch context when changing directories
```

### 3. Backup Strategy
```bash
# Backup all contexts
for project in ~/.whitemagic/*/; do
    whitemagic --base-dir "$project" backup
done
```

### 4. Cleanup
```bash
# Remove old test contexts
rm -rf ~/.whitemagic/test-*

# Keep production contexts
ls -d ~/.whitemagic/prod-* ~/.whitemagic/client-*
```

---

## Python API

```python
from whitemagic import MemoryManager

# Project A
manager_a = MemoryManager(base_dir="~/.whitemagic/projectA")
manager_a.create_memory(title="Feature X", content="...")

# Project B
manager_b = MemoryManager(base_dir="~/.whitemagic/projectB")
manager_b.create_memory(title="Bugfix Y", content="...")

# Independent contexts, no interference
```

---

## MCP Server Configuration

```json
{
  "mcpServers": {
    "whitemagic-projectA": {
      "command": "npx",
      "args": ["whitemagic-mcp"],
      "env": {
        "WM_BASE_PATH": "/home/user/.whitemagic/projectA"
      }
    },
    "whitemagic-projectB": {
      "command": "npx",
      "args": ["whitemagic-mcp"],
      "env": {
        "WM_BASE_PATH": "/home/user/.whitemagic/projectB"
      }
    }
  }
}
```

**Use in IDE**:
- Switch between contexts via MCP server selection
- Each context appears as separate resource
- No cross-contamination

---

## Troubleshooting

### Context Not Found
```bash
# Create context first
mkdir -p ~/.whitemagic/new-project
whitemagic --base-dir ~/.whitemagic/new-project create --title "Init" --content "..."
```

### Permission Denied
```bash
# Check directory permissions
ls -la ~/.whitemagic/

# Fix if needed
chmod -R u+rw ~/.whitemagic/your-project/
```

### Wrong Context
```bash
# Verify which context you're using
echo $WHITEMAGIC_BASE_DIR

# Or check with list
whitemagic --base-dir ~/.whitemagic/projectA list
```

---

## Migration Guide

### From Single Context
```bash
# Old way (single global context)
whitemagic create ...

# New way (explicit contexts)
whitemagic --base-dir ~/.whitemagic/default create ...
```

### Moving Memories Between Contexts
```bash
# Copy entire memory directory
cp -r ~/.whitemagic/projectA/memory/* ~/.whitemagic/projectB/memory/

# Or selective copy
cp ~/.whitemagic/projectA/memory/short_term/*.md ~/.whitemagic/projectB/memory/short_term/
```

---

## Performance Considerations

**Parallel contexts are lightweight**:
- Each process is independent
- No shared memory or IPC overhead
- Filesystem naturally handles concurrent access
- Modern SSDs handle many small file operations well

**Benchmarks** (typical):
- Create memory: <10ms (same whether 1 or 10 contexts)
- Search: <50ms per context
- List: <20ms per context

**Total**: Can operate 10 contexts with <1 second combined response time

---

## Future Enhancements (v2.3.0+)

- **Context discovery**: Auto-list available contexts
- **Context templates**: Quick setup from templates
- **Context switching**: `whitemagic switch projectA`
- **Shared memories**: Link memories across contexts
- **Context analytics**: Track usage per context

---

**Status**: ✅ Feature complete in v2.2.2  
**Documentation**: Up to date  
**Examples**: See above  
**Support**: File issues on GitHub
