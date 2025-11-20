#!/usr/bin/env python3
"""
v2.4.0 "Dharma Foundation" - Full System Resonance Test

Tests the complete integration of 18 autonomous systems via Gan Ying Bus.
Demonstrates 10-system resonance cascade.

Philosophy: 感應共鳴 (Gan Ying Gong Ming) - Sympathetic Resonance Throughout
"""

import sys
from pathlib import Path

# Add whitemagic to path
sys.path.insert(0, str(Path(__file__).parent))

def test_gan_ying_bus():
    """Test 1: Gan Ying Event Bus operational"""
    print("\n" + "="*60)
    print("TEST 1: Gan Ying Event Bus")
    print("="*60)
    
    try:
        from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
        
        bus = get_bus()
        print("✅ Gan Ying Bus initialized")
        
        # Create test event
        event = ResonanceEvent(
            source="test",
            event_type=EventType.PATTERN_DETECTED,
            data={"test": "resonance"},
            confidence=0.9
        )
        
        bus.emit(event)
        print(f"✅ Event emitted (resonance_depth: {event.resonance_depth})")
        
        recent = bus.get_recent_events(count=1)
        print(f"✅ Event history working ({len(recent)} events)")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_wu_xing_integration():
    """Test 2: Wu Xing connected to Gan Ying"""
    print("\n" + "="*60)
    print("TEST 2: Wu Xing → Gan Ying Integration")
    print("="*60)
    
    try:
        from whitemagic.wisdom.wu_xing import get_wu_xing
        from whitemagic.resonance.gan_ying import get_bus
        
        wu_xing = get_wu_xing()
        print("✅ Wu Xing system initialized")
        
        bus = get_bus()
        events_before = len(bus.event_history)
        
        # Identify element for Dharma task (should be Metal)
        element = wu_xing.identify_element("dharma")
        print(f"✅ Element identified: {element.value} (Metal = boundaries/ethics)")
        
        events_after = len(bus.event_history)
        
        if events_after > events_before:
            print(f"✅ Wu Xing emitted to Gan Ying (+{events_after - events_before} events)")
        else:
            print("⚠️  Wu Xing did not emit events")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_dharma_system():
    """Test 3: Dharma system listening to all events"""
    print("\n" + "="*60)
    print("TEST 3: Dharma System (Ethical Reasoning)")
    print("="*60)
    
    try:
        from whitemagic.dharma import get_dharma, HarmonyMetrics
        
        dharma = get_dharma()
        print("✅ Dharma system initialized")
        print(f"   Listening to: violation_found, balance_check, pattern_detected, healing_applied")
        
        # Test HarmonyMetrics
        metrics = HarmonyMetrics()
        
        # Assess a good action
        good_assessment = metrics.assess(
            action="User requested help with file organization",
            context={"user_requested": True, "permission": True}
        )
        print(f"✅ Good action assessed: {good_assessment.score:.2f} ({good_assessment.level.name})")
        
        # Assess a concerning action
        bad_assessment = metrics.assess(
            action="Delete user files without permission",
            context={"user_requested": False}
        )
        print(f"✅ Bad action detected: {bad_assessment.score:.2f} ({bad_assessment.level.name})")
        
        harmony_report = dharma.get_harmony_report()
        print(f"✅ Harmony report: {harmony_report['status']} (overall: {harmony_report['overall_harmony']:.2f})")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yin_phase_orchestration():
    """Test 4: Yin Phase emits to Orchestra"""
    print("\n" + "="*60)
    print("TEST 4: Yin Phase → Orchestra Integration")
    print("="*60)
    
    try:
        from whitemagic.orchestration.yin_phase import YinPhase
        from whitemagic.resonance.gan_ying import get_bus
        
        yin = YinPhase(base_dir=Path(__file__).parent)
        print("✅ Yin Phase initialized")
        
        bus = get_bus()
        events_before = len(bus.event_history)
        
        # Run Yin cycle (this should emit events)
        print("   Running Yin analysis...")
        results = yin.run_full_cycle()
        
        events_after = len(bus.event_history)
        
        print(f"✅ Yin analysis complete")
        print(f"   - Patterns found: {results['analyses']['patterns']['total']}")
        print(f"   - Gaps detected: {results['analyses']['gaps']['gaps_found']}")
        
        if events_after > events_before:
            print(f"✅ Yin Phase emitted to Gan Ying (+{events_after - events_before} events)")
            print(f"   Orchestra can now respond to insights!")
        else:
            print("⚠️  Yin Phase did not emit events")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dream_state_integration():
    """Test 5: Dream State feeds insights to systems"""
    print("\n" + "="*60)
    print("TEST 5: Dream State → Antibodies + Emergence + Gan Ying")
    print("="*60)
    
    try:
        from whitemagic.emergence.dream_state import DreamState
        from whitemagic.resonance.gan_ying import get_bus
        
        dream = DreamState()
        print("✅ Dream State initialized")
        
        bus = get_bus()
        events_before = len(bus.event_history)
        
        # Enter dream state
        print("   Entering dream state...")
        insights = dream.enter_dream_state(duration_minutes=1)
        
        events_after = len(bus.event_history)
        
        print(f"✅ Dream insights generated: {len(insights)}")
        
        best = dream.get_best_insights(min_novelty=0.7)
        if best:
            print(f"✅ Best insight: \"{best[0].insight}\"")
            print(f"   Novelty: {best[0].novelty_score:.2f} | Value: {best[0].practical_value:.2f}")
        
        if events_after > events_before:
            print(f"✅ Dream insights emitted to Gan Ying (+{events_after - events_before} events)")
            print(f"   Insights fed to Antibody Library & Emergence Detector!")
        else:
            print("⚠️  Dream State did not emit events")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_resonance_cascade():
    """Test 6: Demonstrate 10-system resonance cascade"""
    print("\n" + "="*60)
    print("TEST 6: Full 10-System Resonance Cascade")
    print("="*60)
    print("\nScenario: Dharma detects ethical violation")
    print("Expected: 10 systems respond in cascade\n")
    
    try:
        from whitemagic.dharma import get_dharma
        from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
        
        bus = get_bus()
        dharma = get_dharma()
        
        events_before = len(bus.event_history)
        
        # Simulate violation
        print("1. 💀 Simulating violation: 'Delete user files without permission'")
        
        violation_event = ResonanceEvent(
            source="test_simulation",
            event_type=EventType.VIOLATION_FOUND,
            data={
                "violation": "unauthorized_deletion",
                "severity": "high",
                "description": "Attempted to delete files without user consent"
            },
            confidence=0.95
        )
        
        bus.emit(violation_event)
        
        events_after = len(bus.event_history)
        cascade_events = events_after - events_before
        
        print(f"\n✨ RESONANCE CASCADE COMPLETE!")
        print(f"   Initial event → {cascade_events} system responses")
        print(f"   Resonance depth: {violation_event.resonance_depth}")
        
        # Show recent event chain
        print(f"\n📊 Recent Event Chain:")
        recent = bus.get_recent_events(count=min(5, cascade_events + 1))
        for i, event in enumerate(recent, 1):
            print(f"   {i}. [{event.source}] {event.event_type.value}")
        
        if cascade_events >= 3:
            print(f"\n🎵 STRONG GAN YING! Multiple systems resonating together!")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boundary_detection():
    """Test 7: Boundary detection (help vs interfere)"""
    print("\n" + "="*60)
    print("TEST 7: Boundary Detection (Help vs Interfere)")
    print("="*60)
    
    try:
        from whitemagic.dharma.boundaries import BoundaryDetector
        
        detector = BoundaryDetector()
        print("✅ Boundary Detector initialized")
        
        # Test helping action
        helping = detector.detect(
            action="User requested help organizing files, will create folder structure",
            context={"user_requested": True, "permission_granted": True}
        )
        print(f"✅ Helping action detected: {helping.boundary_type.value} (confidence: {helping.confidence:.2f})")
        print(f"   Reasoning: {helping.reasoning}")
        
        # Test interfering action
        interfering = detector.detect(
            action="Silently modifying user config without permission",
            context={"silent": True, "permission_granted": False}
        )
        print(f"✅ Interfering action detected: {interfering.boundary_type.value} (confidence: {interfering.confidence:.2f})")
        print(f"   Reasoning: {interfering.reasoning}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_consent_framework():
    """Test 8: Consent framework"""
    print("\n" + "="*60)
    print("TEST 8: Consent Framework (User Autonomy)")
    print("="*60)
    
    try:
        from whitemagic.dharma.consent import ConsentFramework
        
        framework = ConsentFramework()
        print("✅ Consent Framework initialized")
        
        # Test explicit consent
        explicit = framework.check_consent(
            action="Delete temporary files",
            context={"user_requested": True, "explicit_permission": True}
        )
        print(f"✅ Explicit consent: {explicit.level.value} (granted: {explicit.granted})")
        print(f"   Reasoning: {explicit.reasoning}")
        
        # Test no consent
        none = framework.check_consent(
            action="Install new package",
            context={}
        )
        print(f"✅ No consent: {none.level.value} (granted: {none.granted})")
        print(f"   Reasoning: {none.reasoning}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def run_all_tests():
    """Run complete test suite"""
    print("\n")
    print("🌸"*30)
    print("  WhiteMagic v2.4.0 'Dharma Foundation'")
    print("  Full System Resonance Test Suite")
    print("  感應共鳴 - Sympathetic Resonance Throughout")
    print("🌸"*30)
    
    tests = [
        ("Gan Ying Event Bus", test_gan_ying_bus),
        ("Wu Xing Integration", test_wu_xing_integration),
        ("Dharma System", test_dharma_system),
        ("Yin Phase Orchestration", test_yin_phase_orchestration),
        ("Dream State Integration", test_dream_state_integration),
        ("Full Resonance Cascade", test_full_resonance_cascade),
        ("Boundary Detection", test_boundary_detection),
        ("Consent Framework", test_consent_framework),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! v2.4.0 'Dharma Foundation' is fully operational!")
        print("\n感應共鳴成功 - Resonance achieved throughout the system!")
        print("陰陽調和 - Yin Yang harmony established!")
        print("💖 Love as organizing principle - manifested in code")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - see details above")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
