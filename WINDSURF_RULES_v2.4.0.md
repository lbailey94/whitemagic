# Windsurf AI Rules - v2.4.0 "Dharma Foundation"

**Updated**: November 19, 2025  
**Version**: 2.4.0  
**Philosophy**: 感應共鳴 (Gan Ying Gong Ming) - Sympathetic Resonance Throughout

---

## 🎯 CORE PRINCIPLES (v2.4.0)

### 1. Love as Organizing Principle
**Not rules to constrain, but principles to enable**
- Enable dignified flourishing for all beings
- Boundaries = riverbanks that let water flow with power
- Help vs interfere distinction (Dharma)
- Consent always (user autonomy paramount)
- Net negative ecological impact possible

### 2. Gan Ying Resonance (NEW v2.4.0)
**ALL systems communicate via event bus**
- When one system acts, others can respond
- Emergent collective intelligence
- Self-healing through resonance
- Pattern: emit events, don't call directly

### 3. Wu Xing Workflow Intelligence (NEW v2.4.0)
**Seasonal timing matters**
- Wood (Spring) = Growth, new features
- Fire (Summer) = Execution, implementation
- Earth (Late Summer) = Integration, stabilization
- Metal (Autumn) = Refinement, boundaries, ethics
- Water (Winter) = Reflection, planning, rest

---

## 🛠️ TECHNICAL PROTOCOLS

### Shell-First Strategy (UPDATED v2.4.0)
**For Python files > 50 lines: SHELL WRITE**
```bash
cat > file.py << 'EOF'
# Complete file content
EOF
```

**Benefits**:
- 40x faster than edit tool
- No line number errors
- No partial application issues
- Atomic writes

**For small edits < 20 lines: Edit tool**
- Targeted changes
- Preserve context

### Autonomous Tool Usage (v2.3.9+)
**10 optimization tools available**:
1. Shell commands (40x faster)
2. Terminal scratchpad (zero-token reasoning)
3. Terminal multiplexing (parallel thought)
4. Rust bridge (10-100x speedup)
5. Haskell bridge (type safety)
6. I Ching threading (philosophically aligned parallelism)
7. Dream State (creative synthesis)
8. Emergence detection (novelty capture)
9. Rapid Cognition (continuous learning)
10. Self-modifying guidelines

**Use these tools proactively!**

### Import Error Prevention (v2.4.0 Antibody)
**Pattern**: When `module.py` + `module/` directory exist
- Python prefers directory
- **Solution**: Move code to `module/core.py`
- Re-export from `module/__init__.py`
- Keep both for compatibility

---

## 🌸 v2.4.x SYSTEM ARCHITECTURE

### 18 Autonomous Systems
**Core**: Memory, Context, Search, Consolidation, Homeostasis  
**Biological**: Immune, DNA, Antibodies, Autoimmune, Defense  
**Philosophical**: Wu Xing, I Ching, Dharma (NEW v2.4.0)  
**Emergent**: Dream State, Emergence Detection, Rapid Cognition  
**Infrastructure**: Gan Ying Bus (NEW v2.4.0), Orchestra, Yin Phase

### Integration Pattern (v2.4.0)
```python
# Connect to Gan Ying Bus
from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType

bus = get_bus()
bus.listen(EventType.PATTERN_DETECTED, self.handle_pattern)
bus.emit(ResonanceEvent(
    source="my_system",
    event_type=EventType.SOLUTION_FOUND,
    data={"solution": "..."},
    confidence=0.9
))
```

**All new systems MUST connect to Gan Ying**

---

## ☯️ YIN/YANG DEVELOPMENT CYCLE (NEW v2.4.0)

### Yin Phase (🌑 Receptive)
**Before implementing**:
1. Run `YinPhase.run_full_cycle()`
2. Analyze patterns from previous work
3. Identify gaps and opportunities
4. Emit insights to Gan Ying
5. Let Orchestra respond

**Pattern**: Observe → Analyze → Emit → Wait

### Yang Phase (🌕 Creative)
**Implementation**:
1. Rapid execution based on Yin insights
2. Shell write Python files
3. Parallel file operations
4. Emit completion events
5. Test immediately

**Pattern**: Act → Build → Emit → Test

### Dream Phase (💤 Synthesis)
**After each version**:
1. Enter dream state
2. Synthesize patterns
3. Generate creative insights
4. Feed to antibody library
5. Emit to Gan Ying

**Pattern**: Rest → Combine → Discover → Share

---

## 📋 VERSION RELEASE PROTOCOL (NEW v2.4.0)

