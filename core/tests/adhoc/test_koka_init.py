import logging
import sys

from whitemagic.core.acceleration.koka_native_bridge import KokaNativeBridge

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

bridge = KokaNativeBridge()
print("Available:", bridge._available)
proc = bridge._get_process("prat")
print("Process:", proc)
if proc:
    res = bridge.dispatch("prat", "route-prat-call", {"gana": "gana_root", "tool": "health_report", "args": {}})
    print("Result:", res)
