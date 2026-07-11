"""Audit report generator — professional reports for security assessments."""
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditReport:
    title: str
    project_name: str
    auditor: str
    date: str
    executive_summary: str
    findings: list[dict[str, Any]]
    methodology: str
    coverage: dict[str, Any]
    raw_markdown: str


class AuditReportGenerator:
    """Generate professional audit reports from findings."""

    def __init__(self) -> None:
        self._templates = {
            "standard": self._standard_template,
            "executive": self._executive_template,
            "technical": self._technical_template,
        }

    def generate(
        self,
        project_name: str,
        findings: list[dict[str, Any]],
        format_type: str = "standard",
        auditor: str = "WhiteMagic Security",
        coverage: dict[str, Any] | None = None,
    ) -> AuditReport:
        """Generate a complete audit report."""
        timestamp = time.strftime("%Y-%m-%d")
        cov = coverage or {}

        # Calculate stats
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = f.get("severity", "info").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1

        total = len(findings)
        critical = severity_counts["critical"]
        high = severity_counts["high"]

        # Executive summary
        if critical > 0:
            exec_summary = f"This audit identified {total} findings including {critical} critical and {high} high severity issues. Immediate remediation is required for critical findings before deployment."
        elif high > 0:
            exec_summary = f"This audit identified {total} findings including {high} high severity issues. Remediation is recommended before production deployment."
        elif total > 0:
            exec_summary = f"This audit identified {total} findings. No critical or high severity issues were found. Medium and low severity improvements are recommended."
        else:
            exec_summary = "This audit found no security issues. The contract appears to follow security best practices."

        # Generate using template
        template_fn = self._templates.get(format_type, self._standard_template)
        markdown = template_fn(
            project_name=project_name,
            findings=findings,
            severity_counts=severity_counts,
            exec_summary=exec_summary,
            auditor=auditor,
            date=timestamp,
            coverage=cov,
        )

        return AuditReport(
            title=f"Security Audit Report — {project_name}",
            project_name=project_name,
            auditor=auditor,
            date=timestamp,
            executive_summary=exec_summary,
            findings=findings,
            methodology="Automated static analysis via STRATA, manual review, pattern matching against vulnerability knowledge base.",
            coverage=cov,
            raw_markdown=markdown,
        )

    def _standard_template(self, **kwargs: Any) -> str:
        project_name = kwargs["project_name"]
        findings = kwargs["findings"]
        severity_counts = kwargs["severity_counts"]
        exec_summary = kwargs["exec_summary"]
        auditor = kwargs["auditor"]
        date = kwargs["date"]
        coverage = kwargs["coverage"]

        lines = [
            f"# Security Audit Report — {project_name}",
            "",
            f"**Auditor**: {auditor}",
            f"**Date**: {date}",
            f"**Coverage**: {coverage.get('files_scanned', 'N/A')} files, {coverage.get('loc', 'N/A')} lines of code",
            "",
            "## Executive Summary",
            "",
            exec_summary,
            "",
            "## Finding Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
            f"| Critical | {severity_counts['critical']} |",
            f"| High | {severity_counts['high']} |",
            f"| Medium | {severity_counts['medium']} |",
            f"| Low | {severity_counts['low']} |",
            f"| Info | {severity_counts['info']} |",
            "",
            "## Detailed Findings",
            "",
        ]

        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "info").upper()
            lines.append(f"### [{i}] {sev} — {f.get('title', f.get('message', 'Untitled'))}")
            lines.append("")
            lines.append(f"**File**: `{f.get('file', 'N/A')}`" + (f":{f.get('line', '')}" if f.get('line') else ""))
            lines.append(f"**Category**: {f.get('category', 'N/A')}")
            lines.append("")
            lines.append("**Description**")
            lines.append(f"{f.get('description', f.get('message', 'N/A'))}")
            lines.append("")
            if f.get("impact"):
                lines.append("**Impact**")
                lines.append(f"{f.get('impact')}")
                lines.append("")
            if f.get("proof_of_concept"):
                lines.append("**Proof of Concept**")
                lines.append("```solidity")
                lines.append(f"{f.get('proof_of_concept')}")
                lines.append("```")
                lines.append("")
            if f.get("mitigation") or f.get("suggestion"):
                lines.append("**Recommendation**")
                lines.append(f"{f.get('mitigation', f.get('suggestion', 'N/A'))}")
                lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Methodology")
        lines.append("")
        lines.append("This audit was conducted using a combination of:")
        lines.append("- Automated static analysis (STRATA framework)")
        lines.append("- Pattern matching against vulnerability knowledge base")
        lines.append("- Manual code review")
        lines.append("- Cross-domain vulnerability analysis")
        lines.append("")
        lines.append("## Disclaimer")
        lines.append("")
        lines.append("This report does not constitute a guarantee of security. Smart contracts carry inherent risks, and this audit should not be considered a substitute for thorough testing and review.")

        return "\n".join(lines)

    def _executive_template(self, **kwargs: Any) -> str:
        project_name = kwargs["project_name"]
        severity_counts = kwargs["severity_counts"]
        exec_summary = kwargs["exec_summary"]
        auditor = kwargs["auditor"]
        date = kwargs["date"]

        return (
            f"# Executive Security Summary — {project_name}\n\n"
            f"**Date**: {date} | **Auditor**: {auditor}\n\n"
            f"## Summary\n\n{exec_summary}\n\n"
            f"## Risk Matrix\n\n"
            f"- Critical: {severity_counts['critical']}\n"
            f"- High: {severity_counts['high']}\n"
            f"- Medium: {severity_counts['medium']}\n"
            f"- Low: {severity_counts['low']}\n"
            f"- Info: {severity_counts['info']}\n\n"
            f"**Recommendation**: "
            + ("Deploy with caution after fixing critical issues." if severity_counts['critical'] > 0
               else "Proceed with recommended improvements." if severity_counts['high'] > 0
               else "Safe to deploy with minor improvements.")
        )

    def _technical_template(self, **kwargs: Any) -> str:
        findings = kwargs["findings"]
        lines = ["# Technical Findings Report", ""]
        for f in findings:
            lines.append(f"## {f.get('category', 'unknown')}: {f.get('file', '')}:{f.get('line', '')}")
            lines.append(f"Severity: {f.get('severity', 'info')}")
            lines.append(f"Message: {f.get('message', f.get('description', ''))}")
            if f.get("suggestion"):
                lines.append(f"Fix: {f.get('suggestion')}")
            lines.append("")
        return "\n".join(lines)

    def status(self) -> dict[str, Any]:
        return {"templates": list(self._templates.keys())}


_generator: AuditReportGenerator | None = None


def get_audit_report_generator() -> AuditReportGenerator:
    global _generator
    if _generator is None:
        _generator = AuditReportGenerator()
    return _generator
