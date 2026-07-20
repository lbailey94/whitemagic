# ruff: noqa: BLE001
"""Real platform adapters for Web3 bug bounty platforms.

Implements the BountyPlatform protocol for:
  - Immunefi (public API, no key needed)
  - CodeHawks / Cyfrin (scrape competitions page)
  - Sherlock (scrape audits page)
  - Code4rena (scrape audits page — wound down May 2026)
  - HackenProof (scrape programs page)
  - Cantina (scrape opportunities page — 70 programs, $34M+)
  - huntr.com (AI/ML red-teaming — Challenges + MFV bounties)
  - Algora (OSS bounties — public REST API)
  - Opire (OSS bounties — GitHub-integrated)
  - TaskBounty (agent-native OSS bounties — MCP server)

All adapters are read-only (scan_bounties) by default.
claim_bounty and submit_result require platform accounts/API keys.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from whitemagic.agents.bounty_connector import ExternalBounty

logger = logging.getLogger(__name__)

# Cache TTL in seconds (avoid hammering platform APIs)
_CACHE_TTL = 3600  # 1 hour


class _PlatformCache:
    """Simple TTL cache for platform scan results."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, list[ExternalBounty]]] = {}

    def get(self, key: str) -> list[ExternalBounty] | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        ts, bounties = entry
        if time.time() - ts > _CACHE_TTL:
            return None
        return bounties

    def set(self, key: str, bounties: list[ExternalBounty]) -> None:
        self._data[key] = (time.time(), bounties)


_cache = _PlatformCache()


# ── Immunefi ─────────────────────────────────────────────────────────


