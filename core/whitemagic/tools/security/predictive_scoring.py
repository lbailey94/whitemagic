"""Predictive vulnerability scoring — estimate likelihood and severity of vulnerabilities."""
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VulnerabilityPrediction:
    contract_file: str
    contract_name: str
    predicted_vulnerabilities: list[dict[str, Any]]
    risk_score: float
    confidence: float
    factors: dict[str, float]


class PredictiveScorer:
    """Score contracts for vulnerability likelihood using historical patterns."""

    # Risk factors and their weights
    RISK_FACTORS = {
        "complexity": 0.15,
        "external_calls": 0.20,
        "state_modification": 0.10,
        "access_control_missing": 0.25,
        "arithmetic_operations": 0.10,
        "assembly_usage": 0.10,
        "delegatecall_usage": 0.15,
        "selfdestruct_usage": 0.20,
        "tx_origin_usage": 0.15,
        "unchecked_external": 0.10,
    }

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def score_contract(
        self,
        contract_file: str,
        contract_name: str,
        content: str,
        findings: list[dict[str, Any]] | None = None,
    ) -> VulnerabilityPrediction:
        """Score a contract for vulnerability risk."""
        factors: dict[str, float] = {}

        # Complexity: lines of code
        lines = content.splitlines()
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])
        factors["complexity"] = min(1.0, loc / 500.0)

        # External calls
        ext_calls = content.count(".call(") + content.count(".transfer(") + content.count(".send(")
        factors["external_calls"] = min(1.0, ext_calls / 10.0)

        # State modification
        state_mods = content.count("balances[") + content.count("mapping(") + content.count("=")
        factors["state_modification"] = min(1.0, state_mods / 20.0)

        # Access control missing
        has_access = "onlyOwner" in content or "onlyRole" in content or "require(msg.sender" in content
        factors["access_control_missing"] = 0.0 if has_access else 0.8

        # Arithmetic
        arith_ops = content.count("+") + content.count("-") + content.count("*") + content.count("/")
        factors["arithmetic_operations"] = min(1.0, arith_ops / 30.0)

        # Assembly
        factors["assembly_usage"] = 1.0 if "assembly" in content else 0.0

        # Delegatecall
        factors["delegatecall_usage"] = 1.0 if "delegatecall" in content else 0.0

        # Selfdestruct
        factors["selfdestruct_usage"] = 1.0 if "selfdestruct" in content else 0.0

        # tx.origin
        factors["tx_origin_usage"] = 1.0 if "tx.origin" in content else 0.0

        # Unchecked external
        unchecked = content.count(".call(") - content.count("require(") - content.count("assert(")
        factors["unchecked_external"] = min(1.0, max(0.0, unchecked / 5.0))

        # Calculate weighted risk score
        risk_score = sum(
            factors.get(factor, 0) * weight
            for factor, weight in self.RISK_FACTORS.items()
        )
        risk_score = min(1.0, risk_score)

        # Predict likely vulnerabilities
        predicted = self._predict_vulnerabilities(factors, findings or [])

        # Confidence based on factors evaluated
        confidence = min(1.0, len(factors) / len(self.RISK_FACTORS))

        prediction = VulnerabilityPrediction(
            contract_file=contract_file,
            contract_name=contract_name,
            predicted_vulnerabilities=predicted,
            risk_score=risk_score,
            confidence=confidence,
            factors=factors,
        )

        self._history.append({
            "contract": contract_name,
            "risk_score": risk_score,
            "timestamp": time.time(),
        })

        return prediction

    def _predict_vulnerabilities(
        self,
        factors: dict[str, float],
        existing_findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Predict likely vulnerabilities based on risk factors."""
        predictions = []

        if factors.get("delegatecall_usage", 0) > 0.5:
            predictions.append({
                "vulnerability": "delegatecall_to_user",
                "likelihood": 0.9,
                "severity": "critical",
                "reason": "delegatecall detected — high risk of arbitrary code execution",
            })

        if factors.get("selfdestruct_usage", 0) > 0.5:
            predictions.append({
                "vulnerability": "unprotected_selfdestruct",
                "likelihood": 0.8,
                "severity": "critical",
                "reason": "selfdestruct detected — verify access control",
            })

        if factors.get("tx_origin_usage", 0) > 0.5:
            predictions.append({
                "vulnerability": "tx_origin_auth",
                "likelihood": 0.9,
                "severity": "medium",
                "reason": "tx.origin used for authorization — phishing vector",
            })

        if factors.get("access_control_missing", 0) > 0.5:
            predictions.append({
                "vulnerability": "missing_access_control",
                "likelihood": 0.7,
                "severity": "high",
                "reason": "No access control modifiers detected",
            })

        if factors.get("external_calls", 0) > 0.3 and factors.get("state_modification", 0) > 0.3:
            predictions.append({
                "vulnerability": "reentrancy",
                "likelihood": 0.6,
                "severity": "high",
                "reason": "External calls with state modification — CEI violation risk",
            })

        if factors.get("unchecked_external", 0) > 0.3:
            predictions.append({
                "vulnerability": "unchecked_call",
                "likelihood": 0.7,
                "severity": "medium",
                "reason": "External calls without return value checks",
            })

        if factors.get("arithmetic_operations", 0) > 0.5 and "0.8" not in str(factors):
            predictions.append({
                "vulnerability": "integer_overflow",
                "likelihood": 0.5,
                "severity": "high",
                "reason": "Heavy arithmetic — verify SafeMath or >=0.8.0 pragma",
            })

        if factors.get("assembly_usage", 0) > 0.5:
            predictions.append({
                "vulnerability": "assembly_risk",
                "likelihood": 0.6,
                "severity": "medium",
                "reason": "Inline assembly — manual review required",
            })

        return predictions

    def batch_score(
        self,
        contracts: list[dict[str, str]],
    ) -> list[VulnerabilityPrediction]:
        """Score multiple contracts."""
        results = []
        for c in contracts:
            result = self.score_contract(
                c.get("file", ""),
                c.get("name", ""),
                c.get("content", ""),
            )
            results.append(result)
        # Sort by risk score descending
        results.sort(key=lambda x: -x.risk_score)
        return results

    def status(self) -> dict[str, Any]:
        return {
            "history_count": len(self._history),
            "avg_risk": sum(h["risk_score"] for h in self._history) / max(1, len(self._history)),
        }


_scorer: PredictiveScorer | None = None


def get_predictive_scorer() -> PredictiveScorer:
    global _scorer
    if _scorer is None:
        _scorer = PredictiveScorer()
    return _scorer
