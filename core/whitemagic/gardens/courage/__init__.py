from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class CourageGarden(BaseGarden):
    """CourageGarden: courage garden."""
    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "courage"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.

        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_courage_garden() -> Any:
    """
    Get the courage garden.

    Returns:
        Any
    """
    return CourageGarden()
