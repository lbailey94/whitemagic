"""Public audit report scraper — Code4rena, Sherlock, CodeHawks."""
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _get_state_root() -> Path:
    root = os.environ.get("WM_STATE_ROOT", "")
    if root:
        return Path(root)
    from whitemagic.config.paths import get_state_root as _get_wm_root
    return _get_wm_root()


@dataclass
class ScrapedReport:
    platform: str
    contest_name: str
    url: str
    findings: list[dict[str, Any]]
    raw_text: str
    scraped_at: float


@dataclass
class RateLimiter:
    """Token-bucket rate limiter for polite scraping."""
    interval: float = 2.0
    _last_request: float = field(default=0.0, init=False)

    def wait(self) -> None:
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_request = time.time()


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

    CACHE_TTL = 6 * 3600  # 6 hours
    USER_AGENT = "WhiteMagic-Security/1.0"

    def __init__(self, rate_interval: float = 2.0, cache_ttl: int | None = None) -> None:
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._rate_interval = rate_interval
        self._cache_ttl = cache_ttl or self.CACHE_TTL
        self._robots_cache: dict[str, dict[str, Any] | None] = {}
        self._total_scraped = 0

    def _get_rate_limiter(self, domain: str) -> RateLimiter:
        if domain not in self._rate_limiters:
            self._rate_limiters[domain] = RateLimiter(interval=self._rate_interval)
        return self._rate_limiters[domain]

    def _check_robots(self, url: str) -> bool:
        """Check robots.txt for the URL's domain. Returns True if allowed."""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._robots_cache:
            rules = self._robots_cache[base]
            if rules is None:
                return True
            for path in rules.get("disallowed", []):
                if parsed.path.startswith(path):
                    return False
            return True

        try:
            import requests
            resp = requests.get(f"{base}/robots.txt", timeout=10, headers={"User-Agent": self.USER_AGENT})
            if resp.status_code != 200:
                self._robots_cache[base] = None
                return True
            disallowed: list[str] = []
            in_our_section = False
            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("user-agent:"):
                    ua = line.split(":", 1)[1].strip()
                    in_our_section = ua == "*" or self.USER_AGENT.startswith(ua)
                elif in_our_section and line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.append(path)
            self._robots_cache[base] = {"disallowed": disallowed}
            for path in disallowed:
                if parsed.path.startswith(path):
                    return False
            return True
        except Exception:  # noqa: BLE001
            self._robots_cache[base] = None
            return True

    def _cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_dir = _get_state_root() / "scraper_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{url_hash}.txt"

    def _get_cached(self, url: str) -> str | None:
        cache_file = self._cache_path(url)
        if not cache_file.exists():
            return None
        age = time.time() - cache_file.stat().st_mtime
        if age > self._cache_ttl:
            return None
        return cache_file.read_text()

    def _set_cached(self, url: str, text: str) -> None:
        self._cache_path(url).write_text(text)

    def scrape_url(self, url: str, platform: str = "code4rena") -> ScrapedReport | None:
        """Scrape a single report URL with rate limiting, robots.txt, and caching."""
        cached = self._get_cached(url)
        if cached is not None:
            logger.debug("Cache hit for %s", url)
            findings = self._parse_findings(cached, platform)
            contest_name = self._extract_contest_name(url, cached)
            return ScrapedReport(platform=platform, contest_name=contest_name, url=url, findings=findings, raw_text=cached[:5000], scraped_at=time.time())

        if not self._check_robots(url):
            logger.warning("robots.txt disallows %s", url)
            return None

        parsed = urlparse(url)
        domain = parsed.netloc
        limiter = self._get_rate_limiter(domain)
        limiter.wait()

        try:
            import requests
            backoff = 1
            for attempt in range(3):
                response = requests.get(url, timeout=30, headers={"User-Agent": self.USER_AGENT})
                if response.status_code in (429, 503):
                    logger.warning("Got %d for %s, backing off %ds", response.status_code, url, backoff)
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                break
            else:
                logger.warning("Max retries reached for %s", url)
                return None

            if response.status_code != 200:
                logger.warning("Failed to fetch %s: %d", url, response.status_code)
                return None

            text = response.text
            self._set_cached(url, text)
            findings = self._parse_findings(text, platform)
            contest_name = self._extract_contest_name(url, text)
            self._total_scraped += 1

            return ScrapedReport(
                platform=platform,
                contest_name=contest_name,
                url=url,
                findings=findings,
                raw_text=text[:5000],
                scraped_at=time.time(),
            )
        except Exception as e:  # noqa: BLE001
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

    def scrape_batch(self, urls: list[str], platform: str = "code4rena") -> list[ScrapedReport]:
        """Scrape multiple URLs respecting rate limits across the batch."""
        results = []
        for url in urls:
            report = self.scrape_url(url, platform)
            if report:
                results.append(report)
        return results

    def status(self) -> dict[str, Any]:
        return {
            "platforms": list(self.PLATFORMS.keys()),
            "total_scraped": getattr(self, "_total_scraped", 0),
            "rate_interval": self._rate_interval,
            "cache_ttl": self._cache_ttl,
        }
