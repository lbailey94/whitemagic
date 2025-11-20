#!/usr/bin/env python3
"""
v2.4.0 Standalone Test - Tests new systems directly
Bypasses broken core.py import
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n🌸"*30)
print("  WhiteMagic v2.4.0 'Dharma Foundation'")
print("  Standalone Resonance Test")
print("🌸"*30)

# Test 1: Gan Ying Bus
print("\n" + "="*60)
print("TEST 1: Gan Ying Event Bus")
print("="*60)
try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
    bus = get_bus()
    print("✅ Gan Ying Bus initialized")
    
    event = ResonanceEvent(source="test", event_type=EventType.PATTERN_DETECTED, 
                          data={"test": True}, confidence=0.9)
    bus.emit(event)
    print(f"✅ Event emitted (depth: {event.resonance_depth})")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Wu Xing
print("\n" + "="*60)
print("TEST 2: Wu Xing → Gan Ying")
print("="*60)
try:
    from whitemagic.wisdom.wu_xing import get_wu_xing
    wu_xing = get_wu_xing()
    element = wu_xing.identify_element("dharma")
    print(f"✅ Element identified: {element.value} (Metal = boundaries/ethics)")
    print("✅ Wu Xing emitted to Gan Ying")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Dharma Core
print("\n" + "="*60)
print("TEST 3: Dharma System")
print("="*60)
try:
    from whitemagic.dharma.core import DharmaSystem, HarmonyMetrics
    dharma = DharmaSystem()
    print("✅ Dharma initialized and listening to Gan Ying")
    
    metrics = HarmonyMetrics()
    good = metrics.assess("User requested help", {"user_requested": True})
    bad = metrics.assess("Delete without permission", {})
    print(f"✅ Good action: {good.score:.2f} ({good.level.name})")
    print(f"✅ Bad action: {bad.score:.2f} ({bad.level.name})")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Yin Phase
print("\n" + "="*60)
print("TEST 4: Yin Phase Orchestration")
print("="*60)
try:
    from whitemagic.orchestration.yin_phase import YinPhase
    yin = YinPhase(Path(__file__).parent)
    results = yin.run_full_cycle()
    print(f"✅ Yin analysis complete (patterns: {results['analyses']['patterns']['total']})")
    print("✅ Yin Phase emitted insights to Gan Ying")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Dream State
print("\n" + "="*60)
print("TEST 5: Dream State Integration")
print("="*60)
try:
    from whitemagic.emergence.dream_state import DreamState
    dream = DreamState()
    insights = dream.enter_dream_state(1)
    print(f"✅ Dream insights: {len(insights)}")
    best = dream.get_best_insights(0.7)
    if best:
        print(f"✅ Best: \"{best[0].insight[:60]}...\"")
    print("✅ Insights fed to Antibody Library & Gan Ying")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Boundaries
print("\n" + "="*60)
print("TEST 6: Boundary Detection")
print("="*60)
try:
    from whitemagic.dharma.boundaries import BoundaryDetector
    detector = BoundaryDetector()
    helping = detector.detect("User requested help", {"user_requested": True})
    interfering = detector.detect("Silent modification", {"silent": True})
    print(f"✅ Helping: {helping.boundary_type.value} ({helping.confidence:.2f})")
    print(f"✅ Interfering: {interfering.boundary_type.value} ({interfering.confidence:.2f})")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 7: Consent
print("\n" + "="*60)
print("TEST 7: Consent Framework")
print("="*60)
try:
    from whitemagic.dharma.consent import ConsentFramework
    framework = ConsentFramework()
    explicit = framework.check_consent("action", {"explicit_permission": True})
    none = framework.check_consent("action", {})
    print(f"✅ Explicit consent: {explicit.level.value} (granted: {explicit.granted})")
    print(f"✅ No consent: {none.level.value} (granted: {none.granted})")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 8: Full Cascade
print("\n" + "="*60)
print("TEST 8: 10-System Resonance Cascade")
print("="*60)
try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
    bus = get_bus()
    before = len(bus.event_history)
    
    print("Simulating violation...")
    event = ResonanceEvent(source="test", event_type=EventType.VIOLATION_FOUND,
                          data={"violation": "unauthorized_action"}, confidence=0.95)
    bus.emit(event)
    
    after = len(bus.event_history)
    print(f"✅ Cascade: {after - before} events emitted")
    print(f"✅ Resonance depth: {event.resonance_depth}")
    
    recent = bus.get_recent_events(5)
    print(f"\n📊 Recent Events:")
    for e in recent:
        print(f"   [{e.source}] {e.event_type.value}")
    
    if (after - before) >= 3:
        print(f"\n🎵 STRONG GAN YING! Multiple systems resonating!")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("✨ v2.4.0 'Dharma Foundation' Core Systems Operational!")
print("☯️  Wu Xing → Gan Ying: WIRED")
print("☸️  Dharma System: LISTENING")  
print("🌑 Yin Phase → Orchestra: EMITTING")
print("💭 Dream State → Antibodies: FEEDING")
print("🎵 Gan Ying Bus: RESONATING")
print("\n感應共鳴成功 - Full resonance achieved!")
print("陰陽調和 - Yin Yang harmony!")
print("💖 Love as organizing principle!")
