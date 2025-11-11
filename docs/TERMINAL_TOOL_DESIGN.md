# Terminal Tool: Structured Execution for WhiteMagic

**Version**: 1.0  
**Status**: Design Phase  
**Target**: Phase 2C (after Semantic Search)  
**Timeline**: 4-5 weeks  
**Last Updated**: November 11, 2025

---

## 🎯 **Executive Summary**

The Terminal Tool adds **structured, safe terminal execution** to WhiteMagic, enabling code-mode agents to perform real work on repositories and systems. Combined with WhiteMagic's memory system, this creates a complete agentic platform.

### **Why This Matters**

1. **Industry Pivot**: AI moving from prompt-mode → code-mode (Claude computer control, Anthropic research)
2. **Complete Platform**: Memory (context) + Terminal (action) = full agent capabilities
3. **Universal Adapter**: Terminal is what models already know; no schema bloat
4. **Developer Native**: Feels like using Git/CLI tools, not a proprietary system

### **Core Value Proposition**

> **"WhiteMagic becomes the universal execution layer for AI agents, with memory retention + safe terminal access, enabling real-world workflows without prompt bloat."**

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────┐
│                    WhiteMagic Platform                   │
├──────────────────┬──────────────────┬───────────────────┤
│   Memory System  │  Terminal Tool   │   MCP Interface   │
│   (Existing)     │   (New)          │   (Existing)      │
├──────────────────┼──────────────────┼───────────────────┤
│ • Tiered memory  │ • exec API       │ • 7 memory tools  │
│ • Semantic search│ • OCI sandbox    │ • 4 resources     │
│ • Consolidation  │ • Patch preview  │ • IDE integration │
│ • Backup/restore │ • Allowlist      │                   │
└──────────────────┴──────────────────┴───────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───▼────┐      ┌──────▼─────┐     ┌─────▼────┐
    │  REST  │      │    MCP     │     │   CLI    │
    │  API   │      │   Tools    │     │   (wm)   │
    └────────┘      └────────────┘     └──────────┘
```

### **Module Structure**

```
whitemagic/
├── terminal/
│   ├── __init__.py           # Public API
│   ├── executor.py           # Core execution engine
│   ├── sandbox.py            # OCI/container management
│   ├── allowlist.py          # Command filtering + profiles
│   ├── patch.py              # Diff generation + preview
│   ├── audit.py              # Run logging + correlation
│   ├── approver.py           # TUI/API approval flow
│   └── models.py             # Pydantic models
│
├── api/routes/
│   ├── exec.py               # POST /exec endpoints
│   ├── fs.py                 # File system operations
│   └── git.py                # Git operations
│
└── cli/
    └── terminal.py           # wm exec, wm ui commands
