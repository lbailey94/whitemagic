from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class MysteryGarden(BaseGarden):
    def get_name(self) -> str:
        return "mystery"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_mystery_garden() -> Any:
    return MysteryGarden()
