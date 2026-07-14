"""CrossChainAnalyzer — multi-chain vulnerability correlation and bridge risk analysis.

Extends the basic cross_chain_analysis in vuln_graph.py with:
- Bridge-specific vulnerability patterns (lock-mint, burn-mint, liquidity pools)
- Cross-chain message passing risks (oracle manipulation, replay attacks)
- Chain-specific vulnerability signatures (EVM vs Solana vs Move)
- Composite risk scoring across interconnected protocols
- Integration with SecurityEventBus for cross-chain alerts
"""
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Bridge vulnerability patterns specific to cross-chain
BRIDGE_PATTERNS: dict[str, dict[str, Any]] = {
    "lock_mint_drain": {
        "description": "Lock-and-mint bridge drain: attacker locks on source, mints on target, then drains",
        "severity": "critical",
        "indicators": ["unverified_lock", "mint_without_burn", "centralized_minter"],
        "mitigation": "Require burn proof before mint, decentralized validators",
    },
    "burn_mint_replay": {
        "description": "Replay attack on burn-mint bridge: reuse burn proof across chains",
        "severity": "critical",
        "indicators": ["no_chain_id_binding", "reusable_proof", "missing_nonce"],
        "mitigation": "Bind proof to target chain ID, single-use nonces",
    },
    "liquidity_pool_drain": {
        "description": "Cross-chain liquidity pool manipulation via price oracle divergence",
        "severity": "high",
        "indicators": ["stale_oracle", "price_divergence", "single_lp_provider"],
        "mitigation": "Fresh oracle updates, multi-provider consensus, circuit breaker",
    },
    "message_passing_replay": {
        "description": "Replay of cross-chain messages on different endpoints",
        "severity": "high",
        "indicators": ["no_endpoint_binding", "broadcaster_replay", "missing_timestamp"],
        "mitigation": "Endpoint-specific nonces, message expiry, timestamp validation",
    },
    "validator_collusion": {
        "description": "Bridge validator collusion to sign fraudulent state transitions",
        "severity": "critical",
        "indicators": ["small_validator_set", "no_slashing", "centralized_signers"],
        "mitigation": "Large validator set, slashing, fraud proofs",
    },
    "wrapped_asset_freeze": {
        "description": "Wrapped asset on target chain frozen while original unlocked on source",
        "severity": "medium",
        "indicators": ["no_freeze_sync", "manual_governance", "upgradeable_bridge"],
        "mitigation": "Automatic freeze propagation, governance delay, multi-sig",
    },
    "gas_token_insufficient": {
        "description": "Insufficient gas token on target chain for relay transactions",
        "severity": "low",
        "indicators": ["no_gas_buffer", "fixed_gas_estimate", "no_retry_mechanism"],
        "mitigation": "Dynamic gas estimation, gas buffer, retry with backoff",
    },
}

# Chain-specific vulnerability signatures
CHAIN_SIGNATURES: dict[str, list[str]] = {
    "ethereum": ["reentrancy", "integer_overflow", "access_control", "gas_limit", "tx_origin"],
    "polygon": ["reentrancy", "bridge_validator", "state_transition", "plasma_exit"],
    "arbitrum": ["sequencer_centralization", "delayed_inbox", "outbox_replay", "l2_to_l1_message"],
    "optimism": ["sequencer_centralization", "fraud_proof_window", "state_root_delay"],
    "solana": ["account_model_reentrancy", "owner_check_bypass", "close_account", "seed_collision"],
    "aptos": ["move_resource_access", "module_upgrade", "signer_check_bypass"],
    "sui": ["object_id_reuse", "dynamic_field_collision", "shared_object_deadlock"],
    "bsc": ["reentrancy", "validator_collusion", "short_block_time", "mev_sandwich"],
    "avalanche": ["subnet_validator_collusion", "bridge_centralization", "stake_drain"],
    "base": ["sequencer_centralization", "l1_bridge_risk", "fault_proof"],
}


@dataclass
class CrossChainFinding:
    """A vulnerability finding correlated across multiple chains."""
    finding_id: str
    category: str
    chains_affected: list[str]
    bridge_pattern: str | None
    severity: str
    description: str
    indicators: list[str]
    mitigation: str
    composite_risk_score: float = 0.0