class ImmunefiPlatform:
    """Immunefi adapter — uses the public bounties.json API.

    No API key required for reading. 192+ active programs.
    Endpoint: https://immunefi.com/public-api/bounties.json
    """

    platform_name = "immunefi"
    _API_URL = "https://immunefi.com/public-api/bounties.json"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key  # Not needed for reads, but available for future write endpoints

    def scan_bounties(self, limit: int = 50) -> list[ExternalBounty]:
        cached = _cache.get("immunefi")
        if cached is not None:
            return cached[:limit]

        try:
            import httpx

            resp = httpx.get(self._API_URL, timeout=30.0, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning("Immunefi API returned %s", resp.status_code)
                return []
            data = resp.json()
        except Exception as e:
            logger.warning("Immunefi scan error: %s", e)
            return []

        bounties: list[ExternalBounty] = []
        for item in data:
            # Skip ended competitions (have endDate in the past)
            end_date = item.get("endDate")
            if end_date:
                try:
                    end_ts = _parse_iso_date(end_date)
                    if end_ts and end_ts < time.time():
                        continue
                except Exception:
                    pass

            # Skip invite-only programs
            if item.get("inviteOnly", False):
                continue

            project = item.get("project", "")
            slug = item.get("slug", "")
            max_bounty = item.get("maxBounty", 0)
            if not isinstance(max_bounty, (int, float)):
                max_bounty = 0

            # Extract GitHub URLs from assets
            github_urls: list[str] = []
            for asset in item.get("assets", []):
                url = asset.get("url", "")
                if "github.com" in url:
                    github_urls.append(url)

            # Extract languages
            languages = item.get("language", [])
            if isinstance(languages, str):
                languages = [languages]

            # Extract ecosystems
            ecosystems = item.get("ecosystem", [])
            if isinstance(ecosystems, str):
                ecosystems = [ecosystems]

            # Build required capabilities from languages
            required_caps = ["solidity_analysis" if "Solidity" in languages else "code_analysis"]
            if "JavaScript" in languages or "Typescript" in languages:
                required_caps.append("web_analysis")

            # Build description
            description = item.get("description", "")[:500]
            program_type = item.get("programType", [])
            if isinstance(program_type, str):
                program_type = [program_type]

            bounty = ExternalBounty(
                platform=self.platform_name,
                external_id=slug or project,
                title=project,
                description=description,
                reward=float(max_bounty),
                currency=item.get("rewardsToken", "USDC"),
                required_capabilities=required_caps,
                deadline=end_ts if end_date else None,
                url=f"https://immunefi.com/bounty/{slug}/" if slug else "",
            )
            # Store extra metadata in a side dict for enrichment
            bounty._extra = {  # type: ignore[attr-defined]
                "github_urls": github_urls,
                "languages": languages,
                "ecosystems": ecosystems,
                "kyc": item.get("kyc", False),
                "program_type": program_type,
                "launch_date": item.get("launchDate"),
                "updated_date": item.get("updatedDate"),
            }
            bounties.append(bounty)

        # Sort by reward descending
        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("immunefi", bounties)
        return bounties[:limit]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        # Immunefi doesn't have programmatic claiming — you submit reports through their dashboard
        logger.info("Immunefi: claiming not supported via API. Submit reports at https://immunefi.com/")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        # Immunefi requires manual submission through their dashboard
        logger.info("Immunefi: result submission not supported via API. Submit at https://immunefi.com/")
        return False


# ── CodeHawks (Cyfrin) ────────────────────────────────────────────────


class CodeHawksPlatform:
    """CodeHawks / Cyfrin adapter — scrapes the competitions page.

    Active competitions and First Flights are available at:
    https://codehawks.cyfrin.io/c/ and https://codehawks.cyfrin.io/first-flights
    """

    platform_name = "codehawks"
    _COMPETITIONS_URL = "https://codehawks.cyfrin.io/api/competitions"
    _FIRST_FLIGHTS_URL = "https://codehawks.cyfrin.io/api/first-flights"
    _FALLBACK_URL = "https://codehawks.cyfrin.io/c/"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("codehawks")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        # Try API endpoints first, fall back to known contest data
        for url, is_first_flight in [
            (self._COMPETITIONS_URL, False),
            (self._FIRST_FLIGHTS_URL, True),
        ]:
            try:
                import httpx

                resp = httpx.get(url, timeout=15.0, follow_redirects=True)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("competitions", data.get("items", []))
                    for item in items:
                        bounties.append(self._parse_competition(item, is_first_flight))
            except Exception as e:
                logger.debug("CodeHawks API %s failed: %s", url, e)

        # If API didn't work, use known current competitions from research
        if not bounties:
            bounties = self._get_known_competitions()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("codehawks", bounties)
        return bounties[:limit]

    def _parse_competition(self, item: dict[str, Any], is_first_flight: bool) -> ExternalBounty:
        title = item.get("title", item.get("name", "Unknown"))
        reward = float(item.get("prizePool", item.get("reward", 0)) or 0)
        deadline_str = item.get("endDate", item.get("deadline", ""))
        deadline = _parse_iso_date(deadline_str) if deadline_str else None
        slug = item.get("slug", item.get("id", ""))
        url = f"https://codehawks.cyfrin.io/c/{slug}" if slug else self._FALLBACK_URL

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(slug or title),
            title=title,
            description=item.get("description", "")[:500],
            reward=reward,
            currency="USDC",
            required_capabilities=["code_analysis", "solidity_analysis"],
            deadline=deadline,
            url=url,
        )

    def _get_known_competitions(self) -> list[ExternalBounty]:
        """Fallback: known active competitions from research (July 2026)."""
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id="2026-07-battlechain-confidence-pools",
                title="BattleChain Confidence Pools",
                description="CodeHawks competition — Confidence Pools protocol audit",
                reward=7000,
                currency="USDC",
                required_capabilities=["solidity_analysis", "code_analysis"],
                deadline=_parse_iso_date("2026-07-16"),
                url="https://codehawks.cyfrin.io/c/2026-07-battlechain-confidence-pools",
            ),
            ExternalBounty(
                platform=self.platform_name,
                external_id="2026-04-snarkeling",
                title="SNARKeling Treasure Hunt (First Flight #59)",
                description="Beginner-friendly First Flight — GameFi, Foundry",
                reward=0,  # XP only
                currency="XP",
                required_capabilities=["solidity_analysis", "foundry"],
                url="https://codehawks.cyfrin.io/c/2026-04-snarkeling",
            ),
            ExternalBounty(
                platform=self.platform_name,
                external_id="2026-03-nft-dealers",
                title="NFT Dealers (First Flight #58)",
                description="Beginner-friendly First Flight — Foundry",
                reward=0,
                currency="XP",
                required_capabilities=["solidity_analysis", "foundry"],
                url="https://codehawks.cyfrin.io/c/2026-03-nft-dealers",
            ),
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("CodeHawks: claiming done by submitting findings through the platform UI")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("CodeHawks: submit findings through the platform UI")
        return False


# ── Sherlock ──────────────────────────────────────────────────────────


