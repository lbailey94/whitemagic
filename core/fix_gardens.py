import os

gardens_dir = "/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/gardens"
missing = [
    "courage", "sanctuary", "adventure", "transformation", "patience", 
    "gratitude", "healing", "mystery", "reverence", "wonder", "stillness", 
    "protection", "beauty", "creation"
]

template = """from typing import Any
from whitemagic.gardens.base_garden import BaseGarden

class {name}Garden(BaseGarden):
    def get_name(self) -> str:
        return "{lower}"
        
    def get_coordinate_bias(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

def get_{lower}_garden() -> Any:
    return {name}Garden()
"""

for g in missing:
    g_dir = os.path.join(gardens_dir, g)
    if os.path.exists(g_dir):
        with open(os.path.join(g_dir, "__init__.py"), "w") as f:
            f.write(template.format(name=g.title(), lower=g))

print("Fixed missing gardens")
