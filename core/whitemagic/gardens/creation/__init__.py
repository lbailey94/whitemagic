from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class CreationGarden(BaseGarden):
    """CreationGarden: creation garden."""
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "creation"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_creation_garden() -> Any:
    """
    Get the creation garden.
    
    Returns:
        Any
    """
    return CreationGarden()
