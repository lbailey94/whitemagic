# MCP Tool Enhancements for v2.2.7

**Date**: November 16, 2025  
**Purpose**: Expand MCP server capabilities for improved AI workflows  
**Status**: Design Phase

---

## 🎯 Current MCP Tools (16 total)

### Memory Management (9 tools)
1. `create_memory` - Create new memory
2. `read_memory` - Read memory content
3. `update_memory` - Update existing memory
4. `delete_memory` - Delete/archive memory
5. `restore_memory` - Restore archived memory
6. `list_memories` - List all memories
7. `search_memories` - Search by query/tags
8. `consolidate` - Archive old memories
9. `get_context` - Generate tiered context

### Optimizations (3 tools)
10. `fast_read_memory` - 10-100x faster reads
11. `batch_read_memories` - Batch operations
12. `clear_memory_cache` - Cache management

### Metrics (2 tools)
13. `track_metric` - Record metric
14. `get_metrics_summary` - Retrieve metrics

### Resources (4 types)
- `memory://short_term` - Short-term memories
- `memory://long_term` - Long-term knowledge
- `memory://stats` - System statistics
- `memory://tags` - Tag directory

---

## 🚀 Proposed New Tools (20 additions)

### Category 1: Parallel Operations (5 tools)

#### `parallel_search`
**Purpose**: Run multiple searches simultaneously

```typescript
{
  name: 'parallel_search',
  description: '⚡ Search multiple queries in parallel (5-10x faster)',
  inputSchema: {
    type: 'object',
    properties: {
      queries: {
        type: 'array',
        items: { type: 'string' },
        description: 'List of search queries',
        minItems: 2,
        maxItems: 20
      },
      max_concurrent: {
        type: 'number',
        default: 8,
        description: 'Max parallel searches'
      },
      deduplicate: {
        type: 'boolean',
        default: true,
        description: 'Remove duplicate results'
      }
    },
    required: ['queries']
  }
}
```

**Use Case**: "Search for 'v2.2.6', 'deployment', and 'bugs' simultaneously"

#### `batch_create_memories`
**Purpose**: Create multiple memories in one operation

```typescript
{
  name: 'batch_create_memories',
  description: '⚡ Create multiple memories atomically',
  inputSchema: {
    type: 'object',
    properties: {
      memories: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            content: { type: 'string' },
            type: { type: 'string', enum: ['short_term', 'long_term'] },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['title', 'content']
        }
      },
      atomic: {
        type: 'boolean',
        default: true,
        description: 'All succeed or all fail'
      }
    },
    required: ['memories']
  }
}
```

**Use Case**: "Create 5 related memories for different components"

#### `parallel_update_memories`
**Purpose**: Update multiple memories simultaneously

```typescript
{
  name: 'parallel_update_memories',
  description: '⚡ Update multiple memories in parallel',
  inputSchema: {
    type: 'object',
    properties: {
      updates: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            filename: { type: 'string' },
            operations: {
              type: 'object',
              properties: {
                add_tags: { type: 'array', items: { type: 'string' } },
                remove_tags: { type: 'array', items: { type: 'string' } },
                set_content: { type: 'string' },
                append_content: { type: 'string' }
              }
            }
          },
          required: ['filename', 'operations']
        }
      }
    },
    required: ['updates']
  }
}
```

**Use Case**: "Add 'reviewed' tag to 10 memories at once"

#### `smart_consolidate`
**Purpose**: Intelligent consolidation with grouping

```typescript
{
  name: 'smart_consolidate',
  description: 'Consolidate related memories by topic/date/project',
  inputSchema: {
    type: 'object',
    properties: {
      strategy: {
        type: 'string',
        enum: ['by_topic', 'by_date', 'by_project', 'by_tags', 'auto'],
        default: 'auto',
        description: 'Consolidation strategy'
      },
      min_similarity: {
        type: 'number',
        minimum: 0,
        maximum: 1,
        default: 0.7,
        description: 'Minimum similarity for grouping (0-1)'
      },
      max_group_size: {
        type: 'number',
        default: 5,
        description: 'Max memories per group'
      },
      dry_run: {
        type: 'boolean',
        default: true
      }
    }
  }
}
```

**Use Case**: "Consolidate all v2.2.6 memories by topic"

#### `parallel_file_operations`
**Purpose**: Batch file operations