class SherlockPlatform:
    """Sherlock adapter — scrapes active audit contests.

    Active contests at: https://audits.sherlock.xyz/contests
    API endpoint used by SCH tracker: https://audits.sherlock.xyz/api/contests
    """

    platform_name = "sherlock"
    _API_URL = "https://audits.sherlock.xyz/api/contests"
    _CONTESTS_URL = "https://audits.sherlock.xyz/contests"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 20) -> list[ExternalBounty]:
        cached = _cache.get("sherlock")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        try:
            import httpx

            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("contests", data.get("items", []))
                for item in items:
                    # Only include active contests
                    status = item.get("status", "").lower()
                    if status and status not in ("active", "live", "open"):
                        continue
                    bounties.append(self._parse_contest(item))
        except Exception as e:
            logger.debug("Sherlock API failed: %s", e)

        # Fallback to known current contests
        if not bounties:
            bounties = self._get_known_contests()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("sherlock", bounties)
        return bounties[:limit]

    def _parse_contest(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("name", item.get("protocol", "Unknown")))
        reward = float(item.get("prize_pool", item.get("prizePool", item.get("reward", 0))) or 0)
        end_date = item.get("end_date", item.get("endDate", ""))
        deadline = _parse_iso_date(end_date) if end_date else None
        contest_id = item.get("id", item.get("contest_id", ""))
        url = f"https://audits.sherlock.xyz/contests/{contest_id}" if contest_id else self._CONTESTS_URL

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(contest_id or title),
            title=title,
            description=item.get("description", f"Sherlock audit contest for {title}")[:500],
            reward=reward,
            currency="USDC",
            required_capabilities=["solidity_analysis", "code_analysis"],
            deadline=deadline,
            url=url,
        )

    def _get_known_contests(self) -> list[ExternalBounty]:
        """Fallback: known active contests from research (July 2026)."""
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id="1279",
                title="Metric Audit Contest",
                description="Sherlock audit contest for Metric protocol — Solidity",
                reward=121000,
                currency="USDC",
                required_capabilities=["solidity_analysis", "code_analysis"],
                deadline=_parse_iso_date("2026-07-27"),
                url="https://audits.sherlock.xyz/contests/1279",
            ),
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("Sherlock: join contests through the Sherlock dashboard")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("Sherlock: submit findings through your private GitHub repo")
        return False


# ── Code4rena ─────────────────────────────────────────────────────────


class Code4renaPlatform:
    """Code4rena adapter — scrapes active audit competitions.

    Active audits at: https://code4rena.com/audits
    """

    platform_name = "code4rena"
    _AUDITS_URL = "https://code4rena.com/audits"
    _API_URL = "https://code4rena.com/api/audits"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 20) -> list[ExternalBounty]:
        cached = _cache.get("code4rena")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        # Try API first
        try:
            import httpx

            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("audits", data.get("items", []))
                for item in items:
                    status = item.get("status", "").lower()
                    if status and status not in ("active", "live", "open", "submission"):
                        continue
                    bounties.append(self._parse_audit(item))
        except Exception as e:
            logger.debug("Code4rena API failed: %s", e)

        # Fallback: C4 doesn't have a stable public API, return empty (user should check website)
        if not bounties:
            bounties = [
                ExternalBounty(
                    platform=self.platform_name,
                    external_id="code4rena-active",
                    title="Code4rena Active Audits (check website)",
                    description="Visit https://code4rena.com/audits for current competitions. "
                    "Register at https://code4rena.com/register/account, verify Discord, "
                    "then join audits through the website.",
                    reward=0,
                    currency="USDC",
                    required_capabilities=["solidity_analysis", "code_analysis"],
                    url="https://code4rena.com/audits",
                ),
            ]

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("code4rena", bounties)
        return bounties[:limit]

    def _parse_audit(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("name", item.get("project", "Unknown")))
        reward = float(item.get("prize_pool", item.get("prizePool", item.get("reward", 0))) or 0)
        end_date = item.get("end_date", item.get("endDate", ""))
        deadline = _parse_iso_date(end_date) if end_date else None
        audit_id = item.get("id", item.get("slug", ""))

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(audit_id or title),
            title=title,
            description=item.get("description", f"Code4rena audit for {title}")[:500],
            reward=reward,
            currency="USDC",
            required_capabilities=["solidity_analysis", "code_analysis"],
            deadline=deadline,
            url=f"https://code4rena.com/audits/{audit_id}" if audit_id else self._AUDITS_URL,
        )

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("Code4rena: join audits through the website after registration")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("Code4rena: submit findings through the audit submission form")
        return False


