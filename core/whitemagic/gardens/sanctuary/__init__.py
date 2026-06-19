from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class SanctuaryGarden(BaseGarden):
    """SanctuaryGarden: sanctuary garden."""
    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "sanctuary"

    def get_coordinate_bias(self) -> tuple[float, float, float]:  # type: ignore[override]
        """
        Get the coordinate bias.

        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_sanctuary_garden() -> Any:
    """
    Get the sanctuary garden.

    Returns:
        Any
    """
    return SanctuaryGarden()
