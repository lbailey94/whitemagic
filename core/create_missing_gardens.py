import os

gardens_dir = "/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/gardens"
missing = [
    "courage", "sanctuary", "adventure", "transformation", "patience", 
    "gratitude", "healing", "mystery", "reverence", "wonder", "stillness", 
    "protection", "beauty", "creation"
]

template = """from whitemagic.gardens.base_garden import BaseGarden

class {name}Garden(BaseGarden):
    pass

def get_{lower}_garden():
    return {name}Garden()
"""

for g in missing:
    g_dir = os.path.join(gardens_dir, g)
    os.makedirs(g_dir, exist_ok=True)
    with open(os.path.join(g_dir, "__init__.py"), "w") as f:
        f.write(template.format(name=g.title(), lower=g))

print("Created missing gardens")