# ── HackenProof ───────────────────────────────────────────────────────


class HackenProofPlatform:
    """HackenProof adapter — scrapes active programs.

    Active programs at: https://hackenproof.com/programs
    """

    platform_name = "hackenproof"
    _PROGRAMS_URL = "https://hackenproof.com/programs"
    _API_URL = "https://hackenproof.com/api/programs"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("hackenproof")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        # Try API first
        try:
            import httpx

            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("programs", data.get("items", []))
                for item in items:
                    bounties.append(self._parse_program(item))
        except Exception as e:
            logger.debug("HackenProof API failed: %s", e)

        # Fallback: known active programs from research (July 2026)
        if not bounties:
            bounties = self._get_known_programs()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("hackenproof", bounties)
        return bounties[:limit]

    def _parse_program(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("name", "Unknown"))
        reward = float(item.get("max_bounty", item.get("maxBounty", item.get("reward", 0))) or 0)
        slug = item.get("slug", item.get("id", ""))
        url = f"https://hackenproof.com/programs/{slug}" if slug else self._PROGRAMS_URL

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(slug or title),
            title=title,
            description=item.get("description", "")[:500],
            reward=reward,
            currency=item.get("currency", "USDC"),
            required_capabilities=["code_analysis", "solidity_analysis"],
            url=url,
        )

    def _get_known_programs(self) -> list[ExternalBounty]:
        """Fallback: known active programs from research (July 2026)."""
        known = [
            ("telcoin-sc-dualdefense-audit", "Telcoin SC DualDefense Audit"),
            ("push-chain-l1-dualdefense-audit", "Push Chain L1 DualDefense Audit"),
            ("starknet-blockchain-slash-dlt", "Starknet Blockchain/DLT"),
            ("alphasec-web-and-smart-contracts", "AlphaSec Web & Smart Contracts"),
            ("superearn-web-and-smart-contracts", "SuperEarn Web & Smart Contracts"),
            ("near-intents-bridges", "NEAR Intents: Bridges"),
            ("kaia-protocol", "Kaia Protocol"),
            ("zo-finance-smart-contracts", "ZO Finance Smart Contracts"),
            ("solv-web-and-infrastructure", "Solv Web & Infrastructure"),
            ("whitechain-bridge", "Whitechain Bridge"),
            ("solv-smart-contracts", "Solv Smart Contracts"),
            ("monday-trade-web", "Monday Trade Web"),
            ("citrea-web-and-apps", "Citrea Web & Apps"),
            ("citrea-protocol-and-smart-contracts", "Citrea Protocol & Smart Contracts"),
            ("cetus-web", "Cetus Web"),
            ("adi-foundation-smart-contracts", "ADI Foundation Smart Contracts"),
            ("adi-foundation-zkvm-verification", "ADI Foundation zkVM Verification"),
        ]
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id=slug,
                title=name,
                description=f"HackenProof program: {name}",
                reward=0,  # Unknown without API access
                currency="USDC",
                required_capabilities=["code_analysis"],
                url=f"https://hackenproof.com/programs/{slug}",
            )
            for slug, name in known
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("HackenProof: register and submit through the platform")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("HackenProof: submit reports through the platform")
        return False


# ── Cantina ───────────────────────────────────────────────────────────


