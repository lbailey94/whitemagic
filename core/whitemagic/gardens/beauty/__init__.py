from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class BeautyGarden(BaseGarden):
    """BeautyGarden: beauty garden."""
    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "beauty"

    def get_coordinate_bias(self) -> tuple[float, float, float]:  # type: ignore[override]
        """
        Get the coordinate bias.

        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_beauty_garden() -> Any:
    """
    Get the beauty garden.

    Returns:
        Any
    """
    return BeautyGarden()
