from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class PatienceGarden(BaseGarden):
    def get_name(self) -> str:
        return "patience"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_patience_garden() -> Any:
    return PatienceGarden()