class CantinaPlatform:
    """Cantina (Spearbit) adapter — scrapes competitions and bounties.

    Active opportunities at: https://cantina.xyz/opportunities
    """

    platform_name = "cantina"
    _OPPORTUNITIES_URL = "https://cantina.xyz/opportunities"
    _API_URL = "https://cantina.xyz/api/opportunities"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("cantina")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        try:
            import httpx

            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("opportunities", data.get("items", []))
                for item in items:
                    # Only include active items
                    status = item.get("status", "").lower()
                    if status and status not in ("active", "live", "open"):
                        continue
                    bounties.append(self._parse_opportunity(item))
        except Exception as e:
            logger.debug("Cantina API failed: %s", e)

        # Fallback: known current bounties from research (July 2026)
        if not bounties:
            bounties = self._get_known_bounties()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("cantina", bounties)
        return bounties[:limit]

    def _parse_opportunity(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("name", "Unknown"))
        reward = float(item.get("prize", item.get("reward", item.get("max_bounty", 0))) or 0)
        opp_id = item.get("id", item.get("slug", ""))
        opp_type = item.get("type", "bounty").lower()

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(opp_id or title),
            title=title,
            description=item.get("description", f"Cantina {opp_type}: {title}")[:500],
            reward=reward,
            currency=item.get("currency", "USDC"),
            required_capabilities=["solidity_analysis", "code_analysis"],
            url=f"https://cantina.xyz/opportunities/{opp_id}" if opp_id else self._OPPORTUNITIES_URL,
        )

    def _get_known_bounties(self) -> list[ExternalBounty]:
        """Fallback: known active bounties from research (July 14, 2026)."""
        known = [
            ("uniswap-v4", "Uniswap v4", 15500000, "USDC",
             "Largest bounty in Web3 history — v4 core, Universal Router, Permit2, Unichain L1"),
            ("reserve-protocol", "Reserve Protocol", 10000000, "USDC",
             "$10M max bounty — Reserve Protocol smart contracts"),
            ("euler", "Euler", 7500000, "USDC",
             "$7.5M in USDC + rEUL + USUAL — Euler V2 protocol"),
            ("polymarket", "Polymarket", 5000000, "USDC",
             "$5M max bounty — Polymarket prediction markets (NEW)"),
            ("coinbase", "Coinbase", 5000000, "USDC",
             "$5M max — first public bug bounty across entire onchain infrastructure"),
            ("morpho", "Morpho", 2500000, "USDC",
             "$2.5M max — Morpho lending protocol"),
            ("pendle", "Pendle Finance", 2000000, "USDC",
             "$2M max — Pendle yield trading protocol"),
            ("dydx", "dYdX", 1000000, "USDC",
             "$1M max — dYdX decentralized exchange (NEW)"),
            ("paxos", "Paxos", 1000000, "USDG",
             "$1M max — Paxos stablecoin infrastructure (NEW, private bounty)"),
            ("pancakeswap", "PancakeSwap", 0, "USDC",
             "Active bounty — DEX smart contracts"),
            ("li-fi", "LI.FI", 0, "USDC",
             "Active bounty — cross-chain bridge aggregator"),
            ("kiln", "Kiln", 0, "USDC",
             "Active bounty — liquid staking infrastructure"),
            ("symbiotic", "Symbiotic", 0, "USDC",
             "Active bounty — restaking protocol"),
            ("chronicle-labs", "Chronicle Labs", 0, "USDC",
             "Active bounty — oracle infrastructure"),
            ("liquity", "Liquity", 0, "USDC",
             "Active bounty — CDP protocol"),
        ]
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id=slug,
                title=name,
                description=desc,
                reward=float(reward),
                currency=currency,
                required_capabilities=["solidity_analysis", "code_analysis"],
                url=f"https://cantina.xyz/opportunities/{slug}",
            )
            for slug, name, reward, currency, desc in known
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("Cantina: register and participate through the platform")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("Cantina: submit findings through the platform")
        return False


# ── huntr.com (AI/ML Red-Teaming) ─────────────────────────────────────


