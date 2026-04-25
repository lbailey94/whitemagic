from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class TransformationGarden(BaseGarden):
    def get_name(self) -> str:
        return "transformation"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_transformation_garden() -> Any:
    return TransformationGarden()
