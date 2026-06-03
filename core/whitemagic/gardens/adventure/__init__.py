from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class AdventureGarden(BaseGarden):
    def get_name(self) -> str:
        return "adventure"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_adventure_garden() -> Any:
    return AdventureGarden()
