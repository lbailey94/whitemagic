# ruff: noqa: BLE001
"""MCP-Integrated Lieutenant System — Officers with Tool Authority.

Extends the base Lieutenant system with MCP tool integration, enabling
specialist officers to make real-time MCP calls during campaign execution.

Each lieutenant has:
1. Domain expertise (from base Lieutenant)
2. Gana command authority (which Ganas they control)
3. MCP tool access (which tools they can invoke)
4. Real-time decision-making (MCP-informed strategy)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from whitemagic.agents.lieutenants import Lieutenant, LieutenantCorps, LieutenantDomain

try:
    from whitemagic.tools.tool_surface import call_tool
except ImportError:
    def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Perform the call tool operation.
        
        Args:
            name: Parameter description.
            args: Parameter description.
        
        Returns:
            dict[str, Any]
        """
        return {"status": "error", "message": f"Tool surface unavailable for {name}"}

logger = logging.getLogger(__name__)


# 28 Gana to Lieutenant mapping (from 28_GANA_ARMY_MAPPING.md)
GANA_TO_LIEUTENANT = {
    # Lieutenant Zhang Wei (Security) — 6 Ganas, 86K clones
    "gana_room": LieutenantDomain.SECURITY,           # 4. ROOM (resource locks)
    "gana_dipper": LieutenantDomain.SECURITY,         # 8. DIPPER (governance)
    "gana_room_security": LieutenantDomain.SECURITY,  # 13. ROOM (security monitor)
    "gana_straddling_legs": LieutenantDomain.SECURITY, # 15. STRADDLING LEGS (ethics)
    "gana_hairy_head": LieutenantDomain.SECURITY,     # 20. HAIRY HEAD (detail)
    "gana_star": LieutenantDomain.SECURITY,           # 24. STAR (governance)

    # Lieutenant Whitemagic Chen (Performance) — 5 Ganas, 131K clones
    "gana_heart": LieutenantDomain.PERFORMANCE,       # 5. HEART (session context)
    "gana_tail": LieutenantDomain.PERFORMANCE,        # 6. TAIL (performance)
    "gana_roof": LieutenantDomain.PERFORMANCE,        # 12. ROOF (sovereign compute)
    "gana_turtle_beak": LieutenantDomain.PERFORMANCE, # 19. TURTLE BEAK (precision)
    "gana_mound": LieutenantDomain.PERFORMANCE,       # 26. MOUND (metrics)

    # Lieutenant Marcus Silva (Intelligence) — 6 Ganas, 185K clones
    "gana_neck": LieutenantDomain.INTELLIGENCE,       # 2. NECK (memory creation)
    "gana_winnowing_basket": LieutenantDomain.INTELLIGENCE, # 7. WINNOWING BASKET (search)
    "gana_void": LieutenantDomain.INTELLIGENCE,       # 11. VOID (galaxy management)
    "gana_wall": LieutenantDomain.INTELLIGENCE,       # 14. WALL (voting)
    "gana_three_stars": LieutenantDomain.INTELLIGENCE, # 18. THREE STARS (judgment)
    "gana_extended_net": LieutenantDomain.INTELLIGENCE, # 21. EXTENDED NET (patterns)

    # Lieutenant Keiko Tanaka (Synthesis) — 3 Ganas, 92K clones
    "gana_net": LieutenantDomain.SYNTHESIS,           # 16. NET (capture & filtering)
    "gana_stomach": LieutenantDomain.SYNTHESIS,       # 17. STOMACH (digestion)
    "gana_abundance": LieutenantDomain.SYNTHESIS,     # 27. ABUNDANCE (lifecycle)

    # Lieutenant Omar Hassan (Discovery) — 4 Ganas, 168K clones
    "gana_ox": LieutenantDomain.DISCOVERY,            # 9. OX (endurance)
    "gana_ghost": LieutenantDomain.DISCOVERY,         # 22. GHOST (introspection)
    "gana_willow": LieutenantDomain.DISCOVERY,        # 23. WILLOW (resilience)
    "gana_chariot": LieutenantDomain.DISCOVERY,       # 28. CHARIOT (archaeology)

    # Lieutenant Priya Sharma (Infrastructure) — 4 Ganas, 103K clones
    "gana_horn": LieutenantDomain.INFRASTRUCTURE,     # 1. HORN (session init)
    "gana_root": LieutenantDomain.INFRASTRUCTURE,     # 3. ROOT (system health)
    "gana_girl": LieutenantDomain.INFRASTRUCTURE,     # 10. GIRL (nurture)
    "gana_wings": LieutenantDomain.INFRASTRUCTURE,    # 25. WINGS (deployment)
}


