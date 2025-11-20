# ⚡ Speed Optimization Guide

**Purpose**: Maximize AI efficiency using discovered techniques  
**Impact**: 10-100x faster file operations, better token usage

---

## Core Principle

**Shell > Python > Edit Tool**

Always prefer faster methods. Edit tool is for small, targeted changes only.

---

## Technique 1: Shell Speed (Instant Writes)

### Pattern
```bash
cat > file.py << 'EOF'
#!/usr/bin/env python3
[entire file content here]
