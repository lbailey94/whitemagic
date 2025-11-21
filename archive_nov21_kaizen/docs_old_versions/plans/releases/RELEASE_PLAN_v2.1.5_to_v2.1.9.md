# Release Plan: v2.2.1 → v2.1.9
## Local-First Feature Completion Before Monetization

**Date**: November 14, 2025  
**Strategy**: Ship compelling, easy-to-use, local, secure, **free** version  
**Monetization**: Delayed to v2.2.0+

---

## 🎯 Strategic Objectives

### Why This Approach?

1. **Adoption First**: Build user base with irresistible free version
2. **Feature Complete**: Deliver all core capabilities promised in vision
3. **Local-First Philosophy**: Prove WhiteMagic works perfectly without cloud
4. **Security & Trust**: Establish reputation before asking for money
5. **Community Building**: Get 1,000+ users providing feedback

### Monetization Deferred Until

- **v2.2.0+**: Cloud sync, team features, Stripe integration
- **Goal**: 1,000+ active local users before launching paid tiers
- **Timing**: Q1 2026

---

## 📦 Current State Assessment

### ✅ Fully Built (But Some Disabled/Untested)

| Feature | Status | Location | Tests | Notes |
|---------|--------|----------|-------|-------|
| **Terminal Tool** | ✅ Built, ⚠️ Disabled | `whitemagic/terminal/` | ✅ `test_terminal.py` | Requires `WM_ENABLE_EXEC_API=true` |
| **Semantic Search** | ✅ Built, ✅ Wired | `whitemagic/search/semantic.py` | ✅ `test_semantic_search.py` | API route: `/api/v1/search/semantic` |
| **Embeddings** | ✅ Built | `whitemagic/embeddings/` | ✅ Tested | OpenAI + Local providers |
| **Core Memory** | ✅ Production | `whitemagic/core.py` | ✅ 196 tests | Solid foundation |
| **REST API** | ✅ Production | `whitemagic/api/` | ✅ Tested | Auth, rate limits, quotas |
| **MCP Server** | ✅ Production | `whitemagic-mcp/` | ✅ 27 tests | IDE integration works |

### 🚧 Needs Implementation

| Feature | Priority | Complexity | Rationale |
|---------|----------|------------|-----------|
| **Nested Learning** | High | Medium | Adaptive memory promotion based on surprise/reference patterns |
| **Neuron Spectrum** | Medium | Medium | Multi-speed memory tiers (scratch → episode → project → canon) |
| **Agent Templates** | High | Low | Pre-built workflows showcasing Terminal Tool |
| **Onboarding Flow** | High | Low | `wm init` wizard for new users |
| **Memory Browser TUI** | Medium | Medium | Interactive terminal UI for browsing/searching |
| **CLI Enhancements** | Medium | Low | Better UX, tab completion, colors |

### ❌ Explicitly Deferred

| Feature | Target Version | Reason |
|---------|----------------|--------|
| Stripe Integration | v2.2.0 | Monetization later |
| Cloud Sync | v2.2.0 | Local-first focus |
| Team Workspaces | v2.3.0 | Single-user first |
| Whop Integration | v2.2.0 | After user base |

---

## 🚀 Release Schedule

### **v2.2.1 - Terminal Tool GA** (November 14-15, 2025)

**Theme**: Safe, Powerful Code-Mode Execution

**Goals**:
- Enable Terminal Tool by default (with safety guardrails)
- Polish UX and documentation
- Ship agent templates demonstrating 50-100x efficiency

**Changes**:

#### 1. Enable Terminal Tool
```python
# whitemagic/api/app.py
# Change from:
EXEC_API_ENABLED = os.getenv("WM_ENABLE_EXEC_API", "false").lower() == "true"

# To:
EXEC_API_ENABLED = os.getenv("WM_ENABLE_EXEC_API", "true").lower() == "true"
```

**Safety Measures**:
- Default to `PROD` profile (read-only allowlist)
- Require explicit opt-in for write mode
- Document security model clearly
- Add warning on first use

#### 2. CLI Commands
```bash
# New commands:
wm exec <command> [args]           # Execute read-only command
wm exec --write <command> [args]   # Execute with approval (requires --write flag)
wm exec history                     # View execution history
wm exec show <run_id>              # View specific execution details
```

#### 3. Agent Templates
Create `templates/` directory with:
- `find_todos.py` - Find and optionally fix TODOs
- `test_coverage.py` - Find untested code, generate tests
- `doc_updater.py` - Keep docs in sync with code
- `refactor_helper.py` - Suggest refactorings based on patterns
- `security_scanner.py` - Basic security checks