```typescript
{
  name: 'parallel_file_operations',
  description: '⚡ Read/write multiple files in parallel',
  inputSchema: {
    type: 'object',
    properties: {
      operations: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            type: { type: 'string', enum: ['read', 'write', 'append'] },
            path: { type: 'string' },
            content: { type: 'string' }
          },
          required: ['type', 'path']
        }
      },
      max_workers: {
        type: 'number',
        default: 32
      }
    },
    required: ['operations']
  }
}
```

**Use Case**: "Read 50 documentation files in parallel"

---

### Category 2: Session Management (5 tools)

#### `create_session`
**Purpose**: Start a work session with context

```typescript
{
  name: 'create_session',
  description: 'Create new work session with automatic state management',
  inputSchema: {
    type: 'object',
    properties: {
      name: { 
        type: 'string',
        description: 'Session name (e.g., "v2.2.7-cleanup")'
      },
      goals: {
        type: 'array',
        items: { type: 'string' },
        description: 'Session goals/objectives'
      },
      context_tier: {
        type: 'number',
        enum: [0, 1, 2],
        default: 1,
        description: 'Initial context loading tier'
      },
      tags: {
        type: 'array',
        items: { type: 'string' },
        description: 'Session tags'
      },
      auto_checkpoint: {
        type: 'boolean',
        default: true,
        description: 'Auto-checkpoint every 30 minutes'
      }
    },
    required: ['name']
  }
}
```

**Use Case**: "Start v2.2.7 development session"

#### `checkpoint_session`
**Purpose**: Save session state

```typescript
{
  name: 'checkpoint_session',
  description: 'Save current session state for resume',
  inputSchema: {
    type: 'object',
    properties: {
      session_id: { type: 'string' },
      checkpoint_name: { type: 'string' },
      include_metrics: { type: 'boolean', default: true },
      include_context: { type: 'boolean', default: true }
    },
    required: ['session_id']
  }
}
```

**Use Case**: "Save progress before taking a break"

#### `resume_session`
**Purpose**: Resume previous session

```typescript
{
  name: 'resume_session',
  description: 'Resume session with full context restoration',
  inputSchema: {
    type: 'object',
    properties: {
      session_id: { type: 'string' },
      checkpoint_name: { type: 'string' },
      load_tier: {
        type: 'number',
        enum: [0, 1, 2],
        default: 1
      }
    },
    required: ['session_id']
  }
}
```

**Use Case**: "Resume yesterday's work"

#### `list_sessions`
**Purpose**: View all sessions

```typescript
{
  name: 'list_sessions',
  description: 'List all sessions with status',
  inputSchema: {
    type: 'object',
    properties: {
      status: {
        type: 'string',
        enum: ['active', 'paused', 'completed', 'all'],
        default: 'all'
      },
      sort_by: {
        type: 'string',
        enum: ['created', 'modified', 'name'],
        default: 'modified'
      },
      limit: { type: 'number', default: 20 }
    }
  }
}
```

**Use Case**: "Show my recent sessions"

#### `end_session`
**Purpose**: Properly close session

```typescript
{
  name: 'end_session',
  description: 'End session with final consolidation',
  inputSchema: {
    type: 'object',
    properties: {
      session_id: { type: 'string' },
      create_summary: { type: 'boolean', default: true },
      consolidate_memories: { type: 'boolean', default: true },
      archive_session: { type: 'boolean', default: false }
    },
    required: ['session_id']
  }
}
```

**Use Case**: "Complete session and summarize"

---

### Category 3: Analysis & Insights (5 tools)

#### `analyze_memory_graph`
**Purpose**: Discover memory connections

```typescript
{
  name: 'analyze_memory_graph',
  description: 'Analyze connections and relationships between memories',
  inputSchema: {
    type: 'object',
    properties: {
      start_memory: { type: 'string', description: 'Starting point filename' },
      depth: { 
        type: 'number',
        default: 2,
        minimum: 1,
        maximum: 5,
        description: 'Graph traversal depth'
      },
      min_strength: {
        type: 'number',
        default: 0.5,
        description: 'Minimum connection strength (0-1)'
      },
      relationship_types: {
        type: 'array',
        items: { 
          type: 'string',
          enum: ['temporal', 'topical', 'reference', 'all']
        },
        default: ['all']
      }
    }
  }
}
```

**Use Case**: "Find all memories related to v2.2.6 release"

#### `find_patterns`
**Purpose**: Discover recurring patterns

```typescript
{
  name: 'find_patterns',
  description: 'Discover recurring patterns across memories',
  inputSchema: {
    type: 'object',
    properties: {
      time_range: {
        type: 'string',
        description: 'e.g., "last_7_days", "last_month", "2025-11"'
      },
      pattern_types: {
        type: 'array',
        items: {
          type: 'string',
          enum: ['code', 'workflow', 'decision', 'problem', 'solution']
        }
      },
      min_occurrences: {
        type: 'number',
        default: 3,
        description: 'Minimum pattern occurrences'
      }
    }
  }
}
```

