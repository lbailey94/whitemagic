from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class WonderGarden(BaseGarden):
    """WonderGarden: wonder garden."""
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "wonder"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_wonder_garden() -> Any:
    """
    Get the wonder garden.
    
    Returns:
        Any
    """
    return WonderGarden()
