from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class WonderGarden(BaseGarden):
    def get_name(self) -> str:
        return "wonder"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_wonder_garden() -> Any:
    return WonderGarden()
