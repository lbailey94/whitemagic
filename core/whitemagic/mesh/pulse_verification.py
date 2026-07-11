# ruff: noqa: BLE001
"""Pulse Verification — Tiered trust protocol for mesh experiments (v24.3.0).

Inspired by Neunode's tiered verification protocol, this module provides
4-tier escalating verification for experiment results shared across the
P2P mesh:

    Tier 0: Automated — Ed25519 signature + Merkle proof
    Tier 1: RepOps — Reputation-weighted checks by high-karma nodes
    Tier 2: Peer Review — Human/AI peer review with 1-10 scoring
    Tier 3: ZK/TEE — Future: zero-knowledge or trusted execution proof

Each experiment starts at Tier 0 and can be escalated based on:
    - Fitness score claims (high claims need more verification)
    - Node reputation (new nodes need more verification)
    - Random sampling (deterministic but unpredictable)

Integration points:
    - ResearchDAG: verifies experiments before promoting to breakthrough
    - KarmaLedger: provides node reputation scores for Tier 1
    - ExperimentSync: verification attached to shared experiments
    - MeshClient: Ed25519 keys for signing
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class VerificationTier(IntEnum):
    """Verification tier levels (higher = stronger verification)."""

    AUTOMATED = 0
    REPOPS = 1
    PEER_REVIEW = 2
    ZK_TEE = 3


@dataclass
class VerificationResult:
    """Result of a verification check."""

    tier: VerificationTier
    passed: bool
    score: float = 0.0
    verifier: str = ""
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": int(self.tier),
            "tier_name": self.tier.name,
            "passed": self.passed,
            "score": round(self.score, 4),
            "verifier": self.verifier,
            "notes": self.notes,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class PulseRecord:
    """A signed pulse from a node attesting to an experiment."""

    experiment_id: str
    node_id: str
    signature: str
    merkle_root: str
    fitness_claim: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    verifications: list[VerificationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "node_id": self.node_id,
            "signature": self.signature[:16] + "..." if len(self.signature) > 16 else self.signature,
            "merkle_root": self.merkle_root[:16] + "..." if len(self.merkle_root) > 16 else self.merkle_root,
            "fitness_claim": self.fitness_claim,
            "timestamp": self.timestamp,
            "verifications": [v.to_dict() for v in self.verifications],
            "verified": all(v.passed for v in self.verifications) if self.verifications else False,
            "max_tier": max((v.tier for v in self.verifications), default=VerificationTier.AUTOMATED),
        }


class PulseVerifier:
    """Tiered pulse verification for mesh experiment results.

    Verifies experiment pulses through escalating tiers of trust.
    Tier 0 is always performed (automated cryptographic checks).
    Higher tiers are triggered based on escalation rules.
    """

    _instance: PulseVerifier | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._pulses: dict[str, PulseRecord] = {}
        self._pulses_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        self._tier0_checks = 0
        self._tier1_checks = 0
        self._tier2_checks = 0
        self._tier3_checks = 0
        self._total_passed = 0
        self._total_failed = 0
        self._escalations = 0

    @classmethod
    def get_instance(cls) -> PulseVerifier:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_pulse(
        self,
        experiment_id: str,
        node_id: str,
        fitness_claim: float,
        experiment_data: dict[str, Any] | None = None,
    ) -> PulseRecord:
        """Create a signed pulse for an experiment.

        Generates Ed25519 signature (if keys available) and Merkle root
        from the experiment data.
        """
        # Compute Merkle root from experiment data
        data_str = json.dumps(experiment_data or {}, sort_keys=True, default=str)
        merkle_root = hashlib.sha256(
            f"{experiment_id}:{data_str}".encode()
        ).hexdigest()

        # Generate signature (simulated Ed25519 — real keys would use nacl)
        signature = self._sign(f"{experiment_id}:{merkle_root}:{fitness_claim}")

        pulse = PulseRecord(
            experiment_id=experiment_id,
            node_id=node_id,
            signature=signature,
            merkle_root=merkle_root,
            fitness_claim=fitness_claim,
        )

        with self._pulses_lock:
            self._pulses[experiment_id] = pulse

        return pulse

    def verify(
        self,
        experiment_id: str,
        experiment_data: dict[str, Any] | None = None,
        node_reputation: float = 0.5,
        force_tier: VerificationTier | None = None,
    ) -> PulseRecord | None:
        """Verify an experiment pulse through tiered checks.

        Args:
            experiment_id: The experiment to verify.
            experiment_data: Data to verify against Merkle root.
            node_reputation: 0.0-1.0 reputation of the claiming node.
            force_tier: Force verification up to this tier.

        Returns:
            Updated PulseRecord with verification results, or None if no pulse exists.
        """
        with self._pulses_lock:
            pulse = self._pulses.get(experiment_id)
        if pulse is None:
            return None

        # Determine max tier to check
        max_tier = force_tier or self._determine_escalation(pulse, node_reputation)

        verifications: list[VerificationResult] = []

        # Tier 0: Automated (always)
        t0 = self._verify_tier0(pulse, experiment_data)
        verifications.append(t0)

        # Tier 1: RepOps (if escalated or forced)
        if max_tier >= VerificationTier.REPOPS:
            t1 = self._verify_tier1(pulse, node_reputation)
            verifications.append(t1)

        # Tier 2: Peer Review (if escalated or forced)
        if max_tier >= VerificationTier.PEER_REVIEW:
            t2 = self._verify_tier2(pulse)
            verifications.append(t2)

        # Tier 3: ZK/TEE (future — always fails gracefully)
        if max_tier >= VerificationTier.ZK_TEE:
            t3 = self._verify_tier3(pulse)
            verifications.append(t3)

        # Update pulse
        pulse.verifications = verifications

        # Update stats
        with self._stats_lock:
            self._tier0_checks += 1
            if max_tier >= VerificationTier.REPOPS:
                self._tier1_checks += 1
            if max_tier >= VerificationTier.PEER_REVIEW:
                self._tier2_checks += 1
            if max_tier >= VerificationTier.ZK_TEE:
                self._tier3_checks += 1
            if max_tier > VerificationTier.AUTOMATED:
                self._escalations += 1
            if all(v.passed for v in verifications):
                self._total_passed += 1
            else:
                self._total_failed += 1

        logger.info(
            "Pulse verified [%s]: tier=%s passed=%s checks=%d",
            experiment_id[:8], max_tier.name,
            all(v.passed for v in verifications),
            len(verifications),
        )

        return pulse

    def _determine_escalation(
        self,
        pulse: PulseRecord,
        node_reputation: float,
    ) -> VerificationTier:
        """Determine which verification tier to escalate to.

        Rules:
        - Fitness >= 0.8 (breakthrough claim) → at least Tier 1
        - Node reputation < 0.3 → at least Tier 1
        - Fitness >= 0.9 AND reputation < 0.5 → Tier 2
        - Random 5% sampling → Tier 1
        """
        # High fitness claims need more verification
        if pulse.fitness_claim >= 0.9 and node_reputation < 0.5:
            return VerificationTier.PEER_REVIEW

        if pulse.fitness_claim >= 0.8 or node_reputation < 0.3:
            return VerificationTier.REPOPS

        # Random sampling (5% of experiments get Tier 1)
        import random
        if random.random() < 0.05:
            return VerificationTier.REPOPS

        return VerificationTier.AUTOMATED

    def _verify_tier0(
        self,
        pulse: PulseRecord,
        experiment_data: dict[str, Any] | None,
    ) -> VerificationResult:
        """Tier 0: Automated verification — Ed25519 signature + Merkle proof."""
        try:
            # Verify Merkle root
            data_str = json.dumps(experiment_data or {}, sort_keys=True, default=str)
            expected_root = hashlib.sha256(
                f"{pulse.experiment_id}:{data_str}".encode()
            ).hexdigest()

            merkle_valid = expected_root == pulse.merkle_root

            # Verify signature (simulated)
            expected_sig = self._sign(
                f"{pulse.experiment_id}:{pulse.merkle_root}:{pulse.fitness_claim}"
            )
            sig_valid = pulse.signature == expected_sig

            passed = merkle_valid and sig_valid
            score = (0.5 if merkle_valid else 0.0) + (0.5 if sig_valid else 0.0)

            return VerificationResult(
                tier=VerificationTier.AUTOMATED,
                passed=passed,
                score=score,
                verifier="auto_cryptographic",
                notes=f"merkle_valid={merkle_valid} sig_valid={sig_valid}",
                metadata={
                    "merkle_root": pulse.merkle_root[:16],
                    "node_id": pulse.node_id,
                },
            )
        except Exception as e:
            return VerificationResult(
                tier=VerificationTier.AUTOMATED,
                passed=False,
                score=0.0,
                verifier="auto_cryptographic",
                notes=f"Error: {e}",
            )

    def _verify_tier1(
        self,
        pulse: PulseRecord,
        node_reputation: float,
    ) -> VerificationResult:
        """Tier 1: RepOps — reputation-weighted verification.

        High-karma nodes vouch for the experiment. The verification
        score is weighted by the node's reputation.
        """
        try:
            # Get karma score for the node
            karma_score = self._get_node_karma(pulse.node_id)

            # Combined reputation score
            combined_rep = (node_reputation + karma_score) / 2.0

            # Pass if combined reputation >= 0.4
            passed = combined_rep >= 0.4
            score = combined_rep

            return VerificationResult(
                tier=VerificationTier.REPOPS,
                passed=passed,
                score=score,
                verifier="repops",
                notes=f"node_reputation={node_reputation:.3f} karma={karma_score:.3f} combined={combined_rep:.3f}",
                metadata={
                    "node_reputation": node_reputation,
                    "karma_score": karma_score,
                },
            )
        except Exception as e:
            return VerificationResult(
                tier=VerificationTier.REPOPS,
                passed=False,
                score=0.0,
                verifier="repops",
                notes=f"Error: {e}",
            )

    def _verify_tier2(self, pulse: PulseRecord) -> VerificationResult:
        """Tier 2: Peer Review — structured peer review with 1-10 scoring.

        In a full mesh, this would route to peer nodes for review.
        Locally, we simulate with a heuristic based on experiment metadata.
        """
        try:
            # Simulated peer review — in production, this would query peer nodes
            # For now, we check if the fitness claim is reasonable
            # (not impossibly high for the domain)
            reasonable = 0.0 <= pulse.fitness_claim <= 1.0
            score = 0.7 if reasonable else 0.3
            passed = reasonable

            return VerificationResult(
                tier=VerificationTier.PEER_REVIEW,
                passed=passed,
                score=score,
                verifier="peer_review_simulated",
                notes=f"fitness_claim_reasonable={reasonable}",
                metadata={
                    "review_type": "simulated",
                    "fitness_claim": pulse.fitness_claim,
                },
            )
        except Exception as e:
            return VerificationResult(
                tier=VerificationTier.PEER_REVIEW,
                passed=False,
                score=0.0,
                verifier="peer_review_simulated",
                notes=f"Error: {e}",
            )

    def _verify_tier3(self, pulse: PulseRecord) -> VerificationResult:
        """Tier 3: ZK/TEE — future zero-knowledge or trusted execution proof.

        Not yet implemented. Always returns a graceful failure.
        """
        return VerificationResult(
            tier=VerificationTier.ZK_TEE,
            passed=False,
            score=0.0,
            verifier="zk_tee",
            notes="ZK/TEE verification not yet implemented",
            metadata={"implemented": False},
        )

    def _sign(self, message: str) -> str:
        """Sign a message with Ed25519 (simulated).

        In production, this would use PyNaCl or similar for real Ed25519.
        For now, we use a deterministic hash-based signature.
        """
        # Try to use a persistent key from state root
        state_root = os.environ.get("WM_STATE_ROOT", os.path.expanduser("~/.whitemagic"))
        key_path = os.path.join(state_root, "ed25519_key.txt")

        key_material = ""
        try:
            if os.path.exists(key_path):
                with open(key_path) as f:
                    key_material = f.read().strip()
            else:
                # Generate a deterministic key from hostname + PID
                import socket
                key_material = f"{socket.gethostname()}:whitemagic:pulse"
                os.makedirs(os.path.dirname(key_path), exist_ok=True)
                with open(key_path, "w") as f:
                    f.write(key_material)
        except Exception:
            key_material = "fallback_key"

        return hashlib.sha256(f"{key_material}:{message}".encode()).hexdigest()

    def _get_node_karma(self, node_id: str) -> float:
        """Get karma score for a node from the KarmaLedger."""
        try:
            from whitemagic.dharma.karma_ledger import get_karma_ledger

            ledger = get_karma_ledger()
            report = ledger.get_debt_report()
            # Use total debt as inverse reputation
            total_debt = report.get("total_debt", 0.0)
            return max(0.0, 1.0 - total_debt)
        except Exception:
            return 0.5

    def get_status(self) -> dict[str, Any]:
        """Get verification system status."""
        with self._stats_lock:
            stats = {
                "tier0_checks": self._tier0_checks,
                "tier1_checks": self._tier1_checks,
                "tier2_checks": self._tier2_checks,
                "tier3_checks": self._tier3_checks,
                "total_passed": self._total_passed,
                "total_failed": self._total_failed,
                "escalations": self._escalations,
            }

        with self._pulses_lock:
            pulses_tracked = len(self._pulses)

        return {
            "pulses_tracked": pulses_tracked,
            **stats,
            "pass_rate": (
                self._total_passed / max(self._tier0_checks, 1)
                if self._tier0_checks > 0 else 0.0
            ),
        }

    def get_pulse(self, experiment_id: str) -> PulseRecord | None:
        """Get a pulse record by experiment ID."""
        with self._pulses_lock:
            return self._pulses.get(experiment_id)


def get_pulse_verifier() -> PulseVerifier:
    """Get the singleton PulseVerifier instance."""
    return PulseVerifier.get_instance()
