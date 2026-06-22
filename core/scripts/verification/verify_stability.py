
import sys
from pathlib import Path

# Ensure whitemagic is in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from whitemagic.archaeology import get_archaeologist, mark_read
    from whitemagic.tools.handlers.archaeology import handle_archaeology

    print("--- Archaeology Verification ---")

    # Test singleton
    arch = get_archaeologist()
    print(f"Archaeologist instance: {arch}")

    # Test mark_read
    res = mark_read("/tmp/test_file.txt", context="Verification", note="Testing bridge")
    print(f"Mark Read result: {res}")

    # Test handler
    handler_res = handle_archaeology(action="stats")
    print(f"Handler stats result: {handler_res}")

    print("\n✅ Archaeology bridge is functional.")

except Exception as e:
    print(f"\n❌ Archaeology verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
