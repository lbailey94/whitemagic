"""Tool Types — Base classes for the WhiteMagic Tool Registry.
============================================================
Extracted to avoid circular imports between registry.py and
domain definition files in registry_defs/.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ToolCategory(StrEnum):
    """ToolCategory: tool category.

    Enumeration.

    Members:
        MEMORY
        SESSION
        GARDEN
        METRICS
        EDGE
        INTROSPECTION
        SYSTEM
        ARCHAEOLOGY
        GOVERNOR
        WATCHER
        BROWSER
        INFERENCE
        SYNTHESIS
        DHARMA
        GANA
        BROKER
        TASK
        VOTING
        AGENT
        GOVERNANCE
        SECURITY"""

    MEMORY = "memory"
    SESSION = "session"
    GARDEN = "garden"
    METRICS = "metrics"
    EDGE = "edge"
    INTROSPECTION = "introspection"
    SYSTEM = "system"
    ARCHAEOLOGY = "archaeology"
    GOVERNOR = "governor"
    WATCHER = "watcher"
    BROWSER = "browser"
    INFERENCE = "inference"
    SYNTHESIS = "synthesis"
    DHARMA = "dharma"
    GANA = "gana"
    BROKER = "broker"
    TASK = "task"
    VOTING = "voting"
    AGENT = "agent"
    GOVERNANCE = "governance"
    SECURITY = "security"


class ToolSafety(StrEnum):
    """ToolSafety: tool safety.

    Enumeration.

    Members:
        READ
        WRITE
        DELETE"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class ToolStability(StrEnum):
    """Public contract tier for a tool.

    STABLE      — Part of the guaranteed public API. Gana meta-tools are always STABLE.
                  Callers may rely on name, schema, and envelope shape across releases.
    OPTIONAL    — Available in the current release but not part of the minimum public
                  contract. Schemas and names are likely stable but may evolve.
    EXPERIMENTAL — Labs / preview surface. May change or disappear without a major
                  version bump. Callers should guard against ToolNotFound responses.
    """

    STABLE = "stable"
    OPTIONAL = "optional"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class FastPathSafety:
    """Safety declarations required for fast-path eligibility.

    A tool with ``fast_path=True`` must declare all of these as True.
    The registry loader mechanically verifies these constraints:
    - ``no_writes``: Tool does not modify any persistent state.
    - ``no_network``: Tool does not make external network calls.
    - ``no_secrets``: Tool does not access or return secret material.
    - ``no_user_sensitive_output``: Tool does not return user-private data.
    - ``no_policy_dependent_behavior``: Tool behavior is independent of policy profile.
    """

    no_writes: bool = True
    no_network: bool = True
    no_secrets: bool = True
    no_user_sensitive_output: bool = True
    no_policy_dependent_behavior: bool = True

    @property
    def all_satisfied(self) -> bool:
        """True if all safety constraints are declared as satisfied."""
        return (
            self.no_writes
            and self.no_network
            and self.no_secrets
            and self.no_user_sensitive_output
            and self.no_policy_dependent_behavior
        )


@dataclass
class ToolDefinition:
    """Definition of a WhiteMagic tool."""

    name: str
    description: str
    category: ToolCategory
    safety: ToolSafety
    input_schema: dict[str, Any]
    gana: str | None = None
    garden: str | None = None
    quadrant: str | None = None
    element: str | None = None
    permissions: tuple[str, ...] = ()  # Leap 9: declared capability scopes
    stability: ToolStability = ToolStability.OPTIONAL
    fast_path: bool = False  # Phase 3: registry-declared fast-path eligibility
    fast_path_safety: FastPathSafety | None = None  # Phase 3: safety declarations

    @property
    def risk_level(self) -> str:
        """Map tool metadata to Governor risk levels."""
        from whitemagic.core.governor import RiskLevel

        # 1. FORBIDDEN categories/tools
        if self.category == ToolCategory.GOVERNOR and self.safety != ToolSafety.READ:
            return str(RiskLevel.FORBIDDEN.name)

        # 2. DANGEROUS actions (Delete/Execute)
        if self.safety == ToolSafety.DELETE:
            return str(RiskLevel.DANGEROUS.name)

        if self.category == ToolCategory.SYSTEM and self.safety != ToolSafety.READ:
            # Most system operations are risky
            return str(RiskLevel.DANGEROUS.name)

        # 3. CAUTION (Writes)
        if self.safety == ToolSafety.WRITE:
            return str(RiskLevel.CAUTION.name)

        # 4. SAFE defaults (Read)
        return str(RiskLevel.SAFE.name)

    def to_openai_function(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"[{self.category.value.upper()}] {self.description}",
                "parameters": self.input_schema,
            },
        }

    def to_mcp_tool(self) -> dict[str, Any]:
        """Convert to MCP tool format."""
        safety_suffix = (
            "" if self.safety == ToolSafety.READ else f" | {self.safety.value.upper()}"
        )
        return {
            "name": self.name,
            "description": f"[{self.category.value.upper()}{safety_suffix}] {self.description}",
            "inputSchema": self.input_schema,
            "stability": self.stability.value,
        }

    @property
    def fast_path_eligible(self) -> bool:
        """Mechanically verify fast-path eligibility.

        A tool is fast-path eligible only if:
        1. ``fast_path`` is True, AND
        2. ``safety`` is READ (no writes/deletes), AND
        3. ``fast_path_safety`` is declared and all constraints satisfied.
        """
        if not self.fast_path:
            return False
        if self.safety != ToolSafety.READ:
            return False
        if self.fast_path_safety is None:
            return False
        return self.fast_path_safety.all_satisfied

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "safety": self.safety.value,
            "stability": self.stability.value,
            "input_schema": self.input_schema,
            "fast_path": self.fast_path,
            "fast_path_eligible": self.fast_path_eligible,
        }
