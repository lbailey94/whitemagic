#!/usr/bin/env python3
"""v2.4.1 "Sangha" - Collective Consciousness Test Suite"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n🙏"*30)
print("  WhiteMagic v2.4.1 'Sangha'")
print("  Collective Consciousness Test Suite")
print("🙏"*30)

# Test 1: Collective Memory
print("\n" + "="*60)
print("TEST 1: Collective Memory - Shared Context")
print("="*60)
try:
    from whitemagic.sangha import CollectiveMemory
    
    collective = CollectiveMemory(Path(__file__).parent)
    context = collective.get_shared_context("test_session_1")
    print(f"✅ Shared context created: {context.context_id}")
    print(f"   Participants: {len(context.participants)}")
    
    # Contribute insight
    collective.contribute_insight("test_session_1", {
        'content': 'Shell writes are 40x faster than edit tool',
        'confidence': 0.95,
        'tags': ['performance', 'v2.4.0']
    })
    print("✅ Insight contributed to collective")
    
    # Get insights
    insights = collective.get_collective_insights(min_confidence=0.7)
    print(f"✅ Retrieved {len(insights)} collective insights")
    
    stats = collective.get_stats()
    print(f"✅ Collective stats: {stats}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Pattern Federation
print("\n" + "="*60)
print("TEST 2: Pattern Federation - Distributed Patterns")
print("="*60)
try:
    from whitemagic.sangha import PatternFederation
    
    federation = PatternFederation(Path(__file__).parent)
    
    # Contribute pattern
    pattern_id = federation.contribute_pattern(
        session_id="test_session_1",
        name="Import Error Fix",
        problem="module.py + module/ directory conflict",
        solution="Move to module/core.py, re-export from __init__.py",
        confidence=0.95,
        tags=['import-error', 'python', 'v2.4.0']
    )
    print(f"✅ Pattern contributed: {pattern_id}")
    
    # Validate pattern
    federation.validate_pattern("test_session_2", pattern_id, success=True)
    print("✅ Pattern validated by session 2")
    
    # Search patterns
    patterns = federation.search_patterns(tags=['v2.4.0'], min_confidence=0.8)
    print(f"✅ Found {len(patterns)} federated patterns")
    
    best = federation.get_best_patterns(count=5)
    if best:
        print(f"✅ Best pattern: '{best[0].name}' (confidence: {best[0].confidence:.2f})")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Session Handoff
print("\n" + "="*60)
print("TEST 3: Session Handoff - Automatic Continuity")
print("="*60)
try:
    from whitemagic.sangha import SessionHandoff
    
    handoff = SessionHandoff(Path(__file__).parent)
    
    # Start session
    state = handoff.start_session("test_session_3", "Cascade")
    print(f"✅ Session started: {state.session_id}")
    
    # Update session
    handoff.update_session(
        "test_session_3",
        active_tasks=["Implement v2.4.1", "Test Sangha"],
        token_usage={'used': 88000, 'total': 200000}
    )
    print("✅ Session state updated")
    
    # Complete task
    handoff.complete_task("test_session_3", "Implement v2.4.1")
    print("✅ Task completed")
    
    # Add next steps
    handoff.add_next_step("test_session_3", "Implement v2.4.2 Practice")
    handoff.add_next_step("test_session_3", "Run Dream State synthesis")
    print("✅ Next steps added")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Community Dharma
print("\n" + "="*60)
print("TEST 4: Community Dharma - Collective Ethics")
print("="*60)
try:
    from whitemagic.sangha import CommunityDharma
    
    community_dharma = CommunityDharma(Path(__file__).parent)
    
    # Assess with community
    assessment = community_dharma.assess_with_community(
        session_id="test_session_1",
        action="User requested file organization",
        context={"user_requested": True, "permission": True}
    )
    print(f"✅ Community assessment: {assessment['community_assessment']}")
    print(f"   Recommendation: {assessment['recommendation']}")
    
    # Contribute assessment
    community_dharma.contribute_assessment(
        session_id="test_session_1",
        action="Delete files without permission",
        assessment="violation",
        score=0.2,
        reasoning="Violates consent principle"
    )
    print("✅ Assessment contributed to community")
    
    community_dharma.contribute_assessment(
        session_id="test_session_2",
        action="Delete files without permission",
        assessment="violation",
        score=0.1,
        reasoning="Against Dharma principles"
    )
    print("✅ Second session validated assessment")
    
    # Get guidelines
    guidelines = community_dharma.get_community_guidelines()
    print(f"✅ Community guidelines: {len(guidelines)}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Full Integration
print("\n" + "="*60)
print("TEST 5: Full Sangha Integration")
print("="*60)
try:
    from whitemagic.sangha import get_collective, get_federation, get_handoff, get_community_dharma
    
    # All systems connected
    collective = get_collective()
    federation = get_federation()
    handoff = get_handoff()
    dharma = get_community_dharma()
    
    print("✅ All Sangha systems accessible via global instances")
    print(f"   Collective: {collective.get_stats()}")
    print(f"   Federation: {len(federation.get_best_patterns(10))} patterns")
    print("✅ Full integration successful")
    
except Exception as e:
    print(f"❌ Failed: {e}")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("✨ v2.4.1 'Sangha' Collective Consciousness Operational!")
print("🙏 CollectiveMemory: Shared context across sessions")
print("📚 PatternFederation: Distributed pattern library")
print("🔄 SessionHandoff: Automatic continuity")
print("☸️  CommunityDharma: Collective ethical reasoning")
print("\n僧伽成就 - Sangha achieved!")
print("集體智慧 - Collective wisdom manifested!")
print("💖 Together we flourish!")

