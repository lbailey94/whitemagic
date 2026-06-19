from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class TransformationGarden(BaseGarden):
    """TransformationGarden: transformation garden."""
    def get_name(self) -> str:
        """
        Get the name.

        Returns:
            str
        """
        return "transformation"

    def get_coordinate_bias(self) -> tuple[float, float, float]:  # type: ignore[override]
        """
        Get the coordinate bias.

        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_transformation_garden() -> Any:
    """
    Get the transformation garden.

    Returns:
        Any
    """
    return TransformationGarden()
