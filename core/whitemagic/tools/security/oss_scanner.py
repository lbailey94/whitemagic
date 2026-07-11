"""OSS bounty scanner — scan GitHub repos for Algora/Opire bounties."""
import json
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BountyIssue:
    """A GitHub issue with a bounty attached."""
    repo: str
    issue_number: int
    title: str
    url: str
    labels: list[str]
    bounty_amount: str | None = None
    bounty_platform: str | None = None  # "algora", "opire"
    body_snippet: str = ""


class OSSBountyScanner:
    """Scan GitHub for open-source bounty opportunities."""

    ALGORA_LABELS = {"bounty", "algora", "algora-bounty"}
    OPIRE_LABELS = {"opire", "opire-bounty", "bounty"}

    def __init__(self) -> None:
        self._gh = None

    def _run_gh(self, args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug("gh CLI failed: %s", e)
        return None

    def scan_repo(self, repo: str) -> list[BountyIssue]:
        """Scan a single repo for bounty-labeled issues."""
        output = self._run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "bounty",
            "--limit", "50",
            "--json", "number,title,url,labels,body",
        ])
        if not output:
            return []
        try:
            issues = json.loads(output)
        except json.JSONDecodeError:
            return []

        bounties = []
        for issue in issues:
            labels = [label.get("name", "").lower() for label in issue.get("labels", [])]
            platform = self._detect_platform(labels)
            amount = self._extract_bounty_amount(issue.get("body", ""))
            bounties.append(BountyIssue(
                repo=repo,
                issue_number=issue.get("number", 0),
                title=issue.get("title", ""),
                url=issue.get("url", ""),
                labels=labels,
                bounty_amount=amount,
                bounty_platform=platform,
                body_snippet=issue.get("body", "")[:200],
            ))
        return bounties

    def scan_org(self, org: str) -> list[BountyIssue]:
        """Scan all repos in a GitHub org for bounties."""
        output = self._run_gh(["repo", "list", org, "--limit", "100", "--json", "nameWithOwner"])
        if not output:
            return []
        try:
            repos = json.loads(output)
        except json.JSONDecodeError:
            return []
        all_bounties = []
        for repo_info in repos:
            repo = repo_info.get("nameWithOwner", "")
            if repo:
                all_bounties.extend(self.scan_repo(repo))
        return all_bounties

    def _detect_platform(self, labels: list[str]) -> str | None:
        for label in labels:
            if label in self.ALGORA_LABELS:
                return "algora"
            if label in self.OPIRE_LABELS:
                return "opire"
        return None

    def _extract_bounty_amount(self, body: str) -> str | None:
        patterns = [
            r"\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*USD",
            r"(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$",
            r"Bounty:\s*\$?\s*(\d+(?:,\d{3})*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return "$" + match.group(1).replace(",", "")
        return None

    def status(self) -> dict[str, Any]:
        return {
            "gh_available": self._gh is not None,
            "algora_labels": list(self.ALGORA_LABELS),
            "opire_labels": list(self.OPIRE_LABELS),
        }


_scanner: OSSBountyScanner | None = None


def get_oss_scanner() -> OSSBountyScanner:
    global _scanner
    if _scanner is None:
        _scanner = OSSBountyScanner()
    return _scanner