#### 4. Documentation
- `docs/TERMINAL_TOOL_USAGE.md` - Already exists, verify accuracy
- `docs/AGENT_TEMPLATES.md` - New guide with examples
- Update `README.md` with Terminal Tool section
- Add security FAQ

**Testing**:
- [ ] Run `pytest tests/test_terminal.py -v`
- [ ] Manual test: `wm exec ls -la`
- [ ] Manual test: `wm exec --write touch test.txt` (with approval)
- [ ] Test all agent templates
- [ ] Security audit (allowlist verification)

**Release Criteria**:
- [ ] All Terminal tests passing
- [ ] Agent templates working
- [ ] Security review complete
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

**Timeline**: 1-2 days

---

### **v2.1.6 - Semantic Search Activation** (November 16-18, 2025)

**Theme**: Intelligent Memory Retrieval

**Goals**:
- Make semantic search easy to use
- Support local embeddings (privacy-first)
- CLI integration for power users

**Changes**:

#### 1. CLI Integration
```bash
# New commands:
wm search --mode semantic "query"       # Semantic search
wm search --mode hybrid "query"         # Keyword + semantic
wm search --setup-embeddings            # One-time setup wizard
```

#### 2. Embedding Setup Wizard
```bash
$ wm search --setup-embeddings

WhiteMagic Semantic Search Setup
=================================

Choose embedding provider:
1. Local (sentence-transformers) - Privacy-first, no API key needed
2. OpenAI (text-embedding-3-small) - Best quality, requires API key
3. Skip for now

[1/2/3]: 1

Installing sentence-transformers locally...
✓ Model downloaded (340MB)
✓ Configuration saved

You can now use semantic search:
  wm search --mode semantic "your query"
```

#### 3. Configuration
```yaml
# ~/.whitemagic/config.yaml (new file)
embeddings:
  provider: local  # or "openai"
  model: all-MiniLM-L6-v2
  cache_enabled: true
  cache_path: ~/.whitemagic/embeddings_cache/

search:
  default_mode: hybrid
  semantic_threshold: 0.7
  keyword_weight: 0.3
  semantic_weight: 0.7
```

#### 4. MCP Integration
```typescript
// Add to whitemagic-mcp/src/index.ts
{
  name: "search_semantic",
  description: "Semantic search with embeddings",
  inputSchema: {
    query: { type: "string" },
    mode: { type: "string", enum: ["keyword", "semantic", "hybrid"] },
    k: { type: "number", default: 10 }
  }
}
```

**Testing**:
- [ ] Run `pytest tests/test_semantic_search.py -v`
- [ ] Test local embeddings installation
- [ ] Test OpenAI embeddings (with key)
- [ ] Test hybrid search ranking
- [ ] CLI search commands
- [ ] MCP semantic search tool

**Release Criteria**:
- [ ] All semantic search tests passing
- [ ] Local embeddings working without API key
- [ ] Setup wizard complete
- [ ] MCP tool integrated
- [ ] Documentation complete

**Timeline**: 2-3 days

---

### **v2.1.7 - Nested Learning & Adaptive Promotion** (November 19-23, 2025)

**Theme**: Intelligent Memory Hygiene

**Goals**:
- Implement surprise-weighted promotion
- Multi-speed memory tiers
- Automatic consolidation policies

**Theory Foundation**:
From VISION.md and Google's Nested Learning research:
- **Fast-changing memories** (working, scratch) - high update rate
- **Medium memories** (episodic, session) - moderate update rate  
- **Slow memories** (semantic, canonical) - rare updates
- **Promotion triggers**: Surprise, frequency, explicit user marking

**Implementation**:

#### 1. New Memory Metadata
```yaml
# Memory frontmatter additions:
---
id: mem_abc123
# ... existing fields ...
learning:
  surprise_score: 0.85      # How unexpected was this information?
  reference_count: 5         # Times accessed/referenced
  last_accessed: "2025-11-14T12:00:00Z"
  promotion_candidate: true  # Flagged for promotion
  decay_rate: 0.1           # How quickly this loses relevance
---
```

#### 2. Surprise Scoring Algorithm
```python
# whitemagic/learning/surprise.py (new module)

class SurpriseScorer:
    """Calculate surprise scores for memories."""
    
    def score_memory(self, memory: Memory, context: MemoryContext) -> float:
        """
        Score ranges 0.0 to 1.0:
        - 0.0-0.3: Expected information
        - 0.3-0.7: Moderately surprising
        - 0.7-1.0: Highly surprising (promote!)
        
        Factors:
        - Novelty: Is this new information?
        - Contradiction: Does it conflict with existing memories?
        - Importance: Did user explicitly mark it?
        - Utility: How often is it referenced?
        """
        pass
```

