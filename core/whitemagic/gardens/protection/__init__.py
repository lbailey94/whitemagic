from typing import Any

from whitemagic.gardens.base_garden import BaseGarden


class ProtectionGarden(BaseGarden):
    def get_name(self) -> str:
        """
        Get the name.
        
        Returns:
            str
        """
        return "protection"

    def get_coordinate_bias(self) -> tuple[float, float, float]:
        """
        Get the coordinate bias.
        
        Returns:
            tuple[float, float, float]
        """
        return (0.0, 0.0, 0.0)

def get_protection_garden() -> Any:
    """
    Get the protection garden.
    
    Returns:
        Any
    """
    return ProtectionGarden()
