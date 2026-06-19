from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class PatienceGarden(BaseGarden):
    """PatienceGarden: patience garden."""
    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "patience"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.

        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_patience_garden() -> Any:
    """
    Get the patience garden.

    Returns:
        Any
    """
    return PatienceGarden()
