"""Contest pipeline — format findings for Code4rena, Sherlock, CodeHawks submissions."""
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContestFinding:
    """A finding formatted for contest submission."""
    title: str
    severity: str  # "High", "Medium", "Low", "QA", "Gas"
    category: str
    file: str
    line: int | None
    description: str
    impact: str
    proof_of_concept: str
    mitigation: str
    finding_id: str = ""
    dedup_hash: str = ""
    fix_status: str = "none"  # none, pending, applied, pr_created, merged
    mitre_ttp_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.finding_id:
            self.finding_id = f"WM-{abs(hash(self.title + self.file)) % 10000:04d}"
        if not self.dedup_hash:
            content = f"{self.file}:{self.line}:{self.category}:{self.title}"
            self.dedup_hash = hashlib.sha256(content.encode()).hexdigest()[:16]


class ContestPipeline:
    """Format and deduplicate findings for competitive audit submissions."""

    PLATFORMS = {
        "code4rena": {
            "severity_map": {"critical": "High", "high": "High", "medium": "Medium", "low": "Low", "info": "QA"},
            "format": "markdown",
            "max_findings": 100,
        },
        "sherlock": {
            "severity_map": {"critical": "High", "high": "High", "medium": "Medium", "low": "Low", "info": "Issue"},
            "format": "markdown",
            "max_findings": 50,
        },
        "codehawks": {
            "severity_map": {"critical": "High", "high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
            "format": "markdown",
            "max_findings": 100,
        },
        "cantina": {
            "severity_map": {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
            "format": "markdown",
            "max_findings": 100,
        },
        "hackerone": {
            "severity_map": {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Informational"},
            "format": "markdown",
            "max_findings": 100,
        },
        "bugcrowd": {
            "severity_map": {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4", "info": "P5"},
            "format": "markdown",
            "max_findings": 100,
        },
        "mitre": {
            "severity_map": {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Informational"},
            "format": "navigator",
            "max_findings": 1000,
        },
        "huntr": {
            "severity_map": {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
            "format": "markdown",
            "max_findings": 100,
        },
    }

    def __init__(self) -> None:
        self._findings: list[ContestFinding] = []
        self._seen_hashes: set[str] = set()

    def add_finding(
        self,
        title: str,
        severity: str,
        category: str,
        file: str,
        line: int | None,
        description: str,
        impact: str,
        proof_of_concept: str,
        mitigation: str,
        mitre_ttp_ids: list[str] | None = None,
    ) -> ContestFinding | None:
        finding = ContestFinding(
            title=title,
            severity=severity,
            category=category,
            file=file,
            line=line,
            description=description,
            impact=impact,
            proof_of_concept=proof_of_concept,
            mitigation=mitigation,
            mitre_ttp_ids=mitre_ttp_ids or [],
        )
        if finding.dedup_hash in self._seen_hashes:
            logger.debug("Dedup: skipping %s (hash=%s)", finding.title, finding.dedup_hash)
            return None
        self._seen_hashes.add(finding.dedup_hash)
        self._findings.append(finding)
        return finding

    def add_from_strata(self, strata_findings: list[dict[str, Any]]) -> int:
        """Convert STRATA findings to ContestFindings."""
        count = 0
        for f in strata_findings:
            sev = "low"
            if f.get("severity") == "error":
                sev = "high"
            elif f.get("severity") == "warning":
                sev = "medium"
            from whitemagic.tools.security.strata_mitre_map import (
                get_ttp_ids_for_category,
            )
            ttp_ids = get_ttp_ids_for_category(f.get("category", ""))
            result = self.add_finding(
                title=f.get("message", "Untitled finding")[:100],
                severity=sev,
                category=f.get("category", "unknown"),
                file=f.get("file", ""),
                line=f.get("line"),
                description=f.get("message", ""),
                impact=f.get("suggestion", ""),
                proof_of_concept="",
                mitigation=f.get("suggestion", ""),
                mitre_ttp_ids=ttp_ids,
            )
            if result:
                count += 1
        return count

    def format_for_platform(self, platform: str) -> str:
        """Format all findings as a report for a specific platform."""
        if platform not in self.PLATFORMS:
            return f"Unknown platform: {platform}"

        config = self.PLATFORMS[platform]

        if config["format"] == "navigator":
            return self._format_navigator()

        return self._format_markdown(platform, config)

    def _format_markdown(self, platform: str, config: dict[str, Any]) -> str:
        """Format findings as markdown for a specific platform."""
        lines = [f"# {platform.title()} Submission — WhiteMagic Security Analysis", ""]

        severity_order = ["Critical", "High", "Medium", "Low", "QA", "Issue", "Info", "Gas", "Informational", "P1", "P2", "P3", "P4", "P5"]
        by_severity: dict[str, list[ContestFinding]] = {}
        for f in self._findings:
            mapped_sev = config["severity_map"].get(f.severity.lower(), f.severity)
            by_severity.setdefault(mapped_sev, []).append(f)

        for sev in severity_order:
            findings = by_severity.get(sev, [])
            if not findings:
                continue
            lines.append(f"## {sev} Findings ({len(findings)})")
            lines.append("")
            for f in findings:
                lines.append(f"### {f.title}")
                lines.append("")
                lines.append(f"**File**: `{f.file}`" + (f":{f.line}" if f.line else ""))
                lines.append(f"**Severity**: {sev}")
                lines.append(f"**Category**: {f.category}")
                lines.append(f"**ID**: {f.finding_id}")
                if f.mitre_ttp_ids:
                    lines.append(f"**MITRE ATT&CK**: {', '.join(f.mitre_ttp_ids)}")
                lines.append("")
                lines.append("**Description**")
                lines.append(f"{f.description}")
                lines.append("")
                lines.append("**Impact**")
                lines.append(f"{f.impact}")
                lines.append("")
                if f.proof_of_concept:
                    lines.append("**Proof of Concept**")
                    lines.append("```solidity")
                    lines.append(f"{f.proof_of_concept}")
                    lines.append("```")
                    lines.append("")
                lines.append("**Recommended Mitigation**")
                lines.append(f"{f.mitigation}")
                lines.append("")
                lines.append("---")
                lines.append("")

        lines.append(f"\n*Generated by WhiteMagic Security Pipeline — {len(self._findings)} findings, {platform} format*")
        return "\n".join(lines)

    def _format_navigator(self) -> str:
        """Format findings as a MITRE ATT&CK Navigator layer JSON."""
        from whitemagic.tools.security.strata_mitre_map import generate_navigator_layer

        findings_dicts = [
            {
                "category": f.category,
                "severity": f.severity,
                "file": f.file,
                "message": f.title,
                "mitre_ttp_ids": f.mitre_ttp_ids,
            }
            for f in self._findings
        ]
        layer = generate_navigator_layer(findings_dicts)
        return json.dumps(layer, indent=2)

    def dedup_check(self, new_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only findings that aren't duplicates of already submitted ones."""
        unique = []
        for f in new_findings:
            content = f"{f.get('file', '')}:{f.get('line', '')}:{f.get('category', '')}:{f.get('message', '')[:50]}"
            h = hashlib.sha256(content.encode()).hexdigest()[:16]
            if h not in self._seen_hashes:
                unique.append(f)
        return unique

    def link_fix(self, finding_id: str, fix: Any) -> bool:
        """Link a FixSuggestion to a contest finding, updating fix_status."""
        for f in self._findings:
            if f.finding_id == finding_id:
                f.fix_status = "applied"
                logger.info("Linked fix to finding %s", finding_id)
                return True
        logger.debug("Finding %s not found for fix linking", finding_id)
        return False

    def link_pr(self, finding_id: str, pr_url: str) -> bool:
        """Link a PR URL to a contest finding, updating fix_status to pr_created."""
        for f in self._findings:
            if f.finding_id == finding_id:
                f.fix_status = "pr_created"
                logger.info("Linked PR %s to finding %s", pr_url, finding_id)
                return True
        logger.debug("Finding %s not found for PR linking", finding_id)
        return False

    def fix_coverage_report(self) -> dict[str, Any]:
        """Report which findings have fixes and which don't."""
        by_status: dict[str, int] = {}
        unfixed: list[dict[str, str]] = []
        for f in self._findings:
            by_status[f.fix_status] = by_status.get(f.fix_status, 0) + 1
            if f.fix_status == "none":
                unfixed.append({"finding_id": f.finding_id, "title": f.title, "file": f.file, "severity": f.severity})
        total = len(self._findings)
        fixed = total - by_status.get("none", 0)
        return {
            "total_findings": total,
            "fixed_or_in_progress": fixed,
            "unfixed": len(unfixed),
            "by_fix_status": by_status,
            "unfixed_findings": unfixed,
            "coverage_pct": round(fixed / total * 100, 1) if total else 0.0,
        }

    def status(self) -> dict[str, Any]:
        return {
            "total_findings": len(self._findings),
            "unique_hashes": len(self._seen_hashes),
            "by_severity": {
                sev: sum(1 for f in self._findings if f.severity == sev)
                for sev in set(f.severity for f in self._findings)
            },
            "fix_coverage": self.fix_coverage_report(),
            "platforms": list(self.PLATFORMS.keys()),
        }

    @property
    def findings(self) -> list[ContestFinding]:
        return list(self._findings)


_pipeline: ContestPipeline | None = None


def get_contest_pipeline() -> ContestPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ContestPipeline()
    return _pipeline