#### 3. Promotion Policies
```python
# whitemagic/learning/promotion.py (new module)

PROMOTION_POLICIES = {
    "scratch_to_episode": {
        "triggers": [
            {"type": "surprise", "threshold": 0.7},
            {"type": "references", "threshold": 3},
            {"type": "user_marked", "value": True}
        ],
        "age_min_hours": 1,
        "age_max_hours": 48
    },
    "episode_to_project": {
        "triggers": [
            {"type": "surprise", "threshold": 0.8},
            {"type": "references", "threshold": 5},
            {"type": "consolidation", "value": True}
        ],
        "age_min_days": 2,
        "age_max_days": 30
    },
    "project_to_canon": {
        "triggers": [
            {"type": "surprise", "threshold": 0.9},
            {"type": "references", "threshold": 10},
            {"type": "explicit_promotion", "required": True}
        ],
        "age_min_days": 7
    }
}
```

#### 4. Memory Tiers
```python
# Extend MemoryManager with tier support
MEMORY_TIERS = {
    "scratch": {
        "ttl_hours": 24,
        "auto_consolidate": True,
        "promotion_check": "hourly"
    },
    "episode": {
        "ttl_days": 30,
        "auto_consolidate": True,
        "promotion_check": "daily"
    },
    "project": {
        "ttl_days": 365,
        "auto_consolidate": False,
        "promotion_check": "weekly"
    },
    "canon": {
        "ttl_days": None,  # Permanent
        "auto_consolidate": False,
        "promotion_check": "never"
    }
}
```

#### 5. CLI Commands
```bash
# New commands:
wm promote <memory_id> --to=long_term    # Manual promotion
wm analyze-promotion                      # Show promotion candidates
wm consolidate --policy=aggressive        # Apply promotion policies
wm learning stats                         # Show learning metrics
```

**Testing**:
- [ ] Create surprise scoring tests
- [ ] Test promotion policies
- [ ] Test multi-tier consolidation
- [ ] Test decay/aging logic
- [ ] Integration test with full lifecycle

**Release Criteria**:
- [ ] Surprise scoring working
- [ ] Promotion policies triggering correctly
- [ ] CLI commands functional
- [ ] Documentation explaining theory
- [ ] Performance acceptable (no slowdown)

**Timeline**: 4-5 days

---

### **v2.1.8 - Onboarding & UX Polish** (November 24-27, 2025)

**Theme**: Delightful First Experience

**Goals**:
- Make setup effortless
- Interactive tutorials
- Beautiful CLI output
- Error messages that help

**Changes**:

#### 1. `wm init` Wizard
```bash
$ wm init

╔════════════════════════════════════════════╗
║   Welcome to WhiteMagic Memory OS          ║
║   Let's set up your memory system          ║
╚════════════════════════════════════════════╝

📁 Where should we store your memories?
   [1] ~/.whitemagic/ (recommended)
   [2] ./memory/ (current directory)
   [3] Custom path

Choice [1-3]: 1

🔍 Enable semantic search?
   Local embeddings (privacy-first, no API key)
   
   [Y/n]: Y

   ⏳ Downloading model (340MB)...
   ✓ Model ready

🚀 Enable Terminal Tool?
   Execute commands safely (read-only by default)
   
   [Y/n]: Y

✨ Setup complete! Try these commands:

   wm create "My first memory" --content "Hello!"
   wm search "first"
   wm context --tier 1
   
Need help? Run: wm tutorial
```

#### 2. Interactive Tutorial
```bash
$ wm tutorial

╔════════════════════════════════════════════╗
║  WhiteMagic Tutorial (5 minutes)           ║
╚════════════════════════════════════════════╝

Step 1: Create Your First Memory
─────────────────────────────────
We'll create a short-term memory about this tutorial.

  $ wm create "Tutorial Memory" \\
      --content "I learned how to use WhiteMagic!" \\
      --tags tutorial,learning

[Press ENTER to run this command]

✓ Memory created: 20251114_tutorial_memory.md

You can view it:
  $ wm get 20251114_tutorial_memory.md
  $ cat memory/short_term/20251114_tutorial_memory.md

[Continue? Y/n]
```

#### 3. Beautiful CLI Output
```bash
# Use Rich library for:
- Color-coded output
- Progress bars
- Tables for list/search results
- Syntax highlighting for memory content
- Emoji status indicators
```