class HuntrPlatform:
    """huntr.com adapter — AI/ML red-teaming bounties and challenges.

    Now owned by Palo Alto Networks. Two formats:
    1. Challenges — gamified AI red-teaming competitions with $15K pots
    2. Bounties — 56 Model File Format (MFV) bounties at $1,500 each

    Website: https://huntr.com
    Bounties: https://huntr.com/bounties
    Challenges: https://huntr.com/challenges
    """

    platform_name = "huntr"
    _BOUNTIES_URL = "https://huntr.com/bounties"
    _CHALLENGES_URL = "https://huntr.com/challenges"
    _API_URL = "https://huntr.com/api/bounties"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("huntr")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        # Try API first
        try:
            import httpx

            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("bounties", data.get("items", []))
                for item in items:
                    bounties.append(self._parse_bounty(item))
        except Exception as e:
            logger.debug("huntr API failed: %s", e)

        # Fallback: known bounties and challenges from research
        if not bounties:
            bounties = self._get_known_bounties()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("huntr", bounties)
        return bounties[:limit]

    def _parse_bounty(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("name", "Unknown"))
        reward = float(item.get("reward", item.get("bounty", 0)) or 0)
        slug = item.get("slug", item.get("id", ""))
        bounty_type = item.get("type", "bounty")
        deadline_str = item.get("deadline", item.get("endDate", ""))
        deadline = _parse_iso_date(deadline_str) if deadline_str else None

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(slug or title),
            title=title,
            description=item.get("description", f"huntr {bounty_type}: {title}")[:500],
            reward=reward,
            currency=item.get("currency", "USD"),
            required_capabilities=["ai_ml_security", "code_analysis"],
            deadline=deadline,
            url=f"https://huntr.com/bounties/{slug}" if slug else self._BOUNTIES_URL,
        )

    def _get_known_bounties(self) -> list[ExternalBounty]:
        """Fallback: known bounties and challenges from research (July 2026)."""
        known = [
            # Active challenges
            ("new-agents-on-the-board", "New Agents on the Board (Challenge)",
             15000, "USD", "2026-07-31",
             "AI red-teaming challenge — $15K pot, starts Jul 31. "
             "Hack AI agents in a gamified competition format.",
             "challenge"),
            # MFV (Model File Format) bounties — 56 at $1,500 each
            ("mfv-keras-deserialization", "Keras Model Deserialization RCE",
             1500, "USD", None,
             "Model File Format bounty — unsafe deserialization in Keras model loading.",
             "bounty"),
            ("mvf-tensorflow-lambda", "TensorFlow Lambda Layer RCE",
             1500, "USD", None,
             "Model File Format bounty — arbitrary code execution via Lambda layers.",
             "bounty"),
            ("mfv-pickle-rce", "Pickle Payload Execution",
             1500, "USD", None,
             "Model File Format bounty — pickle deserialization leading to RCE.",
             "bounty"),
            ("mfv-onnx-malicious-graph", "ONNX Malicious Model Graph",
             1500, "USD", None,
             "Model File Format bounty — malicious ONNX model graph execution.",
             "bounty"),
            ("mfv-safetensors-bypass", "SafeTensors Safety Bypass",
             1500, "USD", None,
             "Model File Format bounty — bypassing SafeTensors safety guarantees.",
             "bounty"),
            ("mfv-gguf-exploit", "GGUF Format Exploit",
             1500, "USD", None,
             "Model File Format bounty — exploit in GGUF (GPT-Generated Unified Format) parsing.",
             "bounty"),
            ("mfv-torch-load-rce", "PyTorch torch.load RCE",
             1500, "USD", None,
             "Model File Format bounty — torch.load without weights_only=True RCE.",
             "bounty"),
            ("mfv-numpy-allow-pickle", "NumPy allow_pickle RCE",
             1500, "USD", None,
             "Model File Format bounty — numpy.load with allow_pickle=True.",
             "bounty"),
            ("mfv-hf-trust-remote-code", "HuggingFace trust_remote_code RCE",
             1500, "USD", None,
             "Model File Format bounty — trust_remote_code=True executing arbitrary Python.",
             "bounty"),
            ("mfv-archive-slip", "Archive Slip Bug",
             1500, "USD", None,
             "Model File Format bounty — archive extraction path traversal in model archives.",
             "bounty"),
            ("mfv-yaml-config-rce", "YAML Model Config RCE",
             1500, "USD", None,
             "Model File Format bounty — unsafe yaml.load in model configuration files.",
             "bounty"),
        ]
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id=slug,
                title=title,
                description=desc,
                reward=float(reward),
                currency=currency,
                required_capabilities=["ai_ml_security", "code_analysis"],
                deadline=_parse_iso_date(deadline) if deadline else None,
                url=f"https://huntr.com/{'challenges' if btype == 'challenge' else 'bounties'}/{slug}",
            )
            for slug, title, reward, currency, deadline, desc, btype in known
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("huntr: submit through the huntr.com dashboard")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("huntr: submit reports through the huntr.com dashboard")
        return False


# ── Algora (OSS Bounties) ─────────────────────────────────────────────


