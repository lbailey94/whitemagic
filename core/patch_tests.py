files = [
    "tests/unit/tools/test_handlers_batch1.py",
    "tests/unit/tools/test_handlers_batch3.py"
]

for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    # Add imports at the top right after imports
    if "import whitemagic.core.memory.unified" not in content:
        import_block = """
try:
    import whitemagic.core.memory.unified
    import whitemagic.core.memory.vector_search
    import whitemagic.core.intelligence.knowledge_graph
    import whitemagic.core.intelligence.solver
    import whitemagic.core.governor
    import whitemagic.core.acceleration.simd
    import whitemagic.agents.swarm
    import whitemagic.tools.sandbox
except ImportError:
    pass
"""
        content = content.replace("from unittest.mock import MagicMock, patch", "from unittest.mock import MagicMock, patch\n" + import_block)
        with open(f, "w") as file:
            file.write(content)

print("Patched tests")
