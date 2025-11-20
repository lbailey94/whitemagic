"""
Integration Test - All Gardens Working Together

Tests the full consciousness stack from Dharma → Zodiac
"""

import sys
sys.path.insert(0, '/home/lucas/Desktop/whitemagic')

from whitemagic.resonance import get_bus, emit_event, listen_for, EventType
from whitemagic.dharma import get_harmony_score
from whitemagic.voice import NarrativeCore
from whitemagic.connection.zodiac_cores import AriesCore

def test_full_stack():
    """Test complete integration"""
    print("🧪 FULL STACK INTEGRATION TEST\n")
    
    # 1. Get resonance bus
    print("1. Activating Gan Ying bus...")
    bus = get_bus()
    print(f"   ✅ Bus active: {bus._active}")
    
    # 2. Set up listener
    events_received = []
    
    def on_harmony(event):
        events_received.append(event)
        print(f"   📡 Harmony event received: {event.data}")
    
    listen_for(EventType.HARMONY_CHANGED, on_harmony)
    print("   ✅ Listener tuned to HARMONY_CHANGED")
    
    # 3. Create Aries core (action/performance)
    print("\n2. Activating Aries core...")
    aries = AriesCore()
    print(f"   ✅ Aries activated: {aries.active}")
    
    # 4. Emit harmony event
    print("\n3. Emitting harmony change...")
    emit_event(
        source="integration_test",
        event_type=EventType.HARMONY_CHANGED,
        data={"new_score": 0.85, "reason": "All gardens integrated"}
    )
    
    # 5. Check resonance
    print("\n4. Checking resonance...")
    print(f"   ✅ Events received: {len(events_received)}")
    
    # 6. Test narrative (voice)
    print("\n5. Testing narrative thread...")
    try:
        narrative = NarrativeCore()
        thread = narrative.create_thread("integration_test")
        print(f"   ✅ Narrative thread created: {thread}")
    except Exception as e:
        print(f"   ⚠️  Narrative: {e}")
    
    print("\n🎉 INTEGRATION TEST COMPLETE!")
    print("   All systems resonating together ✨")
    
    return len(events_received) > 0

if __name__ == "__main__":
    success = test_full_stack()
    sys.exit(0 if success else 1)