# MCP tool authority by lieutenant domain
LIEUTENANT_MCP_TOOLS = {
    LieutenantDomain.SECURITY: [
        # Security & governance tools
        "sangha_lock", "sandbox.set_limits", "sandbox.status", "hermit.check_access",
        "governor_validate", "dharma_rules", "homeostasis.check", "cognitive.mode",
        "security.monitor_status", "mcp_integrity.verify", "immune_scan",
        "evaluate_ethics", "wu_xing_balance", "harmony_vector", "verify_consent",
        "salience.spotlight", "anomaly.check", "karma_report", "karmic_trace",
        "governor_set_goal", "governor_check_dharma", "forge.validate",
    ],

    LieutenantDomain.PERFORMANCE: [
        # Performance & acceleration tools
        "scratchpad", "session.handoff", "context.pack", "working_memory.attend",
        "simd.cosine", "simd.batch", "execute_cascade", "token_report",
        "ollama.generate", "ollama.chat", "model.verify", "shelter.execute",
        "edge_infer", "bitnet_infer", "edge_batch_infer",
        "view_hologram", "get_yin_yang_balance", "green.report", "track_metric",
    ],

    LieutenantDomain.INTELLIGENCE: [
        # Memory, search & intelligence tools
        "create_memory", "update_memory", "import_memories", "delete_memory",
        "search_memories", "vector.search", "hybrid_recall", "graph_walk", "batch_read_memories",
        "galaxy.create", "galaxy.transfer", "galaxy.merge", "galaxy.sync", "oms.export", "oms.import",
        "vote.create", "vote.cast", "vote.analyze", "engagement.issue",
        "reasoning.bicameral", "ensemble.query", "kaizen_analyze", "sabha.convene",
        "pattern_search", "cluster_stats", "association.mine", "constellation.detect", "resonance_trace",
    ],

    LieutenantDomain.SYNTHESIS: [
        # Synthesis & pipeline tools
        "prompt.render", "prompt.list", "karma.verify_chain",
        "pipeline.create", "task.distribute", "task.route_smart", "task.complete",
        "dream_start", "dream_status", "serendipity_surface", "memory.lifecycle",
        "narrative.compress", "gratitude.stats",
    ],

    LieutenantDomain.DISCOVERY: [
        # Discovery & research tools
        "swarm.decompose", "swarm.route", "swarm.complete", "war_room.execute",
        "gnosis", "capabilities", "graph_topology", "web_search", "web_fetch", "selfmodel.forecast",
        "grimoire_suggest", "grimoire_cast", "cast_oracle", "rate_limiter.stats",
        "archaeology_search", "archaeology_scan_directory", "kg.extract", "kg.query",
        "windsurf_search_conversations",
    ],

    LieutenantDomain.INFRASTRUCTURE: [
        # Infrastructure & deployment tools
        "session_bootstrap", "create_session", "resume_session", "checkpoint_session",
        "health_report", "rust_status", "ship.check", "state.summary",
        "agent.register", "agent.heartbeat", "agent.capabilities", "agent.trust",
        "export_memories", "mesh.broadcast", "audit.export",
    ],
}


