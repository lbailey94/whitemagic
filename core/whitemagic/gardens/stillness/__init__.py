from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class StillnessGarden(BaseGarden):
    """StillnessGarden: stillness garden."""
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "stillness"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_stillness_garden() -> Any:
    """
    Get the stillness garden.
    
    Returns:
        Any
    """
    return StillnessGarden()
