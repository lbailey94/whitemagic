from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class HealingGarden(BaseGarden):
    def get_name(self) -> str:
        return "healing"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_healing_garden() -> Any:
    return HealingGarden()
