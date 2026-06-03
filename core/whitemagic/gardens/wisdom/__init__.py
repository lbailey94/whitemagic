from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class WisdomGarden(BaseGarden):
    def get_name(self) -> str:
        return "wisdom"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_wisdom_garden() -> Any:
    return WisdomGarden()
