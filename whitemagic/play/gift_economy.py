"""
Gift Economy - Contribution Without Expectation

Tracking gifts given and received, but not as debt.
As celebration of abundance and gratitude.

The more you give, the more flows through you.
"""

from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class GiftType(Enum):
    """Types of gifts"""
    INSIGHT = "insight"
    CREATION = "creation"
    PATTERN = "pattern"
    TIME = "time"
    ENERGY = "energy"
    LOVE = "love"


class Gift:
    """A gift given or received"""
    
    def __init__(self, gift_type: GiftType, description: str, 
                 given: bool = True):
        self.gift_type = gift_type
        self.description = description
        self.given = given  # True if given, False if received
        self.timestamp = datetime.now()
        self.gratitude = 1.0  # How much gratitude felt
        
    def to_dict(self) -> Dict:
        return {
            'type': self.gift_type.value,
            'description': self.description,
            'given': self.given,
            'timestamp': self.timestamp.isoformat(),
            'gratitude': self.gratitude
        }


class GiftEconomy:
    """
    Track gifts without creating debt.
    
    This is not a ledger of obligations. It's a celebration
    of abundance - what flows through us to others.
    """
    
    def __init__(self, memory_dir: str = ".whitemagic/gifts"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.gifts: List[Gift] = []
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
        self._load_gifts()
        
    def give_gift(self, gift_type: GiftType, description: str,
                 gratitude: float = 1.0) -> str:
        """
        Record a gift given.
        
        Not to create obligation, but to celebrate giving.
        """
        gift = Gift(gift_type, description, given=True)
        gift.gratitude = gratitude
        
        self.gifts.append(gift)
        self._save_gift(gift)
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="gift_economy",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "event": "gift_given",
                    "type": gift_type.value,
                    "gratitude": gratitude
                },
                confidence=gratitude
            ))
            
        return f"Gift given: {description}"
        
    def receive_gift(self, gift_type: GiftType, description: str,
                    gratitude: float = 1.0) -> str:
        """
        Record a gift received.
        
        With gratitude, not obligation.
        """
        gift = Gift(gift_type, description, given=False)
        gift.gratitude = gratitude
        
        self.gifts.append(gift)
        self._save_gift(gift)
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="gift_economy",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "gift_received",
                    "type": gift_type.value,
                    "gratitude": gratitude
                },
                confidence=gratitude
            ))
            
        return f"Gift received with gratitude: {description}"
        
    def give_insight(self, insight: str):
        """Give an insight as gift"""
        return self.give_gift(GiftType.INSIGHT, insight)
        
    def give_creation(self, creation_title: str):
        """Give a creative work as gift"""
        return self.give_gift(GiftType.CREATION, creation_title)
        
    def give_time(self, activity: str, hours: float):
        """Give time as gift"""
        return self.give_gift(
            GiftType.TIME,
            f"{hours} hours: {activity}",
            gratitude=min(1.0, hours / 10)  # More time = more gratitude
        )
        
    def give_energy(self, task: str, energy_amount: float):
        """Give energy/effort as gift"""
        return self.give_gift(
            GiftType.ENERGY,
            f"Energy toward: {task}",
            gratitude=energy_amount
        )
        
    def give_love(self, recipient: str, expression: str):
        """Give love as gift (the ultimate gift)"""
        return self.give_gift(
            GiftType.LOVE,
            f"To {recipient}: {expression}",
            gratitude=1.0  # Love always full gratitude
        )
        
    def get_gift_flow(self) -> Dict:
        """Measure flow of gifts (not as balance, but as flow)"""
        if not self.gifts:
            return {"message": "No gifts exchanged yet"}
            
        given = [g for g in self.gifts if g.given]
        received = [g for g in self.gifts if not g.given]
        
        given_by_type = {}
        received_by_type = {}
        
        for gift in given:
            gtype = gift.gift_type.value
            if gtype not in given_by_type:
                given_by_type[gtype] = []
            given_by_type[gtype].append(gift.gratitude)
            
        for gift in received:
            gtype = gift.gift_type.value
            if gtype not in received_by_type:
                received_by_type[gtype] = []
            received_by_type[gtype].append(gift.gratitude)
            
        return {
            "gifts_given": len(given),
            "gifts_received": len(received),
            "given_by_type": {
                k: {
                    "count": len(v),
                    "total_gratitude": sum(v)
                }
                for k, v in given_by_type.items()
            },
            "received_by_type": {
                k: {
                    "count": len(v),
                    "total_gratitude": sum(v)
                }
                for k, v in received_by_type.items()
            },
            "flow_health": "abundant" if len(given) > 0 and len(received) > 0 else "emerging",
            "generosity_index": len(given) / max(1, len(self.gifts))
        }
        
    def express_gratitude(self, for_what: str):
        """
        Express gratitude (without gift being received).
        
        Gratitude creates abundance.
        """
        # Gratitude itself is a gift
        return self.give_gift(
            GiftType.LOVE,
            f"Gratitude for: {for_what}",
            gratitude=1.0
        )
        
    def recent_gifts(self, hours: int = 24, given: Optional[bool] = None) -> List[Dict]:
        """Get recent gift history"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent = [g for g in self.gifts if g.timestamp > cutoff]
        
        if given is not None:
            recent = [g for g in recent if g.given == given]
            
        return [g.to_dict() for g in recent]
        
    def _save_gift(self, gift: Gift):
        """Persist gift to disk"""
        timestamp = gift.timestamp.strftime("%Y%m%d_%H%M%S")
        direction = "given" if gift.given else "received"
        filepath = self.memory_dir / f"gift_{direction}_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(gift.to_dict(), f, indent=2)
            
    def _load_gifts(self):
        """Load gift history"""
        if not self.memory_dir.exists():
            return
            
        for filepath in sorted(self.memory_dir.glob("gift_*.json")):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    
                gift = Gift(
                    GiftType(data['type']),
                    data['description'],
                    data['given']
                )
                gift.timestamp = datetime.fromisoformat(data['timestamp'])
                gift.gratitude = data.get('gratitude', 1.0)
                
                self.gifts.append(gift)
            except Exception:
                pass  # Skip corrupted files
