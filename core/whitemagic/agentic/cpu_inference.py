# ruff: noqa: BLE001
"""
CPU Inference Engine — Answer questions without AI API calls.

Uses local file system, code analysis, and rule-based reasoning
to answer common questions about the project, saving token costs.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from whitemagic.config.paths import get_project_root

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result of a CPU inference query."""

    query: str
    answer: str
    confidence: float = 0.0
    method: str = "unknown"
    evidence: list[str] = field(default_factory=list)
    tokens_equivalent: int = 0
    duration_ms: float = 0.0


class CPUInferenceEngine:
    """Local inference engine that answers questions without AI calls."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or get_project_root()
        self._patterns: list[tuple[str, str]] = [
            (r"how many.*(?:python|file)", "count"),
            (r"how many.*test", "count"),
            (r"how many.*(?:markdown|doc)", "count"),
            (r"how many.*garden", "count"),
            (r"find|search|locate|where", "file_search"),
            (r"what.*version", "version"),
            (r"list.*(?:garden|module|tool)", "list"),
        ]

    def infer(self, query: str) -> InferenceResult:
        """Answer a query using local analysis."""
        start = time.monotonic()
        query_lower = query.lower()

        method = self._classify(query_lower)
        if method == "count":
            result = self._count_inference(query)
        elif method == "file_search":
            result = self._file_search(query)
        elif method == "version":
            result = self._version_inference(query)
        elif method == "list":
            result = self._list_inference(query)
        else:
            result = InferenceResult(
                query=query,
                answer="Unable to resolve locally — needs AI.",
                confidence=0.2,
                method="fallback",
                tokens_equivalent=0,
            )

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def _classify(self, query_lower: str) -> str:
        for pattern, method in self._patterns:
            if re.search(pattern, query_lower):
                return method
        return "fallback"

    def _version_inference(self, query: str) -> InferenceResult:
        try:
            version_file = self.project_root / "VERSION"
            if version_file.exists():
                version = version_file.read_text().strip()
                return InferenceResult(
                    query=query,
                    answer=f"WhiteMagic version is {version}",
                    confidence=1.0,
                    method="version",
                    tokens_equivalent=500,
                )
        except Exception:
            pass
        return InferenceResult(
            query=query,
            answer="Version information not found.",
            confidence=0.5,
            method="version",
        )

    def _count_inference(self, query: str) -> InferenceResult:
        ql = query.lower()

        if "test" in ql:
            test_files = list((self.project_root / "core" / "tests").rglob("test_*.py"))
            return InferenceResult(
                query=query,
                answer=f"There are {len(test_files)} test files in core/tests/.",
                confidence=0.9,
                method="count",
                tokens_equivalent=100,
            )

        if "markdown" in ql or "doc" in ql:
            count = len(
                [f for f in self.project_root.rglob("*.md") if ".git" not in str(f)]
            )
            return InferenceResult(
                query=query,
                answer=f"There are {count} markdown files.",
                confidence=0.95,
                method="count",
                tokens_equivalent=count * 2,
            )

        if "garden" in ql:
            try:
                from whitemagic.gardens import get_all_gardens

                gardens = get_all_gardens()
                return InferenceResult(
                    query=query,
                    answer=f"There are {len(gardens)} gardens: {', '.join(gardens.keys())}",
                    confidence=1.0,
                    method="count",
                    tokens_equivalent=500,
                )
            except Exception:
                pass

        if "python" in ql or "file" in ql:
            count = len(
                [
                    f
                    for f in self.project_root.rglob("*.py")
                    if ".git" not in str(f) and "__pycache__" not in str(f)
                ]
            )
            return InferenceResult(
                query=query,
                answer=f"There are {count} Python files in the project.",
                confidence=0.95,
                method="count",
                tokens_equivalent=count * 5,
            )

        return InferenceResult(
            query=query,
            answer="Specify what to count: files, tests, gardens, docs.",
            confidence=0.3,
            method="count",
        )

    def _file_search(self, query: str) -> InferenceResult:
        words = [w for w in query.split() if len(w) > 3]
        matches: list[Path] = []
        for word in words:
            for f in self.project_root.rglob(f"*{word}*"):
                if ".git" not in str(f) and "__pycache__" not in str(f):
                    matches.append(f)
        if matches:
            return InferenceResult(
                query=query,
                answer=f"Found {len(matches)} files matching '{words[0] if words else query}'",
                confidence=0.9,
                method="file_search",
                evidence=[str(m.relative_to(self.project_root)) for m in matches[:5]],
                tokens_equivalent=len(matches) * 20,
            )
        return InferenceResult(
            query=query,
            answer=f"No files found matching '{words[0] if words else query}'",
            confidence=0.7,
            method="file_search",
        )

    def _list_inference(self, query: str) -> InferenceResult:
        ql = query.lower()
        if "garden" in ql:
            try:
                from whitemagic.gardens import get_all_gardens

                gardens = get_all_gardens()
                return InferenceResult(
                    query=query,
                    answer=f"Gardens: {', '.join(gardens.keys())}",
                    confidence=1.0,
                    method="list",
                    tokens_equivalent=500,
                )
            except Exception:
                pass
        return InferenceResult(
            query=query,
            answer="List type not recognized.",
            confidence=0.3,
            method="list",
        )


_engine: CPUInferenceEngine | None = None


def get_cpu_inference() -> CPUInferenceEngine:
    global _engine
    if _engine is None:
        _engine = CPUInferenceEngine()
    return _engine


def cpu_infer(query: str) -> InferenceResult:
    return get_cpu_inference().infer(query)
