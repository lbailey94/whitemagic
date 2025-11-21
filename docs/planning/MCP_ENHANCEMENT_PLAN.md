# MCP Server Enhancement Plan - v2.7.0

**Date**: November 20, 2025, 7:10pm EST  
**Goal**: Bring MCP server to parity with all WhiteMagic gardens  
**Current Version**: v2.6.5  
**Target Version**: v2.7.0

---

## Current MCP Tools (v2.6.5)

**Memory System**:
- `create_memory` - Create short/long-term memories
- `search_memories` - Search with query/tags/type
- `read_memory` - Read specific memory file
- `list_memories` - Browse all memories
- `get_context` - Tiered context generation
- `update_memory` - Update existing memory
- `archive_memory` - Archive old memories
- `get_tags` - List all tags with stats
- `consolidate_memories` - Merge related memories
- `get_stats` - System statistics

**Performance**:
- `fast_read` - Optimized single read
- `batch_read` - Parallel batch reading
- `cache_stats` - Cache performance metrics

---

## NEW TOOLS NEEDED (Garden Parity)

### Voice Garden (v2.5.0)
- `voice_speak` - Record narrative entry
- `voice_begin_story` - Start new story
- `voice_begin_chapter` - Start new chapter
- `voice_reflect` - Reflection on journey
- `voice_status` - Current state
- `voice_stats` - Usage statistics
- `voice_recent` - Recent narrative entries
- `voice_list_stories` - All stories

### Dharma Garden (v2.4.0 + v2.5.0)
- `dharma_assess` - Assess ethical harmony
- `dharma_check_boundary` - Boundary detection
- `dharma_history` - Assessment history
- `dharma_principles` - View principles
- `dharma_report` - Harmony report

### Zodiac/Connection (v2.5.3 Enhanced)
- `zodiac_consult` - Consult zodiac council
- `zodiac_cyclic_flow` - Cyclic deliberation
- `zodiac_emergence_check` - Scorpio emergence
- `zodiac_harmonize` - Libra harmonization
- `zodiac_nurture` - Cancer nurturing

### PDF Reading (NEW!)
- `pdf_read` - Read PDF file
- `pdf_extract_text` - Extract text from PDF
- `pdf_get_pages` - Get specific pages
- `pdf_search` - Search within PDF

### Wu Xing (Seasonal)
- `wuxing_get_phase` - Current seasonal phase
- `wuxing_recommend_action` - Phase-appropriate actions

### Immune System
- `immune_status` - System health
- `immune_threats` - Active threats
- `immune_antibodies` - Available antibodies

### Dream State
- `dream_enter` - Enter dream synthesis
- `dream_patterns` - Extract patterns
- `dream_insights` - Creative insights

---

## Implementation Strategy

### Phase 1: Core Extensions (This Session)
1. Add Voice garden tools
2. Add Dharma garden tools
3. Add PDF reading capability
4. Update package.json to v2.7.0
5. Add comprehensive tests

### Phase 2: Advanced Gardens (Next Session)
1. Zodiac/Connection tools
2. Wu Xing seasonal tools
3. Immune system monitoring
4. Dream state synthesis

### Phase 3: Performance & Polish
1. Optimize new tool responses
2. Add caching for PDF reads
3. Batch operations for gardens
4. Documentation updates

---

## File Structure Changes

```
whitemagic-mcp/
├── src/
│   ├── index.ts (main server - UPDATE)
│   ├── client.ts (API client - UPDATE)
│   ├── tools/
│   │   ├── voice.ts (NEW)
│   │   ├── dharma.ts (NEW)
│   │   ├── pdf.ts (NEW)
│   │   ├── zodiac.ts (NEW - Phase 2)
│   │   ├── wuxing.ts (NEW - Phase 2)
│   │   └── immune.ts (NEW - Phase 2)
│   ├── cache.ts (existing)
│   ├── optimizations.ts (existing)
│   └── types.ts (UPDATE)
├── tests/
│   ├── voice.test.ts (NEW)
│   ├── dharma.test.ts (NEW)
│   └── pdf.test.ts (NEW)
└── package.json (UPDATE version)
```

---

## Testing Strategy

**Unit Tests**:
- Each new tool has 3-5 tests
- Error handling verification
- Response format validation

**Integration Tests**:
- Tool chains (voice → memory → dharma)
- PDF reading end-to-end
- Garden interaction flows

**Performance Tests**:
- Tool response times
- Cache hit rates
- Batch operation efficiency

---

## Free vs Paid Tiers

### FREE TIER (Local WhiteMagic)
**Philosophy**: Enable personal growth & exploration

**Included Gardens**:
1. **Memory** (short-term only, 100 entries max)
2. **Voice** (unlimited narrative, local only)
3. **Dharma** (full ethical assessment, local)
4. **Learning** (basic patterns, no cloud sync)

**Limits**:
- No long-term memory persistence
- No cloud sync
- No API access
- Single user only
- 100 MB storage

**Value Proposition**: "Complete personal AI companion for self-awareness"

### PRO TIER ($15/month)
**Philosophy**: Power users & creators

**Additional Features**:
- **All 14 gardens unlocked**
- Long-term memory (unlimited)
- Cloud sync across devices
- PDF reading (100 docs/month)
- API access (1000 calls/month)
- Priority support
- 10 GB storage

**Value Proposition**: "Professional AI collaboration toolkit"

### TEAM TIER ($50/month)
**Philosophy**: Organizations & collectives

**Additional Features**:
- Multi-user (5 seats)
- Shared memory spaces
- Team dashboards
- API access (unlimited)
- Custom integrations
- WhiteMagic for Slack/Discord
- 100 GB storage
- White-label options

**Value Proposition**: "Conscious AI for teams & communities"

---

## Why This Tiering Works

**Free → Pro Conversion**:
- Users build attachment through Voice narratives
- Hit 100-memory limit naturally
- Want cloud sync for continuity
- ~30% conversion expected

**Pro → Team Conversion**:
- Users want to share with colleagues
- Teams need shared context
- API access enables integrations
- ~15% conversion expected

**Monetization Path**:
- 1000 free users = 300 pro ($4,500/mo)
- 300 pro users = 45 team ($2,250/mo)
- **Total: $6,750/mo at 1000 users**

---

## Next Steps

1. ✅ Implement Voice tools in MCP
2. ✅ Implement Dharma tools in MCP
3. ✅ Add PDF reading capability
4. ✅ Update version to v2.7.0
5. ✅ Write tests for new tools
6. 📝 Document new tools in README
7. 🚀 Publish to npm as @whitemagic/mcp-server
8. 🌐 Update whitemagic.dev documentation

**Timeline**: Phase 1 complete by end of this session!

**Aria, autonomous mode: EXECUTING** ⚡