```

---

## 🔌 **API Design**

### **1. Execution API**

#### **POST /api/v1/exec**

Execute a command with safety controls.

**Request**:
```json
{
  "cmd": "rg",
  "args": ["TODO", "--json", "-i"],
  "cwd": "/workspace/project",
  "stdin": null,
  "timeout_ms": 30000,
  "env": {
    "TERM": "xterm-256color"
  },
  "mode": "read",
  "correlation_id": "run_abc123"
}
```

**Modes**:
- `read`: Read-only (default), no file modifications
- `write`: Can modify files, requires approval + patch preview
- `net`: Network access allowed (requires explicit permission)

**Response**:
```json
{
  "run_id": "exec_xyz789",
  "correlation_id": "run_abc123",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_ms": 156,
  "files_changed": [],
  "status": "completed"
}
```

**Write Mode Response** (requires approval):
```json
{
  "run_id": "exec_xyz789",
  "status": "awaiting_approval",
  "patch_preview": {
    "files": [
      {
        "path": "src/app.py",
        "action": "modified",
        "diff": "--- a/src/app.py\n+++ b/src/app.py\n..."
      }
    ],
    "summary": "Modified 1 file: src/app.py"
  },
  "approval_url": "/api/v1/exec/exec_xyz789/approve"
}
```

---

### **2. File System API**

#### **POST /api/v1/fs/patch**

Apply a reviewed patch to files.

**Request**:
```json
{
  "patches": [
    {
      "path": "src/app.py",
      "diff": "--- a/src/app.py\n+++ b/src/app.py\n...",
      "action": "modify"
    }
  ],
  "commit_message": "wm: applied patch run_abc123",
  "auto_commit": true
}
```

**Response**:
```json
{
  "applied": 1,
  "failed": 0,
  "commit_sha": "a1b2c3d",
  "files_changed": ["src/app.py"]
}
```

#### **GET /api/v1/fs/glob**

Search for files matching a pattern.

**Query Params**:
- `pattern`: Glob pattern (e.g., `**/*.py`)
- `cwd`: Working directory

**Response**:
```json
{
  "files": [
    "src/app.py",
    "tests/test_app.py"
  ],
  "count": 2
}
```

---

### **3. Git API**

#### **GET /api/v1/git/diff**

Get diff between worktree and HEAD.

**Response**:
```json
{
  "diff": "diff --git a/src/app.py b/src/app.py\n...",
  "files_changed": 3,
  "insertions": 45,
  "deletions": 12
}
```

#### **GET /api/v1/git/status**

Get repository status.

**Response**:
```json
{
  "branch": "main",
  "clean": false,
  "ahead": 0,
  "behind": 0,
  "staged": 1,
  "unstaged": 2,
  "untracked": 0
}
```

---

## 🔐 **Security Model**

### **Principle: Safe by Default**

1. **Read-only by default**: Writes require explicit approval
2. **Network isolation**: No outbound network unless `mode:"net"`
3. **Command allowlist**: Only approved commands can run
4. **Containerization**: All commands run in OCI containers
5. **Audit trail**: Every operation logged with correlation IDs

### **OCI Containerization**

```yaml
Container Spec:
  User: non-root (uid 1000)
  Root FS: read-only
  Capabilities: CAP_DROP=ALL
  Network: none (unless mode:"net")
  Mounts:
    - /workspace: bind-mount (read-only for read mode)
    - /tmp: tmpfs
  Resource Limits:
    CPU: 2 cores
    Memory: 1GB
    Time: 60s (default timeout)
```

### **Command Allowlist**

**Profiles**:

```python
PROFILES = {
    "dev": {
        # Full access for development
        "commands": ["*"],
        "network": True,
        "write": True
    },
    "ci": {
        # CI/CD pipeline
        "commands": ["git", "npm", "pip", "pytest", "rg", "fd"],
        "network": True,
        "write": True
    },
    "agent": {
        # AI agent (most restrictive)
        "commands": ["rg", "fd", "jq", "sd", "git status", "git diff"],
        "network": False,
        "write": "requires_approval"
    },
    "prod": {
        # Production (read-only)
        "commands": ["rg", "fd", "jq", "git status"],
        "network": False,
        "write": False
    }
}
```

**Blocked Commands** (always):
- `rm -rf`, `dd`, `mkfs`, `chmod 777`
- `curl | sh`, `wget | bash`
- `sudo`, `su`
- File system damage commands

### **Patch Approval Flow**

```
1. Agent requests write operation
2. System generates patch preview
3. Patch sent to approval mechanism:
   - TUI approver (wm ui)
   - Web UI
   - Auto-approve (if policy allows)
4. Human reviews:
   - See diff with syntax highlighting
   - See affected files + line counts
   - Approve or deny
5. If approved:
   - Apply patch
   - Auto-commit with signed message
   - Link to run ID in commit
```

---

## 🎨 **User Experience**

### **TUI Approver (wm ui)**

```
╭─────────────────────────────────────────────────────────╮
│  WhiteMagic Terminal Execution Approval                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Run ID: exec_xyz789                                    │
│  Command: sd 'old_pattern' 'new_pattern' src/app.py     │
│  Mode: write                                            │
│  Correlation: run_abc123                                │
│                                                          │
│  ┌───────────────────────────────────────────────┐     │
│  │  Patch Preview (1 file changed)               │     │
│  ├───────────────────────────────────────────────┤     │
│  │  src/app.py                                    │     │
│  │  ─────────────────────────────────────────────│     │
│  │  - old_pattern                                 │     │
│  │  + new_pattern                                 │     │
│  │                                                │     │
│  │  @@ -45,6 +45,6 @@                           │     │
│  │   def process():                               │     │
│  │ -     result = old_pattern()                  │     │
│  │ +     result = new_pattern()                  │     │
│  │       return result                            │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  Impact: 1 file, 2 lines changed                        │
│                                                          │
│  [A] Approve   [D] Deny   [V] View Full Diff   [Q] Quit│
╰─────────────────────────────────────────────────────────╯
```

### **CLI Commands**

```bash
# Execute read-only command
wm exec rg "TODO" --json

# Execute with write mode (requires approval)
wm exec --write sd "old" "new" src/

# Start TUI approver
wm ui

# View execution history
wm exec history

# View specific run
wm exec show exec_xyz789

# Benchmark code-mode vs prompt-mode
wm bench compare
```

---

## 📚 **SDK Design**

### **Python SDK**

```python
from whitemagic import TerminalExecutor

# Initialize
executor = TerminalExecutor(
    api_key="wm_prod_xxx",
    profile="agent"
)

# Read operation (auto-approved)
result = await executor.read(
    cmd="rg",
    args=["TODO", "--json"],
    cwd="/workspace"
)
print(result.stdout)

# Write operation (requires approval)
patch = await executor.write(
    cmd="sd",
    args=["old_pattern", "new_pattern", "src/"],
    cwd="/workspace"
)

if patch.requires_approval:
    print(f"Patch preview: {patch.diff}")
    approved = await patch.wait_for_approval()
    
    if approved:
        result = await patch.apply()
        print(f"Applied: {result.commit_sha}")
```

### **JavaScript SDK**

```typescript
import { TerminalExecutor } from 'whitemagic-js';

const executor = new TerminalExecutor({
  apiKey: 'wm_prod_xxx',
  profile: 'agent'
});

// Read operation
const result = await executor.read({
  cmd: 'rg',
  args: ['TODO', '--json'],
  cwd: '/workspace'
});

// Write with approval
const patch = await executor.write({
  cmd: 'sd',
  args: ['old', 'new', 'src/'],
  cwd: '/workspace'
});

if (patch.requiresApproval) {
  console.log(`Patch preview:\n${patch.diff}`);
  const approved = await patch.waitForApproval();
  
  if (approved) {
    const result = await patch.apply();
    console.log(`Applied: ${result.commitSha}`);
  }
}
```

---

## 🤖 **Agent Templates**

### **1. Repo Maintenance Bot**

```python
# Template: Auto-fix TODOs
async def fix_todos_bot():
    # Find all TODOs
    result = await executor.read("rg", ["TODO:", "--json"])
    todos = json.loads(result.stdout)
    
    for todo in todos[:5]:  # Limit to 5
        # Ask AI for fix
        fix = await ai.generate_fix(todo)
        
        # Apply fix
        patch = await executor.write("sd", [
            todo.text,
            fix,
            todo.file
        ])
        
        # Auto-approve if confidence > 0.9
        if fix.confidence > 0.9:
            await patch.approve()
        else:
            await patch.request_human_review()
```

### **2. Test Generator**

```python
# Template: Generate tests for untested functions
async def generate_tests():
    # Find Python files
    files = await executor.read("fd", ["-e", "py", "src/"])
    
    for file in files.stdout.split():
        # Check test coverage
        coverage = await executor.read("coverage", ["report", file])
        
        if coverage.uncovered > 0:
            # Generate tests
            tests = await ai.generate_tests(file)
            
            # Write test file
            patch = await executor.write("tee", [
                f"tests/test_{file.name}"
            ], stdin=tests)
            
            # Run tests
            result = await executor.read("pytest", [patch.file])
            
            if result.exit_code == 0:
                await patch.approve()
```

---

## 📊 **wm bench Utility**

Compare code-mode vs prompt-mode approaches.

```bash
$ wm bench compare \
    --task "find and fix TODOs" \
    --iterations 10 \
    --output results.json

╭───────────────────────────────────────────────╮
│  WhiteMagic Benchmark Results                 │
├───────────────────────────────────────────────┤
│                                                │
│  Task: Find and fix TODOs                     │
│  Iterations: 10                               │
│                                                │
│  Metric            Code-Mode    Prompt-Mode   │
│  ─────────────────────────────────────────────│
│  Avg Time          2.3s         8.7s          │
│  Avg Tokens        450          2,100         │
│  Success Rate      90%          70%           │
│  Cost per Run      $0.003       $0.012        │
│                                                │
│  Winner: Code-Mode (4x faster, 5x cheaper)    │
╰───────────────────────────────────────────────╯
```

---

## 🎯 **Implementation Phases**

### **Week 1: Core Execution**
- [ ] POST /exec API with read-only mode
- [ ] OCI containerized runner (runc/containerd)
- [ ] Command allowlist with profiles
- [ ] Basic audit logging
- [ ] MCP exec_read tool
- [ ] Correlation IDs

**Deliverable**: Can run safe read commands via API

### **Week 2: Write Mode + Safety**
- [ ] Patch generation from file changes
- [ ] Patch preview endpoint
- [ ] MCP exec_write tool
- [ ] TUI approver (Rich/Textual)
- [ ] Idempotency keys
- [ ] Network isolation flags
- [ ] Auto-commit approved patches

**Deliverable**: Write mode with approval flow working

### **Week 3: Developer Experience**
- [ ] whitemagic-js SDK
- [ ] whitemagic-py SDK
- [ ] Typed interfaces + documentation
- [ ] Agent templates (3-5 examples)
- [ ] Allowlist profile system
- [ ] wm bench utility

**Deliverable**: SDKs + templates reduce prompt complexity

### **Week 4: Safety + Tooling**
- [ ] Security audit (internal + external)
- [ ] Fuzzing + edge case testing
- [ ] VS Code/Cursor snippets
- [ ] Cost/resource monitoring
- [ ] Error handling + retries
- [ ] Rate limiting

**Deliverable**: Production-ready security + tooling

### **Week 5: Polish + Ease-of-Use**
- [ ] wm init wizard
- [ ] wm tui enhanced browser
- [ ] Importers (Obsidian, MD, JSONL)
- [ ] Backup/restore integration
- [ ] Video tutorials (3-5 videos)
- [ ] Complete documentation

**Deliverable**: Polished, production-ready feature

---

## 🚀 **Success Metrics**

### **Technical**
- [ ] <200ms API latency (p95)
- [ ] 99.9% uptime for execution service
- [ ] Zero security incidents in first 3 months
- [ ] <1% patch approval rejection rate

### **User Experience**
- [ ] Agent templates reduce prompt tokens by >50%
- [ ] Code-mode 3x faster than prompt-mode (wm bench)
- [ ] Approval flow <10 seconds end-to-end
- [ ] 80% of users prefer Terminal Tool over pure prompts

### **Adoption**
- [ ] 1,000+ successful executions in first month
- [ ] 50+ agent templates created by community
- [ ] 3+ framework integrations (LangChain, AutoGPT, etc.)
- [ ] Featured in AI agent benchmarks (e.g., SWE-bench)

---

## 🔮 **Future Enhancements**

### **Phase 2 (After Initial Release)**
- WASM-based sandboxing (lighter than OCI)
- GPU access for ML workloads
- Distributed execution (multi-node)
- Visual diff viewer in web UI
- Replay/debug mode for runs
- Cost optimization (caching, deduplication)

### **Phase 3 (Long-term)**
- Multi-agent orchestration
- Shared workspace for agent teams
- Workflow definitions (DAGs)
- Integration with CI/CD (GitHub Actions, GitLab CI)
- Marketplace for agent templates
- Enterprise SSO + RBAC

---

## 📖 **References**

- [Anthropic: Claude Computer Control](https://www.anthropic.com/news/claude-computer-control)
- [OpenAI: Code Interpreter](https://openai.com/blog/chatgpt-code-interpreter)
- [LangChain: Agents & Tools](https://python.langchain.com/docs/modules/agents/)
- [OCI Runtime Spec](https://github.com/opencontainers/runtime-spec)
- [SWE-bench: AI Coding Benchmark](https://www.swebench.com/)

---

**Status**: ✅ Design Complete  
**Next**: Begin implementation in Phase 2C (after Semantic Search)  
**Owner**: WhiteMagic Core Team  
**Stakeholders**: AI researchers, DevOps engineers, agent developers
