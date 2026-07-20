"""Tool Types — Base classes for the WhiteMagic Tool Registry.
============================================================
Extracted to avoid circular imports between registry.py and
domain definition files in registry_defs/.
"""

import hashlib
import json
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
    """ToolSafety: tool safety classification.

    Members:
        READ
        WRITE
        DELETE
        UNCLASSIFIED

    UNCLASSIFIED is assigned to dispatch-only tools that lack authored
    ToolDefinitions. Such tools cannot enter safe/fast paths and are
    treated conservatively by permissions, effects, and the governor.
    """

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UNCLASSIFIED = "unclassified"


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


@dataclass(frozen=True)
class McpAnnotations:
    """MCP spec annotations for a tool (2025-03-26 revision).

    All fields default to ``None`` meaning "not declared" — the MCP client
    then assumes worst case. Explicit values should be preferred wherever
    derivable (see ``whitemagic.tools.annotations``).

    - ``title``: Human-readable display name.
    - ``read_only``: Tool does not modify its environment (readOnlyHint).
    - ``destructive``: Tool may perform destructive updates (destructiveHint).
      Only meaningful when ``read_only`` is False.
    - ``idempotent``: Repeated calls with the same arguments have no
      additional effect (idempotentHint). Only meaningful when
      ``read_only`` is False.
    - ``open_world``: Tool interacts with external entities beyond the
      local environment, e.g. network calls (openWorldHint).
    """

    title: str | None = None
    read_only: bool | None = None
    destructive: bool | None = None
    idempotent: bool | None = None
    open_world: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP ToolAnnotations wire format (None fields omitted)."""
        out: dict[str, Any] = {}
        if self.title is not None:
            out["title"] = self.title
        if self.read_only is not None:
            out["readOnlyHint"] = self.read_only
        if self.destructive is not None:
            out["destructiveHint"] = self.destructive
        if self.idempotent is not None:
            out["idempotentHint"] = self.idempotent
        if self.open_world is not None:
            out["openWorldHint"] = self.open_world
        return out


@dataclass
class ToolDefinition:
    """Definition of a WhiteMagic tool.

    This is the authoritative tool metadata structure. All other modules
    (stable_contract.py, canonical.py, stable_surface.py) must eventually
    be consolidated into ToolDefinition fields (P1.4).
    """

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
    aliases: tuple[str, ...] = ()  # P1.3: explicit alias modeling
    since_version: str | None = None  # P1.3: version when first stabilized
    annotations: McpAnnotations | None = None  # P9.3: explicit MCP annotation overrides

    def __post_init__(self) -> None:
        """Validate construction invariants (P1.3 strict construction)."""
        if not self.name or not self.name.strip():
            raise ValueError(f"ToolDefinition.name must be non-empty, got: {self.name!r}")
        if not self.description or not self.description.strip():
            raise ValueError(f"ToolDefinition.description must be non-empty for {self.name!r}")
        if self.safety == ToolSafety.UNCLASSIFIED and self.stability == ToolStability.STABLE:
            raise ValueError(
                f"ToolDefinition '{self.name}' cannot be STABLE with UNCLASSIFIED safety. "
                f"STABLE tools must have explicit safety declarations."
            )
        if self.fast_path and self.safety != ToolSafety.READ:
            raise ValueError(
                f"ToolDefinition '{self.name}' has fast_path=True but safety={self.safety.value}. "
                f"Fast-path requires READ safety."
            )
        if self.fast_path and self.fast_path_safety is None:
            raise ValueError(
                f"ToolDefinition '{self.name}' has fast_path=True but no fast_path_safety declaration."
            )

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

        if self.category == ToolCategory.SYSTEM and self.safety not in (
            ToolSafety.READ,
            ToolSafety.UNCLASSIFIED,
        ):
            # Most system operations are risky
            return str(RiskLevel.DANGEROUS.name)

        # 3. CAUTION (Writes, unclassified)
        if self.safety in (ToolSafety.WRITE, ToolSafety.UNCLASSIFIED):
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
        """Convert to MCP tool format (annotations resolved via derivation policy)."""
        safety_suffix = (
            "" if self.safety == ToolSafety.READ else f" | {self.safety.value.upper()}"
        )
        from whitemagic.tools.annotations import resolve_annotations

        resolved = resolve_annotations(self)
        return {
            "name": self.name,
            "title": resolved.title,
            "description": f"[{self.category.value.upper()}{safety_suffix}] {self.description}",
            "inputSchema": self.input_schema,
            "annotations": resolved.to_dict(),
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
            "aliases": list(self.aliases),
            "since_version": self.since_version,
            "annotations": self.annotations.to_dict() if self.annotations else None,
        }

    def to_snapshot(self) -> dict[str, Any]:
        """Produce a deterministic serialization snapshot for CI/docs (P1.3).

        The snapshot is sorted by key and includes all fields. The content_hash
        enables detecting drift between registry versions.
        """
        payload = {
            "aliases": sorted(self.aliases),
            "category": self.category.value,
            "description": self.description,
            "element": self.element,
            "fast_path": self.fast_path,
            "fast_path_eligible": self.fast_path_eligible,
            "fast_path_safety": (
                {
                    "no_network": self.fast_path_safety.no_network,
                    "no_policy_dependent_behavior": self.fast_path_safety.no_policy_dependent_behavior,
                    "no_secrets": self.fast_path_safety.no_secrets,
                    "no_user_sensitive_output": self.fast_path_safety.no_user_sensitive_output,
                    "no_writes": self.fast_path_safety.no_writes,
                }
                if self.fast_path_safety
                else None
            ),
            "gana": self.gana,
            "garden": self.garden,
            "input_schema": self.input_schema,
            "name": self.name,
            "permissions": sorted(self.permissions),
            "quadrant": self.quadrant,
            "safety": self.safety.value,
            "since_version": self.since_version,
            "stability": self.stability.value,
        }
        canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        payload["content_hash"] = hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()[:16]
        return payload