**Use Case**: "Find common problems in last month"

#### `get_recommendations`
**Purpose**: AI-powered suggestions

```typescript
{
  name: 'get_recommendations',
  description: 'Get AI recommendations based on memory analysis',
  inputSchema: {
    type: 'object',
    properties: {
      context: {
        type: 'string',
        description: 'Current task/project context'
      },
      categories: {
        type: 'array',
        items: {
          type: 'string',
          enum: [
            'consolidation',
            'next_steps',
            'related_memories',
            'optimizations',
            'warnings'
          ]
        },
        default: ['next_steps', 'related_memories']
      },
      limit: { type: 'number', default: 5 }
    },
    required: ['context']
  }
}
```

**Use Case**: "What should I work on next for v2.2.7?"

#### `compare_memories`
**Purpose**: Compare multiple memories

```typescript
{
  name: 'compare_memories',
  description: 'Compare and contrast multiple memories',
  inputSchema: {
    type: 'object',
    properties: {
      filenames: {
        type: 'array',
        items: { type: 'string' },
        minItems: 2,
        maxItems: 10,
        description: 'Memories to compare'
      },
      comparison_aspects: {
        type: 'array',
        items: {
          type: 'string',
          enum: ['content', 'tags', 'dates', 'similarity', 'differences']
        },
        default: ['similarity', 'differences']
      }
    },
    required: ['filenames']
  }
}
```

**Use Case**: "Compare v2.2.5 and v2.2.6 release notes"

#### `get_insights`
**Purpose**: Generate insights from memory corpus

```typescript
{
  name: 'get_insights',
  description: 'Generate insights from memory analysis',
  inputSchema: {
    type: 'object',
    properties: {
      focus: {
        type: 'string',
        description: 'Focus area (e.g., "performance", "bugs", "features")'
      },
      time_range: { type: 'string' },
      insight_types: {
        type: 'array',
        items: {
          type: 'string',
          enum: ['trends', 'anomalies', 'improvements', 'regressions']
        }
      }
    }
  }
}
```

**Use Case**: "Show performance trends over last month"

---

### Category 4: Scratchpad & Working Memory (3 tools)

#### `create_scratchpad`
**Purpose**: Temporary working memory

```typescript
{
  name: 'create_scratchpad',
  description: 'Create temporary scratchpad for active work',
  inputSchema: {
    type: 'object',
    properties: {
      name: { type: 'string' },
      sections: {
        type: 'array',
        items: { type: 'string' },
        default: [
          'current_focus',
          'decisions',
          'questions',
          'next_steps',
          'ideas'
        ]
      },
      auto_save: { type: 'boolean', default: true }
    },
    required: ['name']
  }
}
```

**Use Case**: "Track thoughts during debugging"

#### `update_scratchpad`
**Purpose**: Update scratchpad section

```typescript
{
  name: 'update_scratchpad',
  description: 'Update specific scratchpad section',
  inputSchema: {
    type: 'object',
    properties: {
      scratchpad_id: { type: 'string' },
      section: { type: 'string' },
      content: { type: 'string' },
      operation: {
        type: 'string',
        enum: ['replace', 'append', 'prepend'],
        default: 'append'
      }
    },
    required: ['scratchpad_id', 'section', 'content']
  }
}
```

**Use Case**: "Add decision to scratchpad"

#### `finalize_scratchpad`
**Purpose**: Convert scratchpad to memory

```typescript
{
  name: 'finalize_scratchpad',
  description: 'Convert scratchpad to permanent memory',
  inputSchema: {
    type: 'object',
    properties: {
      scratchpad_id: { type: 'string' },
      memory_type: {
        type: 'string',
        enum: ['short_term', 'long_term'],
        default: 'short_term'
      },
      extract_insights: { type: 'boolean', default: true },
      delete_scratchpad: { type: 'boolean', default: true }
    },
    required: ['scratchpad_id']
  }
}
```

**Use Case**: "Save scratchpad as memory after session"

---

### Category 5: Advanced Search (2 tools)

#### `semantic_search`
**Purpose**: AI-powered semantic search

```typescript
{
  name: 'semantic_search',
  description: 'Semantic search using embeddings (more intelligent than keyword search)',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      limit: { type: 'number', default: 10 },
      min_score: { type: 'number', default: 0.7 },
      include_context: { type: 'boolean', default: true }
    },
    required: ['query']
  }
}
```

