from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class GratitudeGarden(BaseGarden):
    """GratitudeGarden: gratitude garden."""
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "gratitude"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_gratitude_garden() -> Any:
    """
    Get the gratitude garden.
    
    Returns:
        Any
    """
    return GratitudeGarden()