@dataclass
class ChainRiskProfile:
    """Risk profile for a single chain in a cross-chain analysis."""
    chain_id: str
    total_vulnerabilities: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    bridge_exposure: float = 0.0
    known_patterns: list[str] = field(default_factory=list)


class CrossChainAnalyzer:
    """Analyze vulnerabilities across multiple blockchain protocols.

    Enhances the basic vuln_graph cross_chain_analysis with bridge-specific
    pattern matching, chain-specific vulnerability signatures, and composite
    risk scoring.
    """

    def __init__(self) -> None:
        self._bridge_patterns = BRIDGE_PATTERNS
        self._chain_signatures = CHAIN_SIGNATURES

    def analyze(
        self,
        chains: list[dict[str, Any]],
        bridge_connections: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run comprehensive cross-chain vulnerability analysis.

        Args:
            chains: List of chain data, each with chain_id and vulnerabilities.
            bridge_connections: Optional list of bridge connections between chains
                with source_chain, target_chain, bridge_type, tvl.
        """
        bridge_connections = bridge_connections or []
        chain_profiles = self._build_chain_profiles(chains)
        findings = self._detect_bridge_vulnerabilities(chains, bridge_connections)
        cross_chain_findings = self._correlate_cross_chain(chains)
        all_findings = findings + cross_chain_findings

        for f in all_findings:
            f.composite_risk_score = self._compute_composite_risk(f, chain_profiles, bridge_connections)

        all_findings.sort(key=lambda f: f.composite_risk_score, reverse=True)

        return {
            "chains_analyzed": len(chain_profiles),
            "chain_profiles": {k: v.__dict__ for k, v in chain_profiles.items()},
            "bridge_connections": len(bridge_connections),
            "total_findings": len(all_findings),
            "critical_findings": sum(1 for f in all_findings if f.severity == "critical"),
            "high_findings": sum(1 for f in all_findings if f.severity == "high"),
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "category": f.category,
                    "chains_affected": f.chains_affected,
                    "bridge_pattern": f.bridge_pattern,
                    "severity": f.severity,
                    "description": f.description,
                    "indicators": f.indicators,
                    "mitigation": f.mitigation,
                    "composite_risk_score": f.composite_risk_score,
                }
                for f in all_findings
            ],
            "overall_risk": self._overall_risk(all_findings, chain_profiles),
        }

    def _build_chain_profiles(self, chains: list[dict[str, Any]]) -> dict[str, ChainRiskProfile]:
        """Build risk profiles for each chain."""
        profiles: dict[str, ChainRiskProfile] = {}
        for chain in chains:
            chain_id = chain.get("chain_id", "unknown")
            vulns = chain.get("vulnerabilities", [])
            profile = ChainRiskProfile(chain_id=chain_id, total_vulnerabilities=len(vulns))

            for v in vulns:
                sev = v.get("severity", "medium")
                cat = v.get("category", "")
                if sev == "critical":
                    profile.critical_count += 1
                elif sev == "high":
                    profile.high_count += 1
                elif sev == "medium":
                    profile.medium_count += 1
                else:
                    profile.low_count += 1

                sigs = self._chain_signatures.get(chain_id, [])
                if cat in sigs:
                    profile.known_patterns.append(cat)

            profiles[chain_id] = profile
        return profiles

    def _detect_bridge_vulnerabilities(
        self,
        chains: list[dict[str, Any]],
        bridge_connections: list[dict[str, Any]],
    ) -> list[CrossChainFinding]:
        """Detect bridge-specific vulnerabilities from connections."""
        findings: list[CrossChainFinding] = []

        for i, bridge in enumerate(bridge_connections):
            source = bridge.get("source_chain", "")
            target = bridge.get("target_chain", "")
            bridge_type = bridge.get("bridge_type", "unknown")
            tvl = bridge.get("tvl", 0)

            for pattern_name, pattern_info in self._bridge_patterns.items():
                source_vulns = {v.get("category", "") for v in next((c for c in chains if c.get("chain_id") == source), {}).get("vulnerabilities", [])}
                target_vulns = {v.get("category", "") for v in next((c for c in chains if c.get("chain_id") == target), {}).get("vulnerabilities", [])}

                matched_indicators = []
                for indicator in pattern_info["indicators"]:
                    if any(indicator in v for v in source_vulns | target_vulns):
                        matched_indicators.append(indicator)

                if matched_indicators:
                    tvl_factor = min(1.0, tvl / 1_000_000) if tvl > 0 else 0.5
                    severity = pattern_info["severity"]
                    if tvl_factor > 0.5 and severity == "high":
                        severity = "critical"

                    findings.append(CrossChainFinding(
                        finding_id=f"bridge_{i}_{pattern_name}",
                        category=pattern_name,
                        chains_affected=[source, target],
                        bridge_pattern=bridge_type,
                        severity=severity,
                        description=pattern_info["description"],
                        indicators=matched_indicators,
                        mitigation=pattern_info["mitigation"],
                    ))

        return findings

    def _correlate_cross_chain(self, chains: list[dict[str, Any]]) -> list[CrossChainFinding]:
        """Find vulnerabilities that appear across multiple chains."""
        category_chains: dict[str, list[str]] = {}
        for chain in chains:
            chain_id = chain.get("chain_id", "unknown")
            for v in chain.get("vulnerabilities", []):
                cat = v.get("category", "")
                category_chains.setdefault(cat, []).append(chain_id)

        findings: list[CrossChainFinding] = []
        for cat, affected_chains in category_chains.items():
            if len(affected_chains) > 1:
                unique_chains = list(set(affected_chains))
                if len(unique_chains) > 1:
                    findings.append(CrossChainFinding(
                        finding_id=f"cross_chain_{cat}",
                        category=cat,
                        chains_affected=unique_chains,
                        bridge_pattern=None,
                        severity="high" if len(unique_chains) >= 3 else "medium",
                        description=f"Vulnerability category '{cat}' found across {len(unique_chains)} chains: {', '.join(unique_chains)}",
                        indicators=[cat],
                        mitigation="Coordinate patches across all affected chains, prioritize based on TVL exposure",
                    ))

        return findings

    def _compute_composite_risk(
        self,
        finding: CrossChainFinding,
        chain_profiles: dict[str, ChainRiskProfile],
        bridge_connections: list[dict[str, Any]],
    ) -> float:
        """Compute composite risk score (0.0-1.0)."""
        severity_weight = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}
        base = severity_weight.get(finding.severity, 0.3)

        chain_factor = 1.0
        for chain_id in finding.chains_affected:
            profile = chain_profiles.get(chain_id)
            if profile:
                chain_factor *= (1.0 + 0.1 * profile.critical_count)

        bridge_factor = 1.0
        for bridge in bridge_connections:
            if bridge.get("source_chain") in finding.chains_affected and bridge.get("target_chain") in finding.chains_affected:
                tvl = bridge.get("tvl", 0)
                bridge_factor *= (1.0 + min(0.5, tvl / 10_000_000))

        return round(min(1.0, base * chain_factor * bridge_factor), 3)

    def _overall_risk(
        self,
        findings: list[CrossChainFinding],
        chain_profiles: dict[str, ChainRiskProfile],
    ) -> str:
        """Determine overall cross-chain risk level."""
        if not findings:
            return "low"
        critical = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        max_composite = max((f.composite_risk_score for f in findings), default=0.0)

        if critical > 0 or max_composite >= 0.8:
            return "critical"
        if high >= 2 or max_composite >= 0.5:
            return "high"
        if high >= 1 or max_composite >= 0.3:
            return "medium"
        return "low"

    def list_bridge_patterns(self) -> dict[str, Any]:
        """List all known bridge vulnerability patterns."""
        return {
            name: {
                "description": info["description"],
                "severity": info["severity"],
                "indicators": info["indicators"],
                "mitigation": info["mitigation"],
            }
            for name, info in self._bridge_patterns.items()
        }

    def list_chain_signatures(self) -> dict[str, list[str]]:
        """List chain-specific vulnerability signatures."""
        return dict(self._chain_signatures)


_analyzer: CrossChainAnalyzer | None = None


def get_cross_chain_analyzer() -> CrossChainAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CrossChainAnalyzer()
    return _analyzer
