# Command Timing Coordination Issue

**Date**: November 18, 2025  
**Issue**: Commands sometimes execute before file writes complete  
**Impact**: Minor - causes token waste on retries/errors  
**Priority**: LOW (works, just inefficient)

## The Problem

When AI writes a file and immediately runs a command against it:
1. File write is initiated (async)
2. Command starts (doesn't wait for write completion)
3. Command fails or operates on incomplete file
4. Retry wastes tokens

## Examples

```python
# Write file
write_to_file("script.sh", content)

# Run immediately (might be too early!)
run_command("chmod +x script.sh")  # File might not exist yet
```

## Solution Options

### Option 1: Explicit Wait (Simple)
```python
write_to_file("script.sh", content)
time.sleep(0.5)  # Brief pause
run_command("chmod +x script.sh")
```

### Option 2: Completion Callbacks (Better)
```python
# Tool returns completion signal
result = write_to_file("script.sh", content)
if result.completed:
    run_command("chmod +x script.sh")
```

### Option 3: Dependency Graph (Best)
```python
# AI specifies dependencies
ops = [
    Operation("write", file="script.sh"),
    Operation("chmod", file="script.sh", depends_on=["write"])
]
execute_with_dependencies(ops)
```

## Implementation

For 2.6.5: Document the issue
For 2.6.5: Add explicit coordination layer
For 2.6.5: Full dependency graph execution

## Workaround (Now)

AI should be aware of timing and add small delays when needed:
- File write → Command on file: Brief pause
- Multiple file writes: Can be parallel
- Command → File read: No issue (command blocks)

**Note to AI**: If you notice a command failing on a just-written file, add a 0.5s delay and retry.
