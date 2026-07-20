"""GitHub PR integration — fetch diffs, analyze with STRATA, post inline reviews.

Usage:
    from whitemagic.integrations.github_pr import GitHubPRReviewer

    reviewer = GitHubPRReviewer(token="ghp_...")
    review = reviewer.review_pr("owner/repo", pr_number=42)
    reviewer.post_review("owner/repo", pr_number=42, review=review)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    """A single finding from PR review."""
    file: str
    line: int
    severity: str  # critical, warning, style, nitpick
    message: str
    checker: str
    suggestion: str | None = None
    diff_line_type: str = "added"  # added, context


@dataclass
class PRReview:
    """Complete PR review result."""
    repo: str
    pr_number: int
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    approved: bool = False
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "findings": [
                {
                    "file": f.file,
                    "line": f.line,
                    "severity": f.severity,
                    "message": f.message,
                    "checker": f.checker,
                    "suggestion": f.suggestion,
                }
                for f in self.findings
            ],
            "summary": self.summary,
            "approved": self.approved,
            "stats": self.stats,
        }


class GitHubPRReviewer:
    """GitHub PR reviewer using STRATA for diff-aware code analysis.

    Args:
        token: GitHub API token (or set GITHUB_TOKEN env var).
        use_gh_cli: If True, use `gh` CLI instead of API calls.
    """

    SEVERITY_ORDER = {"critical": 0, "warning": 1, "style": 2, "nitpick": 3}

    def __init__(self, token: str | None = None, use_gh_cli: bool = True) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._use_gh = use_gh_cli and self._gh_available()

    def _gh_available(self) -> bool:
        try:
            subprocess.run(["gh", "--version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _gh(self, args: list[str]) -> str:
        """Run gh CLI command."""
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("gh CLI failed: %s", result.stderr)
            return ""
        return result.stdout

    def _api(self, endpoint: str, method: str = "GET", body: dict | None = None) -> dict[str, Any]:
        """Call GitHub API directly."""
        import urllib.request

        url = f"https://api.github.com{endpoint}"
        headers = {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def fetch_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the diff for a PR."""
        if self._use_gh:
            return self._gh(["pr", "diff", str(pr_number), "--repo", repo])
        else:
            result = self._api(f"/repos/{repo}/pulls/{pr_number}")
            diff_url = result.get("diff_url", "")
            if diff_url:
                import urllib.request
                with urllib.request.urlopen(diff_url, timeout=30) as resp:
                    return resp.read().decode("utf-8")
            return ""

    def fetch_pr_info(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch PR metadata (title, body, files, etc.)."""
        if self._use_gh:
            output = self._gh(["pr", "view", str(pr_number), "--repo", repo, "--json", "title,body,files,additions,deletions,changedFiles"])
            return json.loads(output) if output else {}
        else:
            return self._api(f"/repos/{repo}/pulls/{pr_number}")

    def review_pr(self, repo: str, pr_number: int, severity_threshold: str = "warning") -> PRReview:
        """Review a PR: fetch diff, analyze, return findings.

        Args:
            repo: GitHub repo in "owner/name" format.
            pr_number: PR number.
            severity_threshold: Minimum severity to report (critical, warning, style, nitpick).

        Returns:
            PRReview with all findings.
        """
        review = PRReview(repo=repo, pr_number=pr_number)

        diff = self.fetch_pr_diff(repo, pr_number)
        if not diff:
            review.summary = "Could not fetch PR diff."
            return review

        from whitemagic.tools.strata.diff_analyzer import DiffAnalyzer

        analyzer = DiffAnalyzer()
        changed_files = analyzer.parse_diff(diff)
        review.stats["files_changed"] = len(changed_files)
        review.stats["total_additions"] = sum(f.additions for f in changed_files)
        review.stats["total_deletions"] = sum(f.deletions for f in changed_files)

        threshold_rank = self.SEVERITY_ORDER.get(severity_threshold, 1)

        for file_diff in changed_files:
            findings = analyzer.analyze_file(file_diff)
            for finding in findings:
                if self.SEVERITY_ORDER.get(finding.severity, 3) <= threshold_rank:
                    review.findings.append(finding)

        critical = sum(1 for f in review.findings if f.severity == "critical")
        warnings = sum(1 for f in review.findings if f.severity == "warning")
        review.stats["critical_count"] = critical
        review.stats["warning_count"] = warnings
        review.stats["total_findings"] = len(review.findings)

        review.approved = critical == 0
        review.summary = self._generate_summary(review)

        return review

    def post_review(self, repo: str, pr_number: int, review: PRReview) -> bool:
        """Post a review to GitHub with inline comments."""
        if self._use_gh:
            return self._post_review_gh(repo, pr_number, review)
        else:
            return self._post_review_api(repo, pr_number, review)

    def _post_review_gh(self, repo: str, pr_number: int, review: PRReview) -> bool:
        """Post review using gh CLI."""
        event = "APPROVE" if review.approved else "REQUEST_CHANGES"
        if review.approved and review.findings:
            event = "COMMENT"

        body_parts = [review.summary, ""]
        for f in review.findings:
            body_parts.append(f"**{f.severity.upper()}** `{f.file}:{f.line}` — {f.message}")
            if f.suggestion:
                body_parts.append(f"```suggestion\n{f.suggestion}\n```")

        body = "\n".join(body_parts)
        result = subprocess.run(
            ["gh", "pr", "review", str(pr_number), "--repo", repo,
             "--event", event, "--body", body],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0

    def _post_review_api(self, repo: str, pr_number: int, review: PRReview) -> bool:
        """Post review using GitHub API with inline comments."""
        event = "APPROVE" if review.approved else "REQUEST_CHANGES"
        if review.approved and review.findings:
            event = "COMMENT"

        comments = []
        for f in review.findings:
            comments.append({
                "path": f.file,
                "line": f.line,
                "side": "RIGHT",
                "body": f"**{f.severity.upper()}** ({f.checker}): {f.message}"
                        + (f"\n```suggestion\n{f.suggestion}\n```" if f.suggestion else ""),
            })

        body = {
            "event": event,
            "body": review.summary,
            "comments": comments,
        }

        try:
            self._api(f"/repos/{repo}/pulls/{pr_number}/reviews", method="POST", body=body)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to post review: %s", e)
            return False

    def _generate_summary(self, review: PRReview) -> str:
        """Generate a human-readable review summary."""
        parts = ["## WhiteMagic Code Review", ""]

        if not review.findings:
            parts.append("No issues found. PR looks good!")
            return "\n".join(parts)

        critical = review.stats.get("critical_count", 0)
        warnings = review.stats.get("warning_count", 0)
        total = review.stats.get("total_findings", 0)

        parts.append(f"**{total} findings** ({critical} critical, {warnings} warnings)")
        parts.append("")
        parts.append(f"Files changed: {review.stats.get('files_changed', 0)}")
        parts.append(f"Lines: +{review.stats.get('total_additions', 0)} / -{review.stats.get('total_deletions', 0)}")
        parts.append("")

        if critical > 0:
            parts.append("Critical issues must be fixed before merge.")
        elif warnings > 0:
            parts.append("Warnings should be reviewed but are not blocking.")

        return "\n".join(parts)
