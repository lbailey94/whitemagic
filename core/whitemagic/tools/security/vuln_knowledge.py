"""Vulnerability knowledge module — store, search, and recall vulnerability patterns.

Integrates with WhiteMagic's memory system to persist vulnerability findings
across engagements. The key differentiator: every finding, false positive, and
pattern is remembered for future audits.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VulnerabilityPattern:
    """A known vulnerability pattern extracted from audits, findings, or research."""
    pattern_id: str
    name: str
    category: str  # e.g., "reentrancy", "access_control", "oracle"
    severity: str  # "critical", "high", "medium", "low", "info"
    description: str
    detection_regex: str | None = None
    detection_keywords: list[str] = field(default_factory=list)
    false_positive_indicators: list[str] = field(default_factory=list)
    mitigation: str = ""
    cwe_id: str | None = None
    swc_id: str | None = None
    examples: list[str] = field(default_factory=list)
    source: str = ""  # "audit_report", "manual", "slither", "research"
    confidence: float = 1.0
    last_seen: float = 0.0
    times_seen: int = 0


# Built-in patterns from known vulnerability classes
_BUILTIN_PATTERNS: list[VulnerabilityPattern] = [
    VulnerabilityPattern(
        pattern_id="WM-REENTRANCY-001",
        name="Reentrancy in withdrawal function",
        category="reentrancy",
        severity="high",
        description="External call before state update allows reentrant calls to drain funds.",
        detection_keywords=["call", "transfer", "send", "withdraw", "balances"],
        false_positive_indicators=["nonReentrant", "ReentrancyGuard", "checks-effects-interactions"],
        mitigation="Use ReentrancyGuard or follow CEI pattern.",
        swc_id="SWC-107",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-ACCESS-001",
        name="Missing access control on privileged function",
        category="access_control",
        severity="high",
        description="Function performs privileged operation without authorization check.",
        detection_keywords=["mint", "burn", "setAdmin", "withdraw", "sweep", "onlyOwner"],
        false_positive_indicators=["onlyOwner", "onlyRole", "require(msg.sender == owner"],
        mitigation="Add access control modifier (onlyOwner, onlyRole).",
        swc_id="SWC-105",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-ORACLE-001",
        name="Spot price oracle manipulation",
        category="oracle",
        severity="high",
        description="Using spot reserves/slot0 for pricing — vulnerable to flash loan attacks.",
        detection_keywords=["getReserves", "slot0", "price0Cumulative"],
        false_positive_indicators=["TWAP", "timeWeighted", "OracleLibrary", "Chainlink"],
        mitigation="Use TWAP oracle or Chainlink price feeds.",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-TXORIGIN-001",
        name="tx.origin authorization",
        category="access_control",
        severity="medium",
        description="Using tx.origin for authorization — phishing attack vector.",
        detection_keywords=["tx.origin"],
        false_positive_indicators=["msg.sender"],
        mitigation="Use msg.sender instead of tx.origin.",
        swc_id="SWC-115",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-INTEGER-001",
        name="Integer overflow/underflow (pre-0.8.0)",
        category="arithmetic",
        severity="high",
        description="Arithmetic without overflow checks (Solidity <0.8.0).",
        detection_keywords=["SafeMath", "add", "sub", "mul"],
        false_positive_indicators=["unchecked", "SafeMath", ">=0.8.0"],
        mitigation="Upgrade to Solidity >=0.8.0 or use SafeMath.",
        swc_id="SWC-101",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-SELFDESTRUCT-001",
        name="Unprotected selfdestruct",
        category="access_control",
        severity="critical",
        description="selfdestruct without access control can destroy contract.",
        detection_keywords=["selfdestruct", "suicide"],
        false_positive_indicators=["onlyOwner", "onlyRole"],
        mitigation="Protect with access control modifier.",
        swc_id="SWC-106",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-DELEGATECALL-001",
        name="Delegatecall to user-controlled address",
        category="delegatecall",
        severity="critical",
        description="delegatecall to user-supplied address enables arbitrary code execution.",
        detection_keywords=["delegatecall", "msg.sender", "msg.data"],
        false_positive_indicators=["library", "staticcall"],
        mitigation="Never delegatecall to user-supplied addresses.",
        swc_id="SWC-112",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-SQLI-001",
        name="SQL injection via string formatting",
        category="injection",
        severity="critical",
        description="SQL query built with f-string or concatenation — injection risk.",
        detection_keywords=["execute", "cursor", "f'", "SELECT", "INSERT"],
        false_positive_indicators=["%s", "parameterized", "?"],
        mitigation="Use parameterized queries.",
        cwe_id="CWE-89",
        source="builtin",
    ),
    VulnerabilityPattern(
        pattern_id="WM-XSS-001",
        name="XSS via innerHTML",
        category="xss",
        severity="high",
        description="User input assigned to innerHTML without sanitization.",
        detection_keywords=["innerHTML", "dangerouslySetInnerHTML", "|safe"],
        false_positive_indicators=["textContent", "DOMPurify", "sanitize"],
        mitigation="Use textContent or sanitize with DOMPurify.",
        cwe_id="CWE-79",
        source="builtin",
    ),
]


class VulnKnowledgeBase:
    """In-memory vulnerability knowledge base with pattern matching."""

    def __init__(self) -> None:
        self._patterns: dict[str, VulnerabilityPattern] = {}
        for p in _BUILTIN_PATTERNS:
            self._patterns[p.pattern_id] = p

    def add_pattern(self, pattern: VulnerabilityPattern) -> None:
        self._patterns[pattern.pattern_id] = pattern

    def get_pattern(self, pattern_id: str) -> VulnerabilityPattern | None:
        return self._patterns.get(pattern_id)

    def search_by_category(self, category: str) -> list[VulnerabilityPattern]:
        return [p for p in self._patterns.values() if p.category == category]

    def search_by_keyword(self, keyword: str) -> list[VulnerabilityPattern]:
        keyword_lower = keyword.lower()
        results = []
        for p in self._patterns.values():
            if keyword_lower in p.name.lower() or keyword_lower in p.description.lower():
                results.append(p)
            elif any(keyword_lower in kw.lower() for kw in p.detection_keywords):
                results.append(p)
        return results

    def match_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Match STRATA findings against known vulnerability patterns."""
        matched = []
        for finding in findings:
            finding.get("category", "")
            message = finding.get("message", "")
            for pattern in self._patterns.values():
                if pattern.detection_regex and re.search(pattern.detection_regex, message):
                    matched.append({
                        "finding": finding,
                        "pattern": pattern.pattern_id,
                        "pattern_name": pattern.name,
                        "severity": pattern.severity,
                        "mitigation": pattern.mitigation,
                        "confidence": pattern.confidence,
                    })
                    break
                if any(kw.lower() in message.lower() for kw in pattern.detection_keywords):
                    has_fp = any(
                        fp.lower() in message.lower()
                        for fp in pattern.false_positive_indicators
                    )
                    if not has_fp:
                        matched.append({
                            "finding": finding,
                            "pattern": pattern.pattern_id,
                            "pattern_name": pattern.name,
                            "severity": pattern.severity,
                            "mitigation": pattern.mitigation,
                            "confidence": pattern.confidence * 0.8,
                        })
                        break
        return matched

    def ingest_audit_report(self, report_text: str, source: str = "audit_report") -> int:
        """Extract vulnerability patterns from an audit report.

        Returns the number of patterns extracted.
        """
        count = 0
        sections = re.split(r"\n#{1,3}\s+", report_text)
        for section in sections:
            severity_match = re.search(
                r"\b(critical|high|medium|low|info)\b", section, re.IGNORECASE
            )
            if not severity_match:
                continue
            name_match = re.search(r"^(.+?)(?:\n|$)", section)
            if not name_match:
                continue
            name = name_match.group(1).strip()[:100]
            pattern_id = f"WM-AUDIT-{count + 1:04d}"
            pattern = VulnerabilityPattern(
                pattern_id=pattern_id,
                name=name,
                category="unknown",
                severity=severity_match.group(1).lower(),
                description=section[:500],
                source=source,
                confidence=0.7,
                last_seen=time.time(),
            )
            self._patterns[pattern_id] = pattern
            count += 1
        return count

    def all_patterns(self) -> list[dict[str, Any]]:
        return [
            {
                "pattern_id": p.pattern_id,
                "name": p.name,
                "category": p.category,
                "severity": p.severity,
                "description": p.description,
                "mitigation": p.mitigation,
                "source": p.source,
                "confidence": p.confidence,
                "times_seen": p.times_seen,
            }
            for p in self._patterns.values()
        ]

    def status(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "builtin": sum(1 for p in self._patterns.values() if p.source == "builtin"),
            "from_audits": sum(1 for p in self._patterns.values() if p.source == "audit_report"),
            "categories": list(set(p.category for p in self._patterns.values())),
        }


_vuln_kb: VulnKnowledgeBase | None = None


def get_vuln_knowledge_base() -> VulnKnowledgeBase:
    global _vuln_kb
    if _vuln_kb is None:
        _vuln_kb = VulnKnowledgeBase()
    return _vuln_kb
