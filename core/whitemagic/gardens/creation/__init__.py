from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class CreationGarden(BaseGarden):
    def get_name(self) -> str:
        return "creation"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_creation_garden() -> Any:
    return CreationGarden()