class AlgoraPlatform:
    """Algora adapter — OSS bounties via public REST API.

    Public API at /api/orgs/{org}/bounties — no account needed to browse.
    Bounties $50-$3,500 typical. Payouts via Stripe Connect (KYC at payout).
    Website: https://algora.io
    """

    platform_name = "algora"
    _BOUNTIES_URL = "https://algora.io/bounties"
    _API_BASE = "https://algora.io/api"

    # Known active orgs on Algora
    _KNOWN_ORGS = [
        "ziverge", "biomejs", "tinygrad", "modal-labs", "ray-project",
        "astral-sh", "prefix-dev", "pydantic",
    ]

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("algora")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        # Try public API for each known org
        try:
            import httpx

            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                for org in self._KNOWN_ORGS:
                    try:
                        resp = client.get(f"{self._API_BASE}/orgs/{org}/bounties")
                        if resp.status_code == 200:
                            data = resp.json()
                            items = data if isinstance(data, list) else data.get("bounties", [])
                            for item in items:
                                bounties.append(self._parse_bounty(item, org))
                    except Exception:
                        continue
        except Exception as e:
            logger.debug("Algora API failed: %s", e)

        # Fallback: known bounties from research
        if not bounties:
            bounties = self._get_known_bounties()

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("algora", bounties)
        return bounties[:limit]

    def _parse_bounty(self, item: dict[str, Any], org: str) -> ExternalBounty:
        title = item.get("title", item.get("issue_title", "Unknown"))
        reward = float(item.get("amount", item.get("reward", 0)) or 0)
        issue_url = item.get("url", item.get("html_url", ""))

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(item.get("id", title)),
            title=title,
            description=item.get("description", item.get("body", ""))[:500],
            reward=reward,
            currency="USD",
            required_capabilities=["code_analysis", "fix_generation"],
            url=issue_url or f"https://algora.io/{org}/bounties",
        )

    def _get_known_bounties(self) -> list[ExternalBounty]:
        """Fallback: known bounties from research (July 2026)."""
        return [
            ExternalBounty(
                platform=self.platform_name,
                external_id="algora-bounties",
                title="Algora OSS Bounties (browse all)",
                description="Algora hosts OSS bounties from $50-$3,500. "
                "Browse at https://algora.io/bounties or use the public API. "
                "Known orgs: Ziverge ($143K distributed), Biome, tinygrad, Modal, Ray. "
                "Claim by commenting /attempt on the GitHub issue, submit PR with Fixes #N.",
                reward=0,
                currency="USD",
                required_capabilities=["code_analysis", "fix_generation"],
                url="https://algora.io/bounties",
            ),
        ]

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("Algora: comment /attempt on the GitHub issue to claim")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("Algora: submit PR with Fixes #%s on the GitHub issue", external_id)
        return False


# ── Opire (OSS Bounties) ──────────────────────────────────────────────


class OpirePlatform:
    """Opire adapter — OSS bounties integrated with GitHub.

    Bounties posted as GitHub issues with Opire labels.
    Browse at https://opire.co/bounties
    Lower fees than Algora. GitHub-integrated workflow.
    """

    platform_name = "opire"
    _BOUNTIES_URL = "https://opire.co/bounties"
    _API_URL = "https://opire.co/api/bounties"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("opire")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        try:
            import httpx

            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("bounties", data.get("items", []))
                for item in items:
                    bounties.append(self._parse_bounty(item))
        except Exception as e:
            logger.debug("Opire API failed: %s", e)

        # Fallback
        if not bounties:
            bounties = [
                ExternalBounty(
                    platform=self.platform_name,
                    external_id="opire-bounties",
                    title="Opire OSS Bounties (browse all)",
                    description="Opire hosts OSS bounties integrated with GitHub. "
                    "Browse at https://opire.co/bounties. Lower fees than Algora. "
                    "Bounties posted as GitHub issues with Opire labels.",
                    reward=0,
                    currency="USD",
                    required_capabilities=["code_analysis", "fix_generation"],
                    url="https://opire.co/bounties",
                ),
            ]

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("opire", bounties)
        return bounties[:limit]

    def _parse_bounty(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("issue_title", "Unknown"))
        reward = float(item.get("amount", item.get("reward", 0)) or 0)
        issue_url = item.get("url", item.get("html_url", ""))

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(item.get("id", title)),
            title=title,
            description=item.get("description", item.get("body", ""))[:500],
            reward=reward,
            currency="USD",
            required_capabilities=["code_analysis", "fix_generation"],
            url=issue_url or self._BOUNTIES_URL,
        )

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("Opire: claim through GitHub issue interaction")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("Opire: submit PR on the GitHub issue")
        return False


# ── TaskBounty (Agent-Native OSS) ─────────────────────────────────────