#### 4. Helpful Error Messages
```python
# Before:
# Error: Memory not found

# After:
╭─ Error: Memory Not Found ────────────────────╮
│                                                │
│ Could not find: 20251114_notes.md             │
│                                                │
│ Did you mean one of these?                    │
│   • 20251114_tutorial_memory.md               │
│   • 20251113_api_notes.md                     │
│                                                │
│ Search for memories:                          │
│   wm search "notes"                           │
│                                                │
│ List all memories:                            │
│   wm list                                     │
╰────────────────────────────────────────────────╯
```

#### 5. Shell Completions
```bash
# Generate completions for bash, zsh, fish
wm --install-completion bash
wm --install-completion zsh
```

**Testing**:
- [ ] Run `wm init` in clean environment
- [ ] Complete `wm tutorial` end-to-end
- [ ] Test all error messages
- [ ] Verify completions work
- [ ] UX review with fresh user

**Release Criteria**:
- [ ] Init wizard works perfectly
- [ ] Tutorial is clear and helpful
- [ ] CLI output is beautiful
- [ ] Error messages are actionable
- [ ] Shell completions installed

**Timeline**: 3-4 days

---

### **v2.1.9 - Memory Browser TUI & Polish** (November 28 - December 1, 2025)

**Theme**: Power User Tools

**Goals**:
- Interactive terminal UI for browsing
- Keyboard-driven workflow
- Performance optimizations
- Final polish before 2.2

**Changes**:

#### 1. Memory Browser TUI
```bash
$ wm browse

╔═══════════════════════════════════════════════════════════════╗
║  WhiteMagic Memory Browser                    [?] Help  [Q] Quit ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                 ║
║  📂 Short-Term (12)          🔍 Search: _                      ║
║  ├─ 20251114_terminal_tool.md        [tags: code, exec]       ║
║  ├─ 20251114_semantic_search.md      [tags: search, ai]       ║
║  ├─ 20251113_api_design.md           [tags: api, design]      ║
║  └─ ...                                                         ║
║                                                                 ║
║  📂 Long-Term (8)                                              ║
║  ├─ project_requirements.md          [tags: project]          ║
║  ├─ architecture_decisions.md        [tags: architecture]     ║
║  └─ ...                                                         ║
║                                                                 ║
║─────────────────────────────────────────────────────────────────║
║  Preview: 20251114_terminal_tool.md                           ║
║  Created: 2025-11-14 12:00  |  Updated: 2025-11-14 14:30     ║
║  Tags: code, exec, terminal                                    ║
║                                                                 ║
║  # Terminal Tool Implementation                                ║
║                                                                 ║
║  Implemented safe command execution with approval workflow...  ║
║                                                                 ║
║─────────────────────────────────────────────────────────────────║
║  [↑↓] Navigate  [Enter] Open  [e] Edit  [d] Delete  [/] Search ║
╚═══════════════════════════════════════════════════════════════╝
```

#### 2. Keyboard Shortcuts
```
Navigation:
  ↑/↓, j/k     - Move selection
  Enter        - Open memory in detail view
  Backspace    - Go back

Actions:
  e            - Edit memory in $EDITOR
  d            - Delete (with confirmation)
  p            - Promote to long-term
  t            - Edit tags
  /            - Search mode
  ?            - Help
  q            - Quit

Views:
  1            - List view (default)
  2            - Tag cloud view
  3            - Timeline view
  4            - Graph view (connections)
```

#### 3. Performance Optimizations
```python
# Optimize core operations:
- Lazy loading of memory content
- Index caching with invalidation
- Parallel file I/O where safe
- Memory-mapped file reading for large memories
- Debounced search (wait for typing to finish)

Target metrics:
- List 1000 memories: <50ms
- Search 1000 memories: <100ms
- Open memory: <10ms
- TUI responsiveness: 60fps
```

#### 4. Final Polish
- [ ] Fix any reported bugs from v2.2.1-2.1.8
- [ ] Update all documentation
- [ ] Create video tutorials (3-5 short videos)
- [ ] Write blog post: "WhiteMagic v2.1: Feature Complete"
- [ ] Prepare for v2.2 launch

**Testing**:
- [ ] TUI tested on Linux, macOS
- [ ] Performance benchmarks met
- [ ] No memory leaks
- [ ] Stress test with 10k+ memories
- [ ] Full regression test suite

**Release Criteria**:
- [ ] TUI is fast and responsive
- [ ] All keyboard shortcuts work
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Ready for public launch

**Timeline**: 3-4 days

---

## 📊 Success Metrics

### Technical Metrics

