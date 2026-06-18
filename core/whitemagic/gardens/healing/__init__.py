from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class HealingGarden(BaseGarden):
    """HealingGarden: healing garden."""
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "healing"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_healing_garden() -> Any:
    """
    Get the healing garden.
    
    Returns:
        Any
    """
    return HealingGarden()
