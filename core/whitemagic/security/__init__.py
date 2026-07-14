"""Security module for WhiteMagic

Provides security middleware and utilities:
- Content Security Policy (CSP)
- Security headers
- CSRF protection
- Rate limiting
- Authentication helpers
- Tool gating and path validation
- Edgerunner Violet security layer:
  - MCP integrity checking (tamper detection)
  - Model signing verification (OMS-compatible)
  - Scope-of-engagement tokens (purple-team authorization)
  - Security circuit breakers (anomaly detection)
"""

# Tool gating - always available
# Edgerunner Violet security layer
import logging

from .engagement_tokens import (
    RED_OPS_TOOL_PATTERNS,
    EngagementToken,
    EngagementTokenManager,
    classify_ops,
    get_token_manager,
    is_blue_ops_tool,
    is_red_ops_tool,
    requires_engagement_token,
)
from .mcp_integrity import McpIntegrity, get_mcp_integrity
from .model_signing import ModelSigningRegistry, ModelTrust, get_model_registry
from .security_breaker import SecurityMonitor, get_security_monitor
from .tool_gating import (
    TOOL_RISK_CLASSIFICATION,
    PathValidator,
    ToolGate,
    ToolRisk,
    check_tool_execution,
    get_tool_gate,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Tool gating
    "ToolRisk",
    "ToolGate",
    "PathValidator",
    "get_tool_gate",
    "check_tool_execution",
    "TOOL_RISK_CLASSIFICATION",
    # Edgerunner Violet
    "McpIntegrity",
    "get_mcp_integrity",
    "ModelSigningRegistry",
    "ModelTrust",
    "get_model_registry",
    "EngagementToken",
    "EngagementTokenManager",
    "get_token_manager",
    "RED_OPS_TOOL_PATTERNS",
    "is_red_ops_tool",
    "is_blue_ops_tool",
    "classify_ops",
    "requires_engagement_token",
    "SecurityMonitor",
    "get_security_monitor",
]

# CSP middleware - optional (requires FastAPI)
try:
    from .csp import (
        CSPBuilder as CSPBuilder,
    )
    from .csp import (
        CSPConfig as CSPConfig,
    )
    from .csp import (
        CSPMiddleware as CSPMiddleware,
    )
    from .csp import (
        CSPReporter as CSPReporter,
    )
    from .csp import (
        SecurityHeadersConfig as SecurityHeadersConfig,
    )
    from .csp import (
        create_security_middleware as create_security_middleware,
    )
    from .csp import (
        get_default_csp_config as get_default_csp_config,
    )

    __all__.extend(
        [
            "CSPBuilder",
            "CSPConfig",
            "CSPMiddleware",
            "CSPReporter",
            "SecurityHeadersConfig",
            "create_security_middleware",
            "get_default_csp_config",
        ]
    )
except ImportError:
    logger.debug("Ignored ImportError in __init__.py:105")
