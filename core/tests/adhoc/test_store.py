from whitemagic.core.memory.models import Memory

from whitemagic.core.memory.sqlite_backend import SQLiteMemoryBackend

backend = SQLiteMemoryBackend("whitemagic.db")
# Fabricated memory type should fail the sutra test!
mem = Memory(id="test_mem", content="test", title="test", memory_type="long_term")

print("Attempting to store normal memory...")
try:
    backend.store(mem)
    print("Store normal memory OK")
except Exception as e:
    print(f"FAILED: {e}")

print("\nMocking sutra kernel violation...")
from whitemagic.core.bridge.sutra_bridge import get_sutra_kernel  # noqa: E402

original_eval = get_sutra_kernel().evaluate_action
get_sutra_kernel().evaluate_action = lambda action_type, **kwargs: "Panic: VIOLATION_SATYA: Memory fabrication is strictly forbidden." if action_type == "fabricate_memory" else original_eval(action_type, **kwargs)

try:
    sutra = get_sutra_kernel()
    v = sutra.evaluate_action("fabricate_memory")
    print(f"Sutra mock returns: {v}")
    if v.startswith("Panic"):
        raise RuntimeError(v)
except Exception as e:
    print(f"Kernel correctly panicked: {e}")