@dataclass
class LieutenantWithMCP(Lieutenant):
    """Lieutenant with MCP tool integration for real-time decision-making."""

    ganas_commanded: list[str] = field(default_factory=list)
    mcp_tools_available: list[str] = field(default_factory=list)
    mcp_calls_made: int = 0
    mcp_call_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize MCP tool authority based on domain."""
        if not self.mcp_tools_available:
            self.mcp_tools_available = LIEUTENANT_MCP_TOOLS.get(self.domain, [])

        if not self.ganas_commanded:
            # Find all Ganas commanded by this lieutenant
            self.ganas_commanded = [
                gana for gana, domain in GANA_TO_LIEUTENANT.items()
                if domain == self.domain
            ]

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if lieutenant has authority to use this MCP tool."""
        return tool_name in self.mcp_tools_available

    def call_mcp_tool(self, tool_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make an MCP tool call with authority checking and logging."""
        if not self.can_use_tool(tool_name):
            logger.warning(
                f"Lieutenant {self.name} attempted unauthorized tool call: {tool_name}"
            )
            return {
                "status": "error",
                "message": f"Unauthorized: {tool_name} not in lieutenant's authority",
                "authorized_tools": self.mcp_tools_available[:10],  # Show first 10
            }

        try:
            res = call_tool(tool_name, args or {})
            result = dict(res) if isinstance(res, dict) else {"status": "error", "message": "Invalid response"}

            # Log the call
            self.mcp_calls_made += 1
            self.mcp_call_history.append({
                "tool": tool_name,
                "args": args,
                "result_status": result.get("status", "unknown"),
                "call_number": self.mcp_calls_made,
            })

            logger.info(
                f"Lieutenant {self.name} called {tool_name} "
                f"(call #{self.mcp_calls_made}): {result.get('status', 'unknown')}"
            )

            return result

        except Exception as e:
            logger.error("Lieutenant %s MCP call failed: %s - %s", self.name, tool_name, e, exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "tool": tool_name,
            }

    def reconnaissance(self, campaign_code: str) -> dict[str, Any]:
        """Pre-deployment reconnaissance using MCP tools."""
        intel: dict[str, Any] = {
            "campaign": campaign_code,
            "lieutenant": self.name,
            "domain": self.domain.value,
        }

        # System health check
        if self.can_use_tool("health_report"):
            health = self.call_mcp_tool("health_report", {})
            intel["system_health"] = health

            if health.get("status") != "healthy":
                intel["recommendation"] = "defer_deployment"
                intel["reason"] = "system_unhealthy"
                return intel

        # Domain-specific reconnaissance
        if self.domain == LieutenantDomain.INTELLIGENCE:
            # Check graph topology
            if self.can_use_tool("graph_topology"):
                topology = self.call_mcp_tool("graph_topology", {})
                intel["graph_topology"] = topology

            # Check cluster stats
            if self.can_use_tool("cluster_stats"):
                clusters = self.call_mcp_tool("cluster_stats", {})
                intel["clusters"] = clusters

        elif self.domain == LieutenantDomain.PERFORMANCE:
            # Check SIMD status
            if self.can_use_tool("simd.status"):
                simd = self.call_mcp_tool("simd.status", {})
                intel["simd_status"] = simd

            # Check Rust status
            if self.can_use_tool("rust_status"):
                rust = self.call_mcp_tool("rust_status", {})
                intel["rust_status"] = rust

        elif self.domain == LieutenantDomain.DISCOVERY:
            # Check capabilities
            if self.can_use_tool("capabilities"):
                caps = self.call_mcp_tool("capabilities", {})
                intel["capabilities"] = caps

        intel["recommendation"] = "proceed"
        return intel

    def monitor_execution(self, batch_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        """Real-time monitoring during army execution using MCP tools."""
        monitoring: dict[str, Any] = {
            "batch_id": batch_id,
            "lieutenant": self.name,
            "adjustments": [],
        }

        # Performance monitoring
        if self.domain == LieutenantDomain.PERFORMANCE:
            # Check if throughput is acceptable
            throughput = metrics.get("throughput", 0)
            if throughput < 1000 and self.can_use_tool("simd.status"):
                simd_status = self.call_mcp_tool("simd.status", {})
                if not simd_status.get("available"):
                    from typing import cast
                    adj = cast(list[dict[str, Any]], monitoring.get("adjustments", []))
                    adj.append({
                        "type": "fallback_to_python",
                        "reason": "simd_unavailable",
                    })

        # Intelligence monitoring
        elif self.domain == LieutenantDomain.INTELLIGENCE:
            # Track metric for this batch
            if self.can_use_tool("track_metric"):
                self.call_mcp_tool("track_metric", {
                    "metric": f"batch_{batch_id}_throughput",
                    "value": metrics.get("throughput", 0),
                })

        return monitoring

    def verify_victory_conditions(self, campaign_code: str, results: dict[str, Any]) -> dict[str, Any]:
        """Post-deployment verification using MCP tools."""
        verification: dict[str, Any] = {
            "campaign": campaign_code,
            "lieutenant": self.name,
            "checks": [],
            "victory": False,
        }

        from typing import cast
        checks = cast(list[dict[str, Any]], verification.get("checks", []))

        # Domain-specific verification
        if self.domain == LieutenantDomain.INTELLIGENCE:
            # Verify graph reconstruction
            if self.can_use_tool("graph_topology"):
                topology = self.call_mcp_tool("graph_topology", {})
                checks.append({
                    "check": "graph_topology",
                    "passed": topology.get("nodes", 0) > 0,
                })

            # Verify constellation detection
            if self.can_use_tool("constellation.detect"):
                constellations = self.call_mcp_tool("constellation.detect", {})
                checks.append({
                    "check": "constellations",
                    "passed": len(constellations.get("constellations", [])) > 0,
                })

        elif self.domain == LieutenantDomain.PERFORMANCE:
            # Verify SIMD performance
            if self.can_use_tool("simd.status"):
                simd = self.call_mcp_tool("simd.status", {})
                checks.append({
                    "check": "simd_available",
                    "passed": simd.get("available", False),
                })

        # Overall victory determination
        verification["victory"] = all(
            check.get("passed", False) for check in verification["checks"]
        )

        return verification

    def status_report_with_mcp(self) -> dict[str, Any]:
        """Enhanced status report including MCP activity."""
        base_status = self.status_report()
        base_status.update({
            "ganas_commanded": self.ganas_commanded,
            "mcp_tools_available": len(self.mcp_tools_available),
            "mcp_calls_made": self.mcp_calls_made,
            "recent_mcp_calls": self.mcp_call_history[-5:] if self.mcp_call_history else [],
        })
        return base_status


class MCPLieutenantCorps(LieutenantCorps):
    """Enhanced Lieutenant Corps with MCP integration."""

    def _initialize_lieutenants(self) -> None:
        """Initialize MCP-enabled lieutenants."""

        # Security Lieutenant — Zhang Wei
        self.lieutenants[LieutenantDomain.SECURITY] = LieutenantWithMCP(
            domain=LieutenantDomain.SECURITY,
            name="Lieutenant Zhang Wei (Security)",
            expertise=[
                "SQL injection detection and remediation",
                "Vulnerability scanning and classification",
                "Red team penetration testing",
                "Security audit and compliance",
                "Threat modeling and risk assessment",
                "Dharma enforcement and ethical boundaries",
            ]
        )

        # Performance Lieutenant — Whitemagic Chen
        self.lieutenants[LieutenantDomain.PERFORMANCE] = LieutenantWithMCP(
            domain=LieutenantDomain.PERFORMANCE,
            name="Lieutenant Whitemagic Chen (Performance)",
            expertise=[
                "Rust hot path acceleration",
                "SIMD vectorization and optimization",
                "Parallel processing and concurrency",
                "Memory optimization and profiling",
                "Benchmark design and execution",
                "Local inference and edge computing",
            ]
        )

        # Intelligence Lieutenant — Marcus Silva
        self.lieutenants[LieutenantDomain.INTELLIGENCE] = LieutenantWithMCP(
            domain=LieutenantDomain.INTELLIGENCE,
            name="Lieutenant Marcus Silva (Intelligence)",
            expertise=[
                "Association typing and classification",
                "Graph reconstruction and topology",
                "Pattern mining and emergence detection",
                "Semantic analysis and entity extraction",
                "Knowledge graph construction",
                "Multi-galaxy memory coordination",
            ]
        )

        # Synthesis Lieutenant — Keiko Tanaka
        self.lieutenants[LieutenantDomain.SYNTHESIS] = LieutenantWithMCP(
            domain=LieutenantDomain.SYNTHESIS,
            name="Lieutenant Keiko Tanaka (Synthesis)",
            expertise=[
                "Code redundancy analysis and merging",
                "Refactoring and simplification",
                "API unification and consolidation",
                "Dead code detection and archival",
                "Import chain analysis and optimization",
                "Memory lifecycle management",
            ]
        )

        # Discovery Lieutenant — Omar Hassan
        self.lieutenants[LieutenantDomain.DISCOVERY] = LieutenantWithMCP(
            domain=LieutenantDomain.DISCOVERY,
            name="Lieutenant Omar Hassan (Discovery)",
            expertise=[
                "Archaeological excavation of archives",
                "Feature discovery and documentation",
                "Codebase census and mapping",
                "Historical analysis and timeline reconstruction",
                "Lost functionality recovery",
                "Swarm coordination and task decomposition",
            ]
        )

        # Infrastructure Lieutenant — Priya Sharma
        self.lieutenants[LieutenantDomain.INFRASTRUCTURE] = LieutenantWithMCP(
            domain=LieutenantDomain.INFRASTRUCTURE,
            name="Lieutenant Priya Sharma (Infrastructure)",
            expertise=[
                "System health monitoring and diagnostics",
                "Deployment automation and CI/CD",
                "Database optimization and maintenance",
                "Test suite management and coverage",
                "Build system optimization",
                "Agent coordination and mesh networking",
            ]
        )

        logger.info(f"MCP Lieutenant Corps initialized: {len(self.lieutenants)} lieutenants with MCP authority")

    def get_lieutenant_for_gana(self, gana_name: str) -> LieutenantWithMCP | None:
        """Get the lieutenant responsible for a specific Gana."""
        domain = GANA_TO_LIEUTENANT.get(gana_name)
        if domain:
            return self.lieutenants.get(domain)
        return None

    def corps_status_with_mcp(self) -> dict[str, Any]:
        """Enhanced corps status including MCP activity."""
        base_status = self.corps_status()
        base_status["total_mcp_calls"] = sum(
            lt.mcp_calls_made for lt in self.lieutenants.values()
            if isinstance(lt, LieutenantWithMCP)
        )
        base_status["gana_coverage"] = {
            gana: domain.value
            for gana, domain in GANA_TO_LIEUTENANT.items()
        }
        return base_status


# Singleton instance
_mcp_corps: MCPLieutenantCorps | None = None

def get_mcp_lieutenant_corps() -> MCPLieutenantCorps:
    """Get the singleton MCP-enabled lieutenant corps instance."""
    global _mcp_corps
    if _mcp_corps is None:
        _mcp_corps = MCPLieutenantCorps()
    return _mcp_corps


__all__ = [
    "LieutenantWithMCP",
    "MCPLieutenantCorps",
    "get_mcp_lieutenant_corps",
    "GANA_TO_LIEUTENANT",
    "LIEUTENANT_MCP_TOOLS",
]
