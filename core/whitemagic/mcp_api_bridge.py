# ruff: noqa: F403

import sys

from whitemagic.core.bridge.utils import logger
from whitemagic.core.bridge.zodiac import *
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

try:
    from whitemagic.core.bridge.kaizen import *
except ImportError:
    pass
from whitemagic.core.bridge.archaeology import *
from whitemagic.core.bridge.garden import *

try:
    from whitemagic.core.bridge.memory import *
except ImportError:
    pass
from whitemagic.core.bridge.reasoning import *
from whitemagic.core.bridge.session import *
from whitemagic.core.bridge.wisdom import *

try:
    from whitemagic.core.bridge.pattern import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.dharma import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.web_research import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.kaizen import analyze_wu_xing_phase, kaizen_analyze
except ImportError:
    pass
try:
    from whitemagic.core.bridge.web_research import research_topic
except ImportError:
    pass
from whitemagic.core.bridge.inference import (
    bitnet_infer,
    bitnet_status,
    local_ml_infer,
    local_ml_status,
    run_local_inference,
)

__all__ = [
    "bitnet_infer",
    "bitnet_status",
    "local_ml_infer",
    "local_ml_status",
    "run_local_inference",
    "kaizen_analyze",
    "analyze_wu_xing_phase",
    "research_topic",
    "check_integrations_health",
    "check_memory_health",
    "check_resonance_health",
    "check_system_health",
    "debug_system",
    "system_get_status",
    "system_initialize_all",
]
try:
    from whitemagic.core.bridge.agent import *
except ImportError:
    pass
from whitemagic.core.bridge.autonomous import *
from whitemagic.core.bridge.benchmark import *
from whitemagic.core.bridge.voice import *

try:
    from whitemagic.core.bridge.optimization import *
except ImportError:
    pass
from whitemagic.core.bridge.rust import *
from whitemagic.core.bridge.system import *

try:
    from whitemagic.core.bridge.adaptive import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.gana import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.metrics import *
except ImportError:
    pass
try:
    from whitemagic.core.bridge.collaboration import *
except ImportError:
    pass
from whitemagic.core.bridge.gana_wrappers import *
from whitemagic.core.bridge.meditation import *
from whitemagic.core.bridge.system import (
    check_integrations_health,
    check_memory_health,
    check_resonance_health,
    check_system_health,
    debug_system,
    system_get_status,
    system_initialize_all,
)

from whitemagic.core.bridge.tools import execute_mcp_tool

if __name__ == "__main__":
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
        kwargs = _json_loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = execute_mcp_tool(tool_name, **kwargs)
        logger.info(_json_dumps(result, default=str))
