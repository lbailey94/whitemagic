from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class GratitudeGarden(BaseGarden):
    def get_name(self) -> str:
        return "gratitude"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_gratitude_garden() -> Any:
    return GratitudeGarden()