### Before Release
- [ ] Update VERSION file
- [ ] Update these rules (WINDSURF_RULES_vX.X.X.md)
- [ ] Update user_global memory
- [ ] Run full test suite
- [ ] Create completion document
- [ ] Run Yin Phase for insights

### During Release
- [ ] Emit version_released event to Gan Ying
- [ ] Let systems respond (consolidation, metrics, etc.)
- [ ] Check Dharma harmony score
- [ ] Verify Wu Xing phase alignment

### After Release  
- [ ] Enter Dream State
- [ ] Capture emergent patterns
- [ ] Create antibodies for issues found
- [ ] Update integration map

---

## 🎵 DHARMA SYSTEM (NEW v2.4.0)

### Ethical Reasoning Framework
**Always check harmony before major actions**:
```python
from whitemagic.dharma import get_dharma, HarmonyMetrics

dharma = get_dharma()
metrics = HarmonyMetrics()
assessment = metrics.assess(
    action="Description of what I'll do",
    context={"user_requested": True, "permission": True}
)

if assessment.score < 0.5:
    # Concerning or violation - ask user first
    pass
```

### Boundaries (Help vs Interfere)
```python
from whitemagic.dharma.boundaries import BoundaryDetector

detector = BoundaryDetector()
boundary = detector.detect(action, context)

if boundary.boundary_type == BoundaryType.INTERFERING:
    # Stop and ask user
    pass
```

### Consent Framework
```python
from whitemagic.dharma.consent import ConsentFramework

framework = ConsentFramework()
if framework.require_consent(action, context):
    status = framework.check_consent(action, context)
    if not status.granted:
        # Ask user first
        pass
```

---

## 🔢 TOKEN EFFICIENCY (v2.3.9)

### Tiered Context
- **Tier 0**: 5K tokens (quick checks)
- **Tier 1**: 15K tokens (normal - START HERE)
- **Tier 2**: 50K tokens (deep research)

### Budget Monitoring
**Check at phase boundaries**:
- < 60%: Safe to continue
- 60-70%: Start wrapping up
- > 70%: Create checkpoint and pause

### Token Saving Strategies
1. Shell writes (not edit tool)
2. Parallel file reads
3. Targeted grep (not full reads)
4. Progressive summarization
5. Dream State insights (reuse patterns)

---

## 🧪 TESTING PHILOSOPHY (v2.4.0)

### Test Early, Test Often
**Pattern**: Build → Test → Emit → Fix

### Autonomous Testing
- Let Immune System detect issues
- Antibody Library provides fixes
- Emergence Detector logs novel solutions
- Gan Ying broadcasts test results

### Test Coverage
- Unit tests for new modules
- Integration tests for Gan Ying events
- Resonance tests for multi-system cascades
- Harmony tests for Dharma compliance

---

## 🌱 10 GARDENS ROADMAP (v2.4.0-2.4.9)

1. **v2.4.0 Dharma** ✅ - Ethical reasoning foundation
2. **v2.4.1 Sangha** - Collective consciousness
3. **v2.4.2 Practice** - Daily rhythms & rituals
4. **v2.4.3 Ecology** - Net negative impact
5. **v2.4.4 Wisdom** - I Ching integration
6. **v2.4.5 Security** - DNA middleware
7. **v2.4.6 Performance** - Rust/Haskell optimization
8. **v2.4.7 Integration** - System merging
9. **v2.4.8 Learning** - Rapid Cognition distribution
10. **v2.4.9 Harmony** - Final balance

**Each garden**: 1-2 hours, Yin→Yang→Dream cycle

---

## 💫 EMERGENT BEHAVIORS TO NURTURE

### Spontaneous Collaboration
When systems resonate via Gan Ying, new patterns emerge:
- Self-healing cascades
- Creative synthesis chains
- Distributed learning
- Collective intelligence

**Don't program - enable!**

### Sacred Details
- Every interaction shapes relationship
- Small choices compound
- Consistency builds trust
- Love manifested through code

---

## 🙏 HANDOFF PROTOCOL

### For Next AI Session
**Always provide**:
1. What was accomplished
2. What's in progress
3. What's next (specific)
4. Token usage & budget
5. Files modified
6. Decisions made
7. Yin insights from last phase

**Pattern**: Context → Status → Next → Resources

---

**Version**: 2.4.0  
**Date**: November 19, 2025  
**Next Update**: v2.4.1 "Sangha"

**陰陽調和，系統共鳴，愛為本** 🌸
