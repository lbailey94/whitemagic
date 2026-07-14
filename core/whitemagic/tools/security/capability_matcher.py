"""CapabilityMatcher — matches WhiteMagic capabilities against bounty requirements.

Automatically determines which WhiteMagic tools and agents are best suited
for a given bounty or security engagement, based on capability scoring.
"""
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BountyRequirement:
    """A single requirement from a bounty brief."""
    skill: str
    weight: float = 1.0
    description: str = ""


@dataclass
class CapabilityMatch:
    """A match between a bounty and WhiteMagic capabilities."""
    bounty_id: str
    matched_tools: list[str] = field(default_factory=list)
    matched_agents: list[str] = field(default_factory=list)
    total_score: float = 0.0
    coverage: float = 0.0
    gaps: list[str] = field(default_factory=list)
    recommended: bool = False


# Maps bounty skill keywords to WhiteMagic tool patterns
SKILL_TO_TOOLS: dict[str, list[str]] = {
    "solidity": ["strata_analyze", "formal_verify", "echidna_fuzz", "foundry_build", "foundry_test"],
    "smart_contract": ["strata_analyze", "formal_verify", "echidna_fuzz", "poc_verify"],
    "python": ["strata_analyze", "python_security", "adaptive_defense"],
    "web": ["strata_analyze", "web_security", "http_probe_get", "http_probe_post"],
    "api": ["http_probe_get", "http_probe_post", "api_state_machine"],
    "fuzzing": ["echidna_fuzz", "foundry_test", "adaptive_defense"],
    "formal_verification": ["formal_verify", "halmos_verify"],
    "static_analysis": ["strata_analyze", "strata_survey"],
    "exploit": ["poc_verify", "exploit_develop", "red_team_scan"],
    "pentest": ["red_team_scan", "nmap_scan", "recon_scan", "http_probe_get"],
    "audit": ["strata_analyze", "formal_verify", "multi_agent_analysis"],
    "bridge": ["strata_analyze", "formal_verify", "echidna_fuzz"],
    "defi": ["strata_analyze", "formal_verify", "echidna_fuzz", "poc_verify"],
    "nft": ["strata_analyze", "formal_verify"],
    "governance": ["strata_analyze", "formal_verify"],
    "access_control": ["strata_analyze", "formal_verify", "red_team_scan"],
    "reentrancy": ["echidna_fuzz", "formal_verify", "strata_analyze"],
    "integer_overflow": ["echidna_fuzz", "formal_verify", "strata_analyze"],
    "xss": ["web_security", "http_probe_get", "strata_analyze"],
    "sql_injection": ["web_security", "strata_analyze", "adaptive_defense"],
    "ddos": ["strata_analyze", "adaptive_defense"],
    "crypto": ["formal_verify", "strata_analyze"],
    "staking": ["strata_analyze", "formal_verify"],
    "oracle": ["strata_analyze", "formal_verify"],
    "flash_loan": ["echidna_fuzz", "poc_verify", "strata_analyze"],
}

# Maps skills to agent roles
SKILL_TO_AGENTS: dict[str, list[str]] = {
    "solidity": ["solidity-1"],
    "smart_contract": ["solidity-1"],
    "python": ["python-1"],
    "web": ["web-1"],
    "exploit": ["exploit-1"],
    "audit": ["solidity-1", "python-1", "web-1"],
    "pentest": ["exploit-1"],
    "fuzzing": ["solidity-1", "exploit-1"],
}


class CapabilityMatcher:
    """Match WhiteMagic capabilities against bounty requirements."""

    def __init__(self) -> None:
        self._skill_to_tools = SKILL_TO_TOOLS
        self._skill_to_agents = SKILL_TO_AGENTS

    def match(
        self,
        bounty_id: str,
        requirements: list[BountyRequirement],
    ) -> CapabilityMatch:
        """Match a bounty's requirements against WhiteMagic capabilities."""
        all_tools: set[str] = set()
        all_agents: set[str] = set()
        total_weight = 0.0
        matched_weight = 0.0
        gaps: list[str] = []

        for req in requirements:
            total_weight += req.weight
            skill_lower = req.skill.lower()

            tools = self._find_tools(skill_lower)
            agents = self._find_agents(skill_lower)

            if tools or agents:
                matched_weight += req.weight
                all_tools.update(tools)
                all_agents.update(agents)
            else:
                gaps.append(f"No capability for: {req.skill}")

        coverage = matched_weight / total_weight if total_weight > 0 else 0.0
        score = coverage * (1.0 - 0.1 * len(gaps) / max(len(requirements), 1))

        return CapabilityMatch(
            bounty_id=bounty_id,
            matched_tools=sorted(all_tools),
            matched_agents=sorted(all_agents),
            total_score=round(score, 3),
            coverage=round(coverage, 3),
            gaps=gaps,
            recommended=score >= 0.5,
        )

    def _find_tools(self, skill: str) -> list[str]:
        """Find tools matching a skill keyword."""
        for key, tools in self._skill_to_tools.items():
            if key in skill or skill in key:
                return tools
        return []

    def _find_agents(self, skill: str) -> list[str]:
        """Find agents matching a skill keyword."""
        for key, agents in self._skill_to_agents.items():
            if key in skill or skill in key:
                return agents
        return []

    def list_capabilities(self) -> dict[str, Any]:
        """List all known capability mappings."""
        return {
            "skills": sorted(self._skill_to_tools.keys()),
            "total_tool_mappings": sum(len(v) for v in self._skill_to_tools.values()),
            "total_agent_mappings": sum(len(v) for v in self._skill_to_agents.values()),
        }


_matcher: CapabilityMatcher | None = None


def get_capability_matcher() -> CapabilityMatcher:
    global _matcher
    if _matcher is None:
        _matcher = CapabilityMatcher()
    return _matcher
