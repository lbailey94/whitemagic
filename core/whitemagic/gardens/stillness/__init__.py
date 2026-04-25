from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class StillnessGarden(BaseGarden):
    def get_name(self) -> str:
        return "stillness"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_stillness_garden() -> Any:
    return StillnessGarden()
