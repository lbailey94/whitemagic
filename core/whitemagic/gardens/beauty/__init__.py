from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class BeautyGarden(BaseGarden):
    def get_name(self) -> str:
        return "beauty"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_beauty_garden() -> Any:
    return BeautyGarden()
