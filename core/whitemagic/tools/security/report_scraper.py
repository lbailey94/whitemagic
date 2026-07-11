"""Public audit report scraper — Code4rena, Sherlock, CodeHawks."""
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScrapedReport:
    platform: str
    contest_name: str
    url: str
    findings: list[dict[str, Any]]
    raw_text: str
    scraped_at: float


class ReportScraper:
    """Scrape public audit reports from competitive audit platforms."""

    PLATFORMS = {
        "code4rena": {
            "base_url": "https://code4rena.com/reports",
            "finding_pattern": r"##\s*\[?([HML])\]?\s*[-:]?\s*(.+?)(?:\n|$)",
            "severity_map": {"H": "high", "M": "medium", "L": "low"},
        },
        "sherlock": {
            "base_url": "https://sherlock.xyz/audits",
            "finding_pattern": r"##\s*\[?([HML])\]?\s*[-:]?\s*(.+?)(?:\n|$)",
            "severity_map": {"H": "high", "M": "medium", "L": "low"},
        },
        "codehawks": {
            "base_url": "https://www.codehawks.com",
            "finding_pattern": r"##\s*\[?([HML])\]?\s*[-:]?\s*(.+?)(?:\n|$)",
            "severity_map": {"H": "high", "M": "medium", "L": "low"},
        },
    }

    def scrape_url(self, url: str, platform: str = "code4rena") -> ScrapedReport | None:
        """Scrape a single report URL."""
        try:
            import requests
            response = requests.get(url, timeout=30, headers={"User-Agent": "WhiteMagic-Security/1.0"})
            if response.status_code != 200:
                logger.warning("Failed to fetch %s: %d", url, response.status_code)
                return None

            text = response.text
            findings = self._parse_findings(text, platform)
            contest_name = self._extract_contest_name(url, text)

            return ScrapedReport(
                platform=platform,
                contest_name=contest_name,
                url=url,
                findings=findings,
                raw_text=text[:5000],
                scraped_at=time.time(),
            )
        except Exception as e:
            logger.warning("Scrape failed for %s: %s", url, e)
            return None

    def _parse_findings(self, text: str, platform: str) -> list[dict[str, Any]]:
        """Parse findings from report text."""
        config = self.PLATFORMS.get(platform, self.PLATFORMS["code4rena"])
        severity_map = config["severity_map"]
        findings = []

        sections = re.split(r"\n#{1,3}\s+", text)
        for section in sections:
            match = re.match(config["finding_pattern"], section)
            if match:
                sev_char = match.group(1).upper()
                title = match.group(2).strip()[:200]
                severity = severity_map.get(sev_char, "info")

                # Extract description (first paragraph after title)
                desc_match = re.search(r"\n(.+?)(?:\n#{1,3}|\Z)", section, re.DOTALL)
                description = desc_match.group(1).strip()[:500] if desc_match else ""

                findings.append({
                    "title": title,
                    "severity": severity,
                    "description": description,
                    "platform": platform,
                })

        return findings

    def _extract_contest_name(self, url: str, text: str) -> str:
        """Extract contest name from URL or page text."""
        name_match = re.search(r"/([^/]+)/?$", url)
        if name_match:
            return name_match.group(1).replace("-", " ").title()
        title_match = re.search(r"<title>(.+?)</title>", text, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        return "Unknown Contest"

    def scrape_to_knowledge_base(self, url: str, platform: str = "code4rena") -> int:
        """Scrape a report and ingest findings into the vuln knowledge base."""
        from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base

        report = self.scrape_url(url, platform)
        if not report:
            return 0

        kb = get_vuln_knowledge_base()
        count = 0
        for finding in report.findings:
            from whitemagic.tools.security.vuln_knowledge import VulnerabilityPattern
            pattern = VulnerabilityPattern(
                pattern_id=f"WM-{platform.upper()}-{count:04d}",
                name=finding["title"],
                category="unknown",
                severity=finding["severity"],
                description=finding["description"],
                source=platform,
                confidence=0.8,
                last_seen=time.time(),
            )
            kb.add_pattern(pattern)
            count += 1

        return count

    def status(self) -> dict[str, Any]:
        return {
            "platforms": list(self.PLATFORMS.keys()),
            "total_scraped": getattr(self, "_total_scraped", 0),
        }