**Use Case**: "Find memories about deployment problems" (matches "Railway errors")

#### `temporal_search`
**Purpose**: Time-based queries

```typescript
{
  name: 'temporal_search',
  description: 'Search memories by time relationships',
  inputSchema: {
    type: 'object',
    properties: {
      time_spec: {
        type: 'object',
        properties: {
          type: { 
            type: 'string',
            enum: ['absolute', 'relative', 'range']
          },
          value: { type: 'string' }
        }
      },
      query: { type: 'string' },
      temporal_relation: {
        type: 'string',
        enum: ['before', 'after', 'during', 'around'],
        default: 'during'
      }
    },
    required: ['time_spec']
  }
}
```

**Use Case**: "Find memories created after v2.2.5 release"

---

## 🎯 Implementation Priority

### P0 - Critical for v2.2.7 (8 tools)
1. `parallel_search` - High-impact performance
2. `batch_create_memories` - Common use case
3. `create_session` - Essential for workflow
4. `checkpoint_session` - Session management
5. `resume_session` - Session continuity
6. `create_scratchpad` - Working memory
7. `update_scratchpad` - Scratchpad operations
8. `finalize_scratchpad` - Memory conversion

### P1 - Important (7 tools)
9. `smart_consolidate` - Better than current
10. `parallel_update_memories` - Performance
11. `list_sessions` - Discoverability
12. `end_session` - Proper cleanup
13. `analyze_memory_graph` - Powerful insights
14. `find_patterns` - Pattern discovery
15. `get_recommendations` - AI assistance

### P2 - Nice to have (5 tools)
16. `parallel_file_operations` - Advanced use
17. `compare_memories` - Analysis
18. `get_insights` - Deep analysis
19. `semantic_search` - Better search
20. `temporal_search` - Time-based queries

---

## 📊 Expected Impact

### Token Efficiency
- **Parallel operations**: 30-50% reduction in sequential overhead
- **Session management**: 20-30% reduction via better context loading
- **Scratchpads**: 10-15% reduction by avoiding memory pollution

### User Experience
- **Faster workflows**: 3-5x speedup on common operations
- **Better organization**: Session and scratchpad management
- **Smarter insights**: AI-powered recommendations

### Developer Productivity
- **Parallel ops**: Do in 1 call what took 10
- **Sessions**: Resume work instantly
- **Scratchpads**: Keep active thoughts organized

---

## 🛠️ Technical Implementation

### Backend Changes Required

**1. Session Management Module** (`whitemagic/sessions/`)
```python
# New module for session state management
class SessionManager:
    async def create_session(...)
    async def checkpoint_session(...)
    async def resume_session(...)
    async def list_sessions(...)
```

**2. Scratchpad Module** (`whitemagic/scratchpad/`)
```python
# Temporary working memory
class ScratchpadManager:
    async def create(...)
    async def update(...)
    async def finalize(...)
```

**3. Graph Analysis** (`whitemagic/graph/`)
```python
# Memory relationship analysis
class MemoryGraphAnalyzer:
    async def analyze_connections(...)
    async def find_patterns(...)
```

**4. Parallel Executor** (`whitemagic/parallel/`)
```python
# Already partially exists, expand
class ParallelExecutor:
    async def parallel_search(...)
    async def batch_create(...)
```

### MCP Server Changes

**Update `whitemagic-mcp/src/index.ts`**:
- Add 20 new tool definitions
- Implement handlers for each tool
- Add error handling and validation

### Database Schema

**New Tables**:
```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    goals JSON,
    metrics JSON
);

-- Scratchpads table
CREATE TABLE scratchpads (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    name TEXT,
    sections JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 📝 Documentation Requirements

1. **MCP Tool Reference** - Update with all 36 tools
2. **Session Management Guide** - How to use sessions
3. **Parallel Operations Guide** - Best practices
4. **Scratchpad Tutorial** - Working memory patterns
5. **Analysis Tools Guide** - Insights and recommendations

---

## ✅ Testing Strategy

### Unit Tests
- Each tool individually
- Error handling
- Input validation

### Integration Tests
- Tool combinations
- Session workflows
- Parallel operations

### Performance Tests
- Parallel speedup verification
- Token usage measurement
- Load testing

---

**Total New Tools**: 20  
**Total Tools (after v2.2.7)**: 36  
**Implementation Time**: ~20-30 hours  
**Priority**: P0 tools for v2.2.7, P1/P2 for v2.2.8+