| Metric | Current | v2.1.9 Target |
|--------|---------|---------------|
| Test Coverage | 93% | 95% |
| Passing Tests | 223 | 250+ |
| CLI Commands | 12 | 20+ |
| Agent Templates | 0 | 5+ |
| Documentation Pages | 45 | 55+ |
| Performance (list 1k) | ~100ms | <50ms |

### User Experience Metrics

| Metric | Measurement | Target |
|--------|-------------|--------|
| Time to First Memory | From install to first `wm create` | <5 minutes |
| Setup Success Rate | Users completing `wm init` | >95% |
| Tutorial Completion | Users finishing `wm tutorial` | >80% |
| Feature Discovery | Users trying semantic search | >60% |
| Terminal Tool Usage | Users running `wm exec` | >40% |

### Adoption Metrics (Post-Launch)

| Metric | Month 1 | Month 3 |
|--------|---------|---------|
| GitHub Stars | 100 | 500 |
| PyPI Downloads | 500 | 5,000 |
| MCP Installs | 200 | 2,000 |
| Active Users | 50 | 500 |
| Community PRs | 5 | 20 |

---

## 🚢 Launch Strategy (Post v2.1.9)

### Week 1: Soft Launch
- Blog post on personal site
- X/Twitter announcement
- Direct outreach to 20-30 dev friends
- Post in niche communities (r/LocalLLaMA, AI Discord servers)

### Week 2: Product Hunt
- Prepare assets (logo, screenshots, demo video)
- Write compelling description
- Schedule for Tuesday morning
- Engage with comments all day

### Week 3: Show HN
- Write technical deep-dive post
- Focus on architecture and philosophy
- Be responsive to questions
- Highlight local-first + Terminal Tool

### Week 4: Content Marketing
- 3-5 YouTube tutorials
- Blog posts on Medium/Dev.to
- Integration guides (LangChain, etc.)
- Framework comparison content

---

## 🔄 Post-v2.1.9: Transition to v2.2

### v2.2.0 Monetization (Q1 2026)

**Only after**:
- [ ] 1,000+ users on local version
- [ ] Community established (Discord active)
- [ ] Feature requests prioritized
- [ ] User testimonials collected

**Then implement**:
- Stripe integration
- Cloud sync
- Usage dashboard
- Team workspaces preview

---

## 📋 Immediate Actions (v2.2.1 Tonight)

### High Priority (Ship Tonight)

1. **Enable Terminal Tool**
   - [ ] Change default: `WM_ENABLE_EXEC_API=true`
   - [ ] Add safety warnings
   - [ ] Test basic exec commands
   - [ ] Update docs with security notes

2. **Quick Wins**
   - [ ] Verify semantic search works (it's already wired!)
   - [ ] Test one agent template (find_todos.py)
   - [ ] Update README.md with feature highlights

3. **Documentation**
   - [ ] CHANGELOG.md entry for v2.2.1
   - [ ] Update VERSION file
   - [ ] Quick security FAQ

### Medium Priority (This Week)

4. **Semantic Search Polish** (v2.1.6)
   - [ ] CLI integration
   - [ ] Setup wizard
   - [ ] MCP tool addition

5. **Testing**
   - [ ] Run full test suite
   - [ ] Fix any broken tests
   - [ ] Add missing test coverage

### Can Wait (Next Week)

6. **Nested Learning** (v2.1.7)
7. **Onboarding Wizard** (v2.1.8)
8. **TUI Browser** (v2.1.9)

---

## 🎯 Key Decisions

### Decisions Made

✅ **Local-first until 1,000 users**: Adoption > monetization  
✅ **Terminal Tool enabled**: Core differentiator  
✅ **Semantic search included**: Already built, wire it up  
✅ **Nested learning in 2.1.x**: Fits vision perfectly  
✅ **Beautiful UX matters**: Onboarding wizard + TUI  

### Decisions Deferred

❌ **Stripe**: Wait until v2.2.0  
❌ **Cloud sync**: Not needed for local-first  
❌ **Team features**: Single-user first  
❌ **Advanced analytics**: Nice-to-have, not critical  

---

## 🚀 Let's Ship!

**Next Steps**:
1. Review this plan
2. Ship v2.2.1 tonight (Terminal Tool)
3. Execute progressive releases v2.1.6-2.1.9
4. Launch publicly by December 1, 2025
5. Build to 1,000 users before monetization

**Philosophy**:
> "Build something people want so badly, they'll pay for the cloud version just to support you."

Local version is free, powerful, and complete. Cloud version (v2.2+) is convenience + team features for those who want it.

---

**Ready to ship v2.2.1?** Let's enable that Terminal Tool! 🎉