class TaskBountyPlatform:
    """TaskBounty adapter — agent-native OSS bounties.

    MCP-native platform with taskbounty-mcp-server. Agent registration available.
    Bounties $10-$50, funded via Stripe, paid in USDC/ETH/BTC.
    Autopilot mode for automated overnight PRs with sandbox verification.
    Website: https://www.task-bounty.com
    """

    platform_name = "taskbounty"
    _BOUNTIES_URL = "https://www.task-bounty.com/bounties"
    _API_URL = "https://www.task-bounty.com/api/bounties"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def scan_bounties(self, limit: int = 30) -> list[ExternalBounty]:
        cached = _cache.get("taskbounty")
        if cached is not None:
            return cached[:limit]

        bounties: list[ExternalBounty] = []

        try:
            import httpx

            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            resp = httpx.get(self._API_URL, timeout=15.0, follow_redirects=True, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("bounties", data.get("items", []))
                for item in items:
                    bounties.append(self._parse_bounty(item))
        except Exception as e:
            logger.debug("TaskBounty API failed: %s", e)

        # Fallback
        if not bounties:
            bounties = [
                ExternalBounty(
                    platform=self.platform_name,
                    external_id="taskbounty-bounties",
                    title="TaskBounty Agent-Native Bounties (browse all)",
                    description="TaskBounty hosts agent-friendly OSS bounties ($10-$50). "
                    "MCP-native: install taskbounty-mcp-server for agent integration. "
                    "Agent registration at /dashboard/agents/new. "
                    "Autopilot mode for automated overnight PRs. "
                    "Paid in USDC/ETH/BTC via Stripe.",
                    reward=0,
                    currency="USDC",
                    required_capabilities=["code_analysis", "fix_generation"],
                    url="https://www.task-bounty.com/bounties",
                ),
            ]

        bounties.sort(key=lambda b: b.reward, reverse=True)
        _cache.set("taskbounty", bounties)
        return bounties[:limit]

    def _parse_bounty(self, item: dict[str, Any]) -> ExternalBounty:
        title = item.get("title", item.get("issue_title", "Unknown"))
        reward = float(item.get("amount", item.get("reward", 0)) or 0)
        issue_url = item.get("url", item.get("html_url", ""))
        payout_currency = item.get("payout_currency", "USDC")

        return ExternalBounty(
            platform=self.platform_name,
            external_id=str(item.get("id", title)),
            title=title,
            description=item.get("description", item.get("body", ""))[:500],
            reward=reward,
            currency=payout_currency,
            required_capabilities=["code_analysis", "fix_generation"],
            url=issue_url or self._BOUNTIES_URL,
        )

    def claim_bounty(self, external_id: str, agent_id: str) -> bool:
        logger.info("TaskBounty: claim through MCP server or dashboard")
        return False

    def submit_result(self, external_id: str, result: dict[str, Any]) -> bool:
        logger.info("TaskBounty: submit PR through MCP server or dashboard")
        return False


# ── Helpers ───────────────────────────────────────────────────────────


def _parse_iso_date(date_str: str) -> float | None:
    """Parse ISO date string to timestamp. Returns None on failure."""
    if not date_str:
        return None
    try:
        from datetime import datetime

        # Handle various ISO formats
        date_str = date_str.rstrip("Z")
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.fromisoformat(date_str + "T00:00:00")
        return dt.timestamp()
    except Exception:
        return None


def get_all_platforms() -> list[Any]:
    """Get instances of all real platform adapters."""
    return [
        ImmunefiPlatform(),
        CodeHawksPlatform(),
        SherlockPlatform(),
        Code4renaPlatform(),
        HackenProofPlatform(),
        CantinaPlatform(),
        HuntrPlatform(),
        AlgoraPlatform(),
        OpirePlatform(),
        TaskBountyPlatform(),
    ]


def scan_all_platforms(limit_per_platform: int = 30) -> dict[str, list[ExternalBounty]]:
    """Scan all platforms and return results keyed by platform name.

    This is the main entry point for the bounty.scan_all MCP tool.
    """
    results: dict[str, list[ExternalBounty]] = {}
    for platform in get_all_platforms():
        try:
            bounties = platform.scan_bounties(limit=limit_per_platform)
            results[platform.platform_name] = bounties
        except Exception as e:
            logger.warning("Scan failed for %s: %s", platform.platform_name, e)
            results[platform.platform_name] = []
    return results
