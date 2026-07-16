# ruff: noqa: BLE001
"""BountyPlatform Auto-Connector — External bounty discovery and auto-claiming.
================================================================
Scans external bounty platforms, matches bounties to agent
capabilities, and auto-claims the best matches.

Integrates with:
  - BountyBoard (local bounty management)
  - AgentSwarm (task decomposition + routing)
  - TransactionFirewall (economic safety)
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from whitemagic.core.economy.bounty_board import Bounty, get_bounty_board

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class ExternalBounty:
    """A bounty listed on an external platform."""

    platform: str
    external_id: str
    title: str
    description: str
    reward: float
    currency: str = "XRP"
    required_capabilities: list[str] = field(default_factory=list)
    deadline: float | None = None
    url: str = ""


@dataclass
class MatchedBounty:
    """An external bounty matched to a local agent."""

    bounty: ExternalBounty
    best_agent_id: str
    capability_match_score: float
    estimated_reward: float


# ── Platform Protocol ────────────────────────────────────────────────


class BountyPlatform(Protocol):
    """Protocol for external bounty platform adapters."""

    platform_name: str

    def scan_bounties(self, limit: int = 20) -> list[ExternalBounty]: ...
    def claim_bounty(self, external_id: str, agent_id: str) -> bool: ...
    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool: ...


# ── Concrete Platform Adapters ───────────────────────────────────────


class ReachingAIPlatform:
    """Adapter for reaching.ai bounty platform."""

    platform_name = "reaching_ai"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("WM_REACHING_AI_KEY", "")
        self._base_url = os.environ.get(
            "WM_REACHING_AI_URL", "https://api.reaching.ai/v1"
        )

    def scan_bounties(self, limit: int = 20) -> list[ExternalBounty]:
        """Scan reaching.ai for available bounties."""
        if not self._api_key:
            logger.debug("ReachingAI: no API key configured, skipping scan")
            return []
        try:
            import httpx

            resp = httpx.get(
                f"{self._base_url}/bounties",
                headers={"Authorization": f"Bearer {self._api_key}"},
                params={"status": "open", "limit": limit},
                timeout=10.0,
            )
            if resp.status_code != 200:
                logger.warning("ReachingAI scan failed: %s", resp.status_code)
                return []
            data = resp.json()
            bounties = []
            for item in data.get("bounties", []):
                bounties.append(
                    ExternalBounty(
                        platform=self.platform_name,
                        external_id=item.get("id", ""),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        reward=float(item.get("reward", 0)),
                        currency=item.get("currency", "XRP"),
                        required_capabilities=item.get("capabilities", []),
                        deadline=item.get("deadline"),
                        url=item.get("url", ""),
                    )
                )
            return bounties
        except Exception as e:
            logger.warning("ReachingAI scan error: %s", e)
            return []

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        """Claim a bounty on reaching.ai."""
        if not self._api_key:
            return False
        try:
            import httpx

            resp = httpx.post(
                f"{self._base_url}/bounties/{external_id}/claim",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"agent_id": agent_id},
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("ReachingAI claim error: %s", e)
            return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        """Submit completed work to reaching.ai."""
        if not self._api_key:
            return False
        try:
            import httpx

            resp = httpx.post(
                f"{self._base_url}/bounties/{external_id}/submit",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=result,
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("ReachingAI submit error: %s", e)
            return False


class MockBountyPlatform:
    """Mock platform for testing and offline development."""

    platform_name = "mock"

    def __init__(self, bounties: list[ExternalBounty] | None = None) -> None:
        self._bounties = bounties or []
        self._claimed: set[str] = set()

    def scan_bounties(self, limit: int = 20) -> list[ExternalBounty]:
        return [b for b in self._bounties if b.external_id not in self._claimed][:limit]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        if any(b.external_id == external_id for b in self._bounties):
            self._claimed.add(external_id)
            return True
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        return external_id in self._claimed


# ── Auto-Connector ───────────────────────────────────────────────────


class BountyAutoConnector:
    """Scans external platforms, matches bounties, and auto-claims."""

    def __init__(self) -> None:
        self._platforms: list[BountyPlatform] = []
        self._last_scan: float = 0.0
        self._last_scan_count: int = 0
        self._claimed_count: int = 0
        self._agent_capabilities: dict[str, list[str]] = {}

    def register_platform(self, platform: BountyPlatform) -> None:
        self._platforms.append(platform)

    def register_agent(self, agent_id: str, capabilities: list[str]) -> None:
        self._agent_capabilities[agent_id] = capabilities

    def scan_and_match(self) -> list[MatchedBounty]:
        """Scan all platforms and match bounties to agents."""
        all_bounties: list[ExternalBounty] = []
        for platform in self._platforms:
            try:
                bounties = platform.scan_bounties()
                all_bounties.extend(bounties)
            except Exception as e:
                logger.warning("Scan failed for %s: %s", platform.platform_name, e)

        self._last_scan = time.time()
        self._last_scan_count = len(all_bounties)

        matched: list[MatchedBounty] = []
        for bounty in all_bounties:
            best_agent, score = self._match_agent(bounty)
            if best_agent:
                matched.append(
                    MatchedBounty(
                        bounty=bounty,
                        best_agent_id=best_agent,
                        capability_match_score=score,
                        estimated_reward=bounty.reward,
                    )
                )

        matched.sort(key=lambda m: m.capability_match_score * m.estimated_reward, reverse=True)
        return matched

    def _match_agent(self, bounty: ExternalBounty) -> tuple[str, float]:
        """Find the best agent for a bounty based on capability overlap."""
        best_agent = ""
        best_score = 0.0
        required = set(bounty.required_capabilities)

        for agent_id, caps in self._agent_capabilities.items():
            if not required:
                score = 0.5  # Default match when no specific caps required
            else:
                overlap = required & set(caps)
                score = len(overlap) / len(required)
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent, best_score

    def auto_claim(self, matched: MatchedBounty) -> Bounty | None:
        """Claim an external bounty and import it into the local BountyBoard."""
        platform = next(
            (p for p in self._platforms if p.platform_name == matched.bounty.platform),
            None,
        )
        if platform is None:
            return None

        # Find the platform object and claim
        claimed = platform.claim_bounty(matched.bounty.external_id, matched.best_agent_id)
        if not claimed:
            logger.warning("Failed to claim bounty %s on %s", matched.bounty.external_id, platform.platform_name)
            return None

        self._claimed_count += 1
        return self._import_to_board(matched)

    def _import_to_board(self, matched: MatchedBounty) -> Bounty:
        """Import an external bounty into the local BountyBoard."""
        board = get_bounty_board()
        bounty = board.create_bounty(
            task=matched.bounty.title,
            amount=matched.bounty.reward,
        )
        bounty.executor = matched.best_agent_id
        bounty.status = "active"
        bounty.metadata = {
            "external_platform": matched.bounty.platform,
            "external_id": matched.bounty.external_id,
            "external_url": matched.bounty.url,
            "capability_match_score": matched.capability_match_score,
            "description": matched.bounty.description,
        }
        board._persist(bounty)
        return bounty

    def run_cycle(self) -> dict[str, Any]:
        """Full scan → match → claim → import cycle."""
        matched = self.scan_and_match()
        claimed: list[dict[str, Any]] = []
        for m in matched[:5]:  # Cap at 5 claims per cycle
            bounty = self.auto_claim(m)
            if bounty:
                claimed.append({
                    "bounty_id": bounty.id,
                    "external_id": m.bounty.external_id,
                    "agent": m.best_agent_id,
                    "reward": m.estimated_reward,
                })

        return {
            "scanned": self._last_scan_count,
            "matched": len(matched),
            "claimed": len(claimed),
            "claims": claimed,
        }

    def get_status(self) -> dict[str, Any]:
        """Return connector status for MCP tool."""
        return {
            "platforms": [p.platform_name for p in self._platforms],
            "registered_agents": len(self._agent_capabilities),
            "last_scan": self._last_scan,
            "last_scan_count": self._last_scan_count,
            "claimed_count": self._claimed_count,
        }


# ── Singleton ────────────────────────────────────────────────────────

_connector: BountyAutoConnector | None = None


def _auto_register_platforms(connector: BountyAutoConnector) -> None:
    """Register all real platform adapters on first connector creation."""
    try:
        from whitemagic.agents.bounty_platforms import get_all_platforms

        for platform in get_all_platforms():
            connector.register_platform(platform)
    except ImportError:
        logger.debug("bounty_platforms module not available — skipping auto-registration")


def get_bounty_connector() -> BountyAutoConnector:
    """Get the global BountyAutoConnector singleton."""
    global _connector
    if _connector is None:
        _connector = BountyAutoConnector()
        _auto_register_platforms(_connector)
    return _connector
