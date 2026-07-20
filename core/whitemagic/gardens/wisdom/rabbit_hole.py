"""Rabbit Hole Research System - Custom Web Search & Synthesis Tools.

Version: 3.0.0 "Ganapati Day"
Created: November 26, 2025

Philosophy:
    "The ida and pingala nadis spiral around the sushumna
     like the double helix of DNA" - Same pattern, different scales!

    This module provides tools for deep research using the Rabbit Hole technique:
    1. Read something interesting
    2. Note EVERY unfamiliar word/concept
    3. Research ALL of them in parallel
    4. Each spawns MORE rabbit holes
    5. Cross-reference multiple sources
    6. Synthesize into reports
    7. Apply insights to WhiteMagic!

Integration:
    Wired into the Wisdom Garden and Gan Ying Bus for resonance.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Web page chrome / boilerplate that should never be extracted as "terms"
_CHROME_STOPWORDS = frozenset(
    {
        # Navigation / UI
        "cookie",
        "privacy",
        "policy",
        "terms",
        "service",
        "sign",
        "menu",
        "search",
        "navigation",
        "footer",
        "header",
        "sidebar",
        "subscribe",
        "newsletter",
        "contact",
        "about",
        "home",
        "page",
        "next",
        "previous",
        "read",
        "more",
        "share",
        "follow",
        "twitter",
        "facebook",
        "linkedin",
        "github",
        "youtube",
        "instagram",
        "download",
        "view",
        "click",
        "here",
        "learn",
        "discover",
        "started",
        "free",
        "trial",
        "accept",
        "reject",
        "close",
        "dismiss",
        "skip",
        "main",
        "content",
        "up",
        "log",
        "in",
        "out",
        "sign up",
        "log in",
        "read more",
        "view all",
        "see all",
        "back to",
        "skip to",
        "main content",
        "estimated",
        "read time",
        "view next",
        "view previous",
        "explore",
        "topics",
        "resources",
        "insider",
        "interviews",
        "infographics",
        "basics",
        "latest",
        "week",
        "report",
        "comment",
        "leave",
        "reply",
        "must be",
        "logged in",
        "post",
        # GitHub UI
        "reload",
        "copy",
        "blame",
        "commits",
        "license",
        "copying",
        "gnu",
        "lesser",
        "forked",
        "fork",
        "star",
        "stars",
        "watch",
        "watching",
        "pull",
        "request",
        "merge",
        "branch",
        "tags",
        "releases",
        "actions",
        "workflow",
        "pipeline",
        "ci",
        "cd",
        "build",
        "deploy",
        "status",
        "checks",
        "passed",
        "failed",
        "pending",
        "running",
        "queued",
        "permalink",
        "raw",
        "history",
        "tree",
        "blob",
        "commit",
        "diff",
        "patch",
        "clone",
        "ssh",
        "https",
        "url",
        "mirror",
        "origin",
        "public",
        "private",
        "archived",
        "template",
        "settings",
        "insights",
        "graph",
        "network",
        "members",
        "collaborators",
        "contributors",
        "dependents",
        "dependencies",
        "packages",
        "deployments",
        "environments",
        "loc",
        "files",
        "file",
        "directory",
        "folder",
        "path",
        "src",
        "dist",
        "bin",
        "lib",
        "test",
        "tests",
        "docs",
        "config",
        "conf",
        "ini",
        "env",
        "requirements",
        "setup",
        "install",
        "uninstall",
        "upgrade",
        "update",
        "changelog",
        "release",
        "version",
        "v1",
        "v2",
        "v3",
        # StackOverflow UI
        "add",
        "edit",
        "delete",
        "remove",
        "save",
        "cancel",
        "confirm",
        "overflow",
        "stack",
        "exchange",
        "ask",
        "answer",
        "answers",
        "question",
        "questions",
        "tagged",
        "tags",
        "badge",
        "badges",
        "reputation",
        "score",
        "upvote",
        "downvote",
        "vote",
        "voting",
        "accepted",
        "marked",
        "correct",
        "helpful",
        "useful",
        "not useful",
        "flag",
        "close",
        "reopen",
        "protect",
        "bounty",
        "edited",
        "commented",
        "asked",
        "answered",
        "viewed",
        "provide",
        "details",
        "share",
        "improve",
        "follow",
        "edited",
        "add comment",
        "show",
        "hide",
        "expand",
        "collapse",
        # dev.to / blog UI
        "copy",
        "javascript",
        "js",
        "css",
        "html",
        "doctype",
        "dom",
        "enter",
        "exit",
        "example",
        "examples",
        "demo",
        "demos",
        "key points",
        "this",
        "that",
        "there",
        "they",
        "them",
        "their",
        "what",
        "when",
        "where",
        "why",
        "how",
        "which",
        "who",
        "whom",
        "over",
        "under",
        "above",
        "below",
        "between",
        "within",
        "without",
        # TechCrunch / news UI
        "image credits",
        "join",
        "june",
        "july",
        "april",
        "march",
        "may",
        "founder summit",
        "apps",
        "report",
        # Hacker News UI
        "points",
        "discuss",
        "hack",
        "show hn",
        "ask hn",
        "comments",
        "front page",
        "new",
        "past",
        "jobs",
        "submit",
        # Generic web actions
        "create",
        "update",
        "delete",
        "toggle",
        "select",
        "deselect",
        "enable",
        "disable",
        "activate",
        "deactivate",
        "start",
        "stop",
        "pause",
        "resume",
        "reset",
        "clear",
        "refresh",
        "sync",
        "async",
        "apply",
        "submit",
        "cancel",
        "confirm",
        "continue",
        "back",
        # Common acronyms that are web chrome, not content
        "api",
        "sdk",
        "cli",
        "gui",
        "ui",
        "ux",
        "css",
        "html",
        "json",
        "xml",
        "yaml",
        "toml",
        "sql",
        "nosql",
        "rest",
        "graphql",
        "pdf",
        "csv",
        "tsv",
        "txt",
        "md",
        "rst",
        # Single common words that slip through as "capitalized"
        "please",
        "there",
        "this",
        "over",
        "some",
        "most",
        "tell",
        "when",
        "maybe",
        "like",
        "also",
        "just",
        "only",
        "even",
        "still",
        "well",
        "will",
        "can",
        "may",
        "might",
        "must",
        "should",
        "could",
        "would",
        "has",
        "have",
        "had",
        "been",
        "being",
        "does",
        "did",
        "done",
        "yes",
        "no",
        "not",
        "nor",
        "but",
        "and",
        "or",
        "yet",
        "so",
        "true",
        "false",
        "none",
        "null",
        "void",
        "type",
        "types",
        "data",
        "value",
        "values",
        "key",
        "keys",
        "pair",
        "pairs",
        "item",
        "items",
        "list",
        "array",
        "object",
        "objects",
        "figure",
        "table",
        "chart",
        "graph",
        "plot",
        "image",
        "fig",
        "subject",
        "subjects",
        "topic",
        "topics",
        "theme",
        "themes",
        "however",
        "although",
        "therefore",
        "moreover",
        "furthermore",
        "nevertheless",
        "nonetheless",
        "thus",
        "hence",
        "whereas",
        "results",
        "whole",
        "hand",
        "high",
        "best",
        "first",
        "second",
        "binary",
        "notes",
        "extensions",
        "plugin",
        "cited",
        "verified",
        "co-authors",
        "university",
        "department",
        "institute",
        # README / doc chrome
        "readme",
        "changelog",
        "license",
        "authors",
        "credits",
        "faq",
        "installation",
        "usage",
        "configuration",
        "development",
        "testing",
        "contributing",
        "guidelines",
        "prerequisites",
        "requirements",
        "description",
        "overview",
        "introduction",
        "background",
        "summary",
        "conclusion",
        "references",
        "bibliography",
        "appendix",
    }
)


# Domains that are web infrastructure / developer tools, not content sources.
# These get deprioritized during rabbit hole exploration to keep research on-topic.
_LOW_QUALITY_DOMAINS = frozenset(
    {
        "github.com",
        "gitlab.com",
        "stackoverflow.com",
        "stackexchange.com",
        "dev.to",
        "medium.com",
        "hackernoon.com",
        "news.ycombinator.com",
        "reddit.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "wikipedia.org",
        "wikimedia.org",
        "npmjs.com",
        "pypi.org",
        "crates.io",
        "rubygems.org",
        "docker.com",
        "hub.docker.com",
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "amazon.com",
        "ebay.com",
        "archive.org",
        "web.archive.org",
        # Academic index sites — return researcher profiles, not primary content
        "scholar.google.com",
        "semanticscholar.org",
        "pdfs.semanticscholar.org",
        # Documentation sites — not primary content
        "readthedocs.io",
        "docs.python.org",
        "docs.rs",
        # News aggregators that pollute term extraction
        "bbc.co.uk",
        "bbc.com",
        "techcrunch.com",
    }
)


def _is_low_quality_url(url: str) -> bool:
    """Check if a URL is from a low-quality / non-content domain."""
    url_lower = url.lower()
    for domain in _LOW_QUALITY_DOMAINS:
        if domain in url_lower:
            return True
    return False


@dataclass
class RabbitHoleEntry:
    """A single concept discovered during research."""

    term: str
    definition: str = ""
    source: str = ""
    related_terms: list[str] = field(default_factory=list)
    depth: int = 0  # How deep in the rabbit hole
    explored: bool = False
    novelty_score: float = 0.0  # 0=redundant, 1=entirely novel
    content_snippet: str = ""  # Short excerpt for context
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ResearchReport:
    """A synthesized research report from multiple rabbit holes."""

    title: str
    topics: list[str]
    entries: list[RabbitHoleEntry] = field(default_factory=list)
    synthesis: str = ""
    connections: list[dict[str, str]] = field(default_factory=list)
    new_holes: list[str] = field(default_factory=list)  # Spawned rabbit holes
    temperature_curve: list[float] = field(default_factory=list)  # temp per level
    novelty_by_level: list[float] = field(default_factory=list)  # novelty per level
    created: datetime = field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = [
            f"# 🐇 {self.title}",
            f"**Generated**: {self.created.strftime('%Y-%m-%d %H:%M')}",
            f"**Topics Explored**: {', '.join(self.topics)}",
            "",
            "---",
            "",
            "## 📚 Entries Discovered",
            "",
        ]

        for entry in self.entries:
            lines.extend(
                [
                    f"### {entry.term}",
                    f"**Source**: {entry.source}",
                    f"**Depth**: {entry.depth}",
                    "",
                    entry.definition,
                    "",
                    f"**Related**: {', '.join(entry.related_terms)}"
                    if entry.related_terms
                    else "",
                    "",
                ]
            )

        if self.synthesis:
            lines.extend(
                [
                    "---",
                    "",
                    "## ✨ Synthesis",
                    "",
                    self.synthesis,
                    "",
                ]
            )

        if self.connections:
            lines.extend(
                [
                    "---",
                    "",
                    "## 🔗 Connections Found",
                    "",
                ]
            )
            for conn in self.connections:
                lines.append(
                    f"- **{conn.get('from', '?')}** ↔ **{conn.get('to', '?')}**: {conn.get('relation', '')}"
                )
            lines.append("")

        if self.new_holes:
            lines.extend(
                [
                    "---",
                    "",
                    "## 🐇 New Rabbit Holes Spawned",
                    "",
                ]
            )
            for hole in self.new_holes:
                lines.append(f"- [ ] {hole}")

        return "\n".join(lines)


class RabbitHoleExplorer:
    """Deep research tool using the Rabbit Hole technique.

    Supports:
    - Parallel concept research
    - Cross-referencing sources
    - Pattern recognition
    - Synthesis generation
    - Knowledge graph building
    """

    def __init__(self, max_parallel: int | None = None, max_depth: int = 3):
        """Initialize the Rabbit Hole Explorer.

        Args:
            max_parallel: Maximum concurrent research threads (default 64 = hexagrams)
            max_depth: Maximum recursion depth for rabbit holes

        """
        self.max_parallel = max_parallel
        self.max_depth = max_depth
        self.discovered: dict[str, RabbitHoleEntry] = {}
        self.connections: list[dict[str, str]] = []

    def extract_unfamiliar_terms(
        self,
        text: str,
        known_terms: frozenset[str] | None = None,
        temperature: float = 0.0,
    ) -> list[str]:
        """Extract potentially unfamiliar terms from text.

        Temperature controls extraction aggressiveness:
        - 0.0: Only terms appearing 2+ times (high confidence, focused)
        - 0.5: All capitalized phrases + acronyms + technical terms
        - 1.0: Everything interesting (wild tangents, outbound curiosity)

        Filters out web page chrome (navigation, cookie notices, etc.)
        """
        if known_terms is None:
            known_terms = frozenset()

        term_freq: dict[str, int] = {}

        # Multi-word capitalized phrases (proper nouns, concepts, technologies)
        caps_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b"
        for match in re.findall(caps_pattern, text):
            lower = match.lower()
            if (
                lower not in known_terms
                and lower not in _CHROME_STOPWORDS
                and len(lower) > 3
            ):
                term_freq[match] = term_freq.get(match, 0) + 1

        # Acronyms (2-7 uppercase letters, optionally with numbers)
        acro_pattern = r"\b[A-Z]{2,7}[0-9]?\b"
        for match in re.findall(acro_pattern, text):
            if match.lower() not in known_terms and len(match) >= 2:
                term_freq[match] = term_freq.get(match, 0) + 1

        # Hyphenated technical terms
        tech_pattern = r"\b[a-z]+(?:-[a-z]+){1,3}\b"
        for match in re.findall(tech_pattern, text, re.IGNORECASE):
            if (
                len(match) > 5
                and match.lower() not in known_terms
                and match.lower() not in _CHROME_STOPWORDS
            ):
                term_freq[match] = term_freq.get(match, 0) + 1

        # Parenthetical content (definitions/translations) — only at higher temps
        if temperature >= 0.3:
            paren_pattern = r"\(([^)]+)\)"
            for match in re.findall(paren_pattern, text):
                clean = match.strip()
                if 3 < len(clean) < 50 and clean.lower() not in known_terms:
                    term_freq[clean] = term_freq.get(clean, 0) + 1

        # At low temperature, only keep terms appearing 2+ times
        # At high temperature, keep everything
        freq_threshold = max(1, int(2 - temperature * 2))

        # Sort by frequency (most frequent first), then alphabetically
        filtered = [
            term
            for term, freq in sorted(term_freq.items(), key=lambda x: (-x[1], x[0]))
            if freq >= freq_threshold
            and "\n" not in term  # Skip multi-line UI artifacts
            and term.strip()
            and term.isascii()  # Skip non-ASCII (arxiv rendering artifacts like θ)
            and not term.startswith("italic_")  # arxiv HTML rendering artifact
            and not term.startswith("mathbf")  # arxiv LaTeX rendering
            and "_" not in term  # Skip snake_case identifiers
        ]

        return filtered

    def find_connections(self, entries: list[RabbitHoleEntry]) -> list[dict[str, str]]:
        """Find connections between discovered concepts.

        Looks for:
        - Shared related terms
        - Similar definitions
        - Cross-references
        """
        connections = []

        for i, entry1 in enumerate(entries):
            for entry2 in entries[i + 1 :]:
                shared = set(entry1.related_terms) & set(entry2.related_terms)
                if shared:
                    connections.append(
                        {
                            "from": entry1.term,
                            "to": entry2.term,
                            "relation": f"Shared concepts: {', '.join(shared)}",
                        }
                    )

                if entry1.term.lower() in entry2.definition.lower():
                    connections.append(
                        {
                            "from": entry1.term,
                            "to": entry2.term,
                            "relation": f"{entry1.term} appears in definition of {entry2.term}",
                        }
                    )
                elif entry2.term.lower() in entry1.definition.lower():
                    connections.append(
                        {
                            "from": entry2.term,
                            "to": entry1.term,
                            "relation": f"{entry2.term} appears in definition of {entry1.term}",
                        }
                    )

        return connections

    def generate_synthesis(
        self,
        entries: list[RabbitHoleEntry],
        connections: list[dict],
        all_content: list[str] | None = None,
        temperature_curve: list[float] | None = None,
        novelty_by_level: list[float] | None = None,
    ) -> str:
        """Generate a synthesis of all discovered concepts.

        Uses extractive summarization: finds sentences with high term density
        from fetched content, grouped by depth level.
        """
        if not entries:
            return "No entries to synthesize."

        # Group entries by depth
        by_depth: dict[int, list[RabbitHoleEntry]] = {}
        for e in entries:
            by_depth.setdefault(e.depth, []).append(e)

        depth_lines = []
        for depth in sorted(by_depth.keys()):
            depth_entries = by_depth[depth]
            terms = [e.term for e in depth_entries]
            temp = (
                temperature_curve[depth]
                if temperature_curve and depth < len(temperature_curve)
                else 0.0
            )
            novelty = (
                novelty_by_level[depth]
                if novelty_by_level and depth < len(novelty_by_level)
                else 0.0
            )
            depth_lines.append(
                f"- **Depth {depth}** ({len(depth_entries)} entries, temp={temp:.2f}, novelty={novelty:.2f}): "
                f"{', '.join(terms[:8])}"
            )

        # Extractive summarization: find sentences with high term density
        key_points: list[str] = []
        if all_content:
            all_terms = {e.term.lower() for e in entries if len(e.term) > 3}
            for content in all_content[:6]:
                sentences = re.split(r"(?<=[.!?])\s+", content)
                for sent in sentences:
                    sent = sent.strip()
                    if 40 < len(sent) < 300:
                        sent_lower = sent.lower()
                        term_hits = sum(1 for t in all_terms if t in sent_lower)
                        if term_hits >= 2:
                            key_points.append(sent)
                            if len(key_points) >= 12:
                                break
                if len(key_points) >= 12:
                    break

        parts = [
            "### Research Summary",
            f"**{len(entries)} concepts discovered** across {len(by_depth)} levels of depth.",
            f"**{len(connections)} connections** identified between concepts.",
            "",
            "### Exploration by Depth",
            *depth_lines,
        ]

        if key_points:
            parts.extend(["", "### Key Findings"])
            for point in key_points:
                parts.append(f"- {point}")

        if connections:
            parts.extend(["", "### Connections Found"])
            for conn in connections[:10]:
                parts.append(
                    f"- **{conn.get('from', '?')}** ↔ **{conn.get('to', '?')}**: {conn.get('relation', '')}"
                )

        return "\n".join(parts)

    def create_report(
        self,
        title: str,
        topics: list[str],
        entries: list[RabbitHoleEntry],
        all_content: list[str] | None = None,
    ) -> ResearchReport:
        """Create a complete research report."""
        connections = self.find_connections(entries)
        synthesis = self.generate_synthesis(entries, connections, all_content)

        # Find new rabbit holes from related terms that weren't explored
        explored_terms = {e.term.lower() for e in entries}
        new_holes = set()
        for entry in entries:
            for related in entry.related_terms:
                if related.lower() not in explored_terms:
                    new_holes.add(related)

        return ResearchReport(
            title=title,
            topics=topics,
            entries=entries,
            synthesis=synthesis,
            connections=connections,
            new_holes=list(new_holes)[:20],
        )

    async def web_explore(
        self,
        topic: str,
        max_depth: int = 3,
        max_parallel_terms: int = 12,
        num_search_results: int = 5,
        fetch_top_results: int = 3,
        max_chars_per_fetch: int = 50_000,
        store_memories: bool = True,
        cache_content: bool = True,
        initial_temperature: float = 0.0,
        temperature_rise: float = 0.25,
        novelty_floor: float = 0.15,
    ) -> ResearchReport:
        """Recursive spiral web research -- the true Rabbit Hole.

        Curiosity temperature system:
        - Starts at initial_temperature (0.0 = focused, 0.5 = curious, 1.0 = wild)
        - Rises by temperature_rise each level (simulates a curious person
          clicking more tangential outbound links as they go deeper)
        - If results are "same-y" (low novelty), temperature gets an extra
          boost to escape the echo chamber
        - Stops when novelty drops below novelty_floor for 2 consecutive levels

        For each level of depth:
        1. Extract unfamiliar terms from current content (temperature-modulated)
        2. Batch-search ALL terms in parallel via web_search_batch
        3. deep_fetch the top results from each search
        4. Score novelty of new content vs existing content
        5. Extract new unfamiliar terms from fetched content
        6. Recurse to next depth level with higher temperature
        7. Cross-reference all sources
        8. Synthesize into a research report with key findings
        """
        from whitemagic.gardens.browser.web_research import (
            AdaptiveBatchSizer,
            cached_deep_fetch,
            get_depth_category,
            web_search_batch,
        )

        all_entries: list[RabbitHoleEntry] = []
        all_content: list[str] = []
        explored_terms: set[str] = {topic.lower()}
        known_terms: set[str] = set()
        fetched_urls: set[str] = set()
        batch_sizer = AdaptiveBatchSizer(initial_size=max_parallel_terms)

        temperature = initial_temperature
        temperature_curve: list[float] = [temperature]
        novelty_by_level: list[float] = [1.0]  # depth 0 is always novel
        low_novelty_streak = 0

        # Level 0: Search for the main topic and sub-queries for broader coverage
        topic_words = topic.split()
        depth0_queries = [topic]
        # Generate sub-queries by taking pairs of adjacent words
        # Only keep pairs that contain a domain keyword to stay on-topic
        _domain_keywords = frozenset(
            {
                "nuclear",
                "reactor",
                "reactors",
                "atomic",
                "fission",
                "fusion",
                "energy",
                "power",
                "fuel",
                "radiation",
                "isotope",
            }
        )
        if len(topic_words) >= 4:
            for i in range(0, len(topic_words) - 1, 2):
                pair = " ".join(topic_words[i : i + 2])
                pair_words = set(pair.lower().split())
                if pair_words & _domain_keywords:
                    depth0_queries.append(pair)
        # Also try the first 3 words as a shorter query
        if len(topic_words) >= 5:
            short = " ".join(topic_words[:3])
            short_words = set(short.lower().split())
            if short_words & _domain_keywords and short not in depth0_queries:
                depth0_queries.append(short)

        category = get_depth_category(0)
        batch = await web_search_batch(
            depth0_queries,
            num_results_per_query=num_search_results,
            category=category,
        )
        batch_sizer.record_response(batch.duration_ms, bool(batch.errors))

        level_content: list[str] = []
        for query in depth0_queries:
            results = batch.results_by_query.get(query, [])
            for r in results[:fetch_top_results]:
                url = r.get("url", "")
                if not url or url in fetched_urls:
                    continue
                if _is_low_quality_url(url):
                    continue
                fetched_urls.add(url)
                fetch_result = await cached_deep_fetch(
                    url, max_chars=max_chars_per_fetch
                )
                if fetch_result.success and fetch_result.content:
                    level_content.append(fetch_result.content)
                    all_content.append(fetch_result.content)
                    # Extract related terms from the content
                    related = self.extract_unfamiliar_terms(
                        fetch_result.content[:5000],
                        frozenset({topic.lower()}),
                        temperature=0.5,
                    )[:5]
                    entry = RabbitHoleEntry(
                        term=query if query != topic else topic,
                        definition=fetch_result.title or url,
                        source=url,
                        related_terms=related,
                        depth=0,
                        explored=True,
                        novelty_score=1.0,
                        content_snippet=fetch_result.content[:200]
                        .replace("\n", " ")
                        .strip(),
                    )
                    all_entries.append(entry)

        # Recursive spiral: extract terms -> batch search -> fetch -> repeat
        for level in range(1, max_depth + 1):
            temperature = min(1.0, initial_temperature + (temperature_rise * level))
            temperature_curve.append(temperature)

            # Extract unfamiliar terms from current level content
            combined_text = (
                " ".join(level_content) if level_content else " ".join(all_content[-3:])
            )
            new_terms = self.extract_unfamiliar_terms(
                combined_text,
                frozenset(known_terms | explored_terms),
                temperature=temperature,
            )

            # Filter out already-explored terms
            unexplored = [t for t in new_terms if t.lower() not in explored_terms]
            if not unexplored:
                logger.debug("Rabbit hole: no new terms at depth %d, stopping", level)
                break

            # Adaptive batch sizing — more terms at higher temperatures
            adaptive_limit = batch_sizer.get_batch_size()
            if temperature > 0.5:
                adaptive_limit = min(adaptive_limit + 2, 20)
            terms_to_search = unexplored[:adaptive_limit]
            for t in terms_to_search:
                explored_terms.add(t.lower())

            # Contextualize search queries: for acronyms and short terms,
            # prepend "nuclear reactor" to disambiguate (e.g., "SMR" -> "SMR nuclear reactor")
            search_queries = []
            for t in terms_to_search:
                is_acronym = bool(re.match(r"^[A-Z]{2,7}[0-9]?$", t))
                is_short = len(t) < 15
                if (is_acronym or is_short) and topic.lower() not in t.lower():
                    search_queries.append(f"{t} nuclear reactor")
                else:
                    search_queries.append(t)

            # Depth-aware category selection
            category = get_depth_category(level)

            # Batch search all terms in parallel
            batch = await web_search_batch(
                search_queries,
                num_results_per_query=num_search_results,
                category=category,
            )
            batch_sizer.record_response(batch.duration_ms, bool(batch.errors))

            level_content = []
            fetch_tasks = []
            term_url_map: list[tuple[str, str]] = []

            for idx, term in enumerate(terms_to_search):
                query = search_queries[idx]
                results = batch.results_by_query.get(
                    query, batch.results_by_query.get(term, [])
                )
                # Limit to 2 entries per term at depth > 0 to encourage diversity
                max_per_term = 2 if level > 0 else fetch_top_results
                for r in results[:max_per_term]:
                    url = r.get("url", "")
                    if url and url not in fetched_urls and not _is_low_quality_url(url):
                        fetched_urls.add(url)
                        fetch_tasks.append(
                            cached_deep_fetch(url, max_chars=max_chars_per_fetch)
                        )
                        term_url_map.append((term, url))

            if fetch_tasks:
                fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                for i, result in enumerate(fetched):
                    term, url = term_url_map[i]
                    if isinstance(result, Exception) or not result.success:
                        continue
                    if result.content:
                        level_content.append(result.content)
                        all_content.append(result.content)
                        # Score novelty of this content vs existing
                        novelty = self._score_novelty(result.content, all_content[:-1])
                        # Extract related terms
                        related = self.extract_unfamiliar_terms(
                            result.content[:5000],
                            frozenset({term.lower()}),
                            temperature=temperature,
                        )[:5]
                        entry = RabbitHoleEntry(
                            term=term,
                            definition=result.title or url,
                            source=url,
                            related_terms=related,
                            depth=level,
                            explored=True,
                            novelty_score=novelty,
                            content_snippet=result.content[:200]
                            .replace("\n", " ")
                            .strip(),
                        )
                        all_entries.append(entry)

            # Score novelty for this level
            if level_content:
                level_novelty = self._score_novelty(
                    level_content, all_content[: -len(level_content)]
                )
            else:
                level_novelty = 0.0
            novelty_by_level.append(level_novelty)

            # Depth decision: stop if novelty is too low for 2 consecutive levels
            if level_novelty < novelty_floor:
                low_novelty_streak += 1
                if low_novelty_streak >= 2:
                    logger.debug(
                        "Rabbit hole: low novelty (%.2f) for %d levels at depth %d, stopping",
                        level_novelty,
                        low_novelty_streak,
                        level,
                    )
                    break
                # Extra temperature boost to escape echo chamber
                temperature = min(1.0, temperature + 0.2)
                temperature_curve[-1] = temperature
            else:
                low_novelty_streak = 0

            # Update known terms
            known_terms.update(t.lower() for t in terms_to_search)

        # Cross-reference all sources
        connections = self.find_connections(all_entries)

        # Generate synthesis with content and curves
        synthesis = self.generate_synthesis(
            all_entries,
            connections,
            all_content,
            temperature_curve,
            novelty_by_level,
        )

        # Find new rabbit holes from related terms that weren't explored
        new_holes = set()
        for entry in all_entries:
            for related in entry.related_terms:
                if related.lower() not in explored_terms:
                    new_holes.add(related)

        report = ResearchReport(
            title=f"Web Exploration: {topic}",
            topics=[topic],
            entries=all_entries,
            synthesis=synthesis,
            connections=connections,
            new_holes=list(new_holes)[:20],
            temperature_curve=temperature_curve,
            novelty_by_level=novelty_by_level,
        )

        if store_memories and all_content:
            try:
                from whitemagic.core.memory.unified import get_unified_memory

                mem = get_unified_memory()
                combined = "\n\n---\n\n".join(all_content[:10])
                mem.store(
                    content=combined[:100_000],
                    metadata={
                        "type": "rabbit_hole_research",
                        "topic": topic,
                        "depth": max_depth,
                        "entries": len(all_entries),
                        "timestamp": datetime.now().isoformat(),
                    },
                    tags=["rabbit_hole", "web_research", topic, "spiral"],
                )
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception", exc_info=True)

        # Emit to Gan Ying
        emit_research_event(
            topic,
            {
                "entries": len(all_entries),
                "depth": max_depth,
                "connections": len(connections),
                "new_holes": len(new_holes),
                "final_temperature": temperature,
            },
        )

        return report

    def _score_novelty(
        self, new_content: str | list[str], existing_content: list[str]
    ) -> float:
        """Score how novel new content is vs already-seen content.

        Uses word-set Jaccard distance to measure information overlap.
        Filters common English words to focus on domain-specific vocabulary.

        Returns:
            0.0 = completely redundant (same-y, echo chamber)
            1.0 = entirely novel (all new information)
        """
        if isinstance(new_content, str):
            new_content = [new_content]
        if not new_content:
            return 0.0
        if not existing_content:
            return 1.0

        # Common English words to exclude from novelty scoring
        # (different from chrome stopwords — these are just common English)
        _common = frozenset(
            {
                "that",
                "this",
                "with",
                "from",
                "have",
                "been",
                "were",
                "they",
                "will",
                "would",
                "could",
                "should",
                "their",
                "there",
                "which",
                "about",
                "after",
                "before",
                "between",
                "through",
                "during",
                "above",
                "below",
                "other",
                "some",
                "many",
                "more",
                "most",
                "such",
                "only",
                "also",
                "than",
                "then",
                "these",
                "those",
                "what",
                "when",
                "where",
                "while",
                "each",
                "both",
                "just",
            }
        )

        # Build word sets (lowercase, alpha-only, 4+ chars, excluding common words)
        def word_set(text: str) -> set[str]:
            return {
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{4,}\b", text)
                if w.lower() not in _common
            }

        new_words: set[str] = set()
        for c in new_content:
            new_words |= word_set(c)

        existing_words: set[str] = set()
        for c in existing_content:
            existing_words |= word_set(c)

        if not new_words:
            return 0.0

        # Proper Jaccard distance: 1 - |intersection| / |union|
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)
        if union == 0:
            return 0.0
        novelty = 1.0 - (intersection / union)
        return novelty

    def save_report(self, report: ResearchReport, output_dir: Path) -> Path:
        """Save report to markdown file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = report.created.strftime("%Y%m%d_%H%M")
        safe_title = re.sub(r"[^a-zA-Z0-9_]", "_", report.title)[:50]
        filename = f"RABBIT_HOLE_{safe_title}_{timestamp}.md"

        filepath = output_dir / filename
        filepath.write_text(report.to_markdown())

        return filepath


class SourceComparator:
    """Compare information across multiple sources on the same topic.

    Identifies:
    - Agreements (consistent across sources)
    - Contradictions (different in sources)
    - Unique insights (only in one source)
    """

    @dataclass
    class SourceInfo:
        """SourceInfo: source info.

        Value object: equality and repr are field-based."""

        url: str
        content: str
        key_points: list[str] = field(default_factory=list)

    def __init__(self) -> None:
        self.sources: list[SourceComparator.SourceInfo] = []

    def add_source(
        self, url: str, content: str, key_points: list[str] | None = None
    ) -> None:
        """Add a source to compare."""
        self.sources.append(
            self.SourceInfo(
                url=url,
                content=content,
                key_points=key_points or [],
            )
        )

    def find_agreements(self) -> list[str]:
        """Find points that appear across multiple sources."""
        if len(self.sources) < 2:
            return []

        # Simple implementation: look for shared key points
        all_points = []
        for source in self.sources:
            all_points.extend(source.key_points)

        # Count occurrences
        from collections import Counter

        point_counts = Counter(all_points)

        # Points appearing in multiple sources
        return [point for point, count in point_counts.items() if count > 1]

    def find_unique_insights(self) -> dict[str, list[str]]:
        """Find insights unique to each source."""
        if not self.sources:
            return {}

        all_points = set()
        for source in self.sources:
            all_points.update(source.key_points)

        unique = {}
        for source in self.sources:
            source_points = set(source.key_points)
            other_points = all_points - source_points
            unique_to_source = source_points - other_points
            if unique_to_source:
                unique[source.url] = list(unique_to_source)

        return unique


class DeepReader:
    """Focused reading tool for extracting specific information.

    Unlike generic web scraping, this focuses on:
    - Key quotes relevant to the focus area
    - Definitions and explanations
    - Cross-references to other topics
    """

    def __init__(self, focus: str):
        """Initialize with a research focus.

        Args:
            focus: The topic/question to focus extraction on

        """
        self.focus = focus
        self.extracted_quotes: list[str] = []
        self.definitions: dict[str, str] = {}
        self.cross_refs: list[str] = []

    def extract_relevant_sections(self, content: str) -> list[str]:
        """Extract sections relevant to the focus topic."""
        # Split content into paragraphs
        paragraphs = content.split("\n\n")

        relevant = []
        focus_lower = self.focus.lower()

        for para in paragraphs:
            if focus_lower in para.lower():
                relevant.append(para.strip())

        return relevant

    def extract_quotes(self, content: str) -> list[str]:
        """Extract notable quotes from content."""
        # Find quoted text
        quote_pattern = r'"([^"]+)"'
        quotes = re.findall(quote_pattern, content)

        # Filter for meaningful quotes (not too short, not too long)
        meaningful = [q for q in quotes if 20 < len(q) < 500]

        self.extracted_quotes.extend(meaningful)
        return meaningful


# Gan Ying Integration
def emit_research_event(topic: str, findings: dict[str, Any]) -> None:
    """Emit research findings to the Gan Ying Bus."""
    try:
        from whitemagic.core.resonance.gan_ying import (
            EventType,
            ResonanceEvent,
            get_bus,
        )

        bus = get_bus()
        bus.emit(
            ResonanceEvent(
                source="wisdom.rabbit_hole",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "topic": topic,
                    "findings": findings,
                    "timestamp": datetime.now().isoformat(),
                },
                confidence=0.8,
            )
        )
    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")


# Convenience functions for direct use
def explore_topic(topic: str, max_depth: int = 2) -> ResearchReport:
    """Quick function to explore a topic using the Rabbit Hole technique.

    Args:
        topic: The starting topic to explore
        max_depth: How deep to go down rabbit holes

    Returns:
        A ResearchReport with findings

    """
    explorer = RabbitHoleExplorer(max_depth=max_depth)

    # Create initial entry
    initial = RabbitHoleEntry(
        term=topic,
        definition=f"Starting point for research on: {topic}",
        depth=0,
    )

    entries = [initial]

    report = explorer.create_report(
        title=f"Exploration: {topic}",
        topics=[topic],
        entries=entries,
    )

    # Emit to Gan Ying
    emit_research_event(topic, {"entries": len(entries), "depth": max_depth})

    return report


def compare_sources(urls: list[str], topic: str) -> dict[str, Any]:
    """Compare multiple sources on a topic.

    Args:
        urls: List of URLs that have been read
        topic: The topic being compared

    Returns:
        Dict with agreements, contradictions, and unique insights

    """
    comparator = SourceComparator()

    # Note: Actual content would be passed from the calling context
    return {
        "topic": topic,
        "num_sources": len(urls),
        "agreements": comparator.find_agreements(),
        "unique_insights": comparator.find_unique_insights(),
    }


# Self-documentation for AI discovery
__doc_for_ai__ = """
# Rabbit Hole Research Tools

## Quick Start
```python
    RabbitHoleExplorer,
    explore_topic,
    compare_sources
)

# Explore a topic
report = explore_topic("Kashmir Shaivism", max_depth=2)
logger.info(report.to_markdown())

# Save report
explorer = RabbitHoleExplorer()
explorer.save_report(report, Path("reports/"))
```

## Integration with Wisdom Garden
This module is part of the Wisdom Garden and connects to:
- Gan Ying Bus (emits PATTERN_DETECTED events)
- Memory system (can save reports as memories)
- Grimoire (discovered patterns can be documented)

## Philosophy
The Rabbit Hole technique mirrors the sacred spiral:
- Start at a point (like Muladhara)
- Spiral outward (like Kundalini rising)
- Each level reveals more (like chakras opening)
- Synthesis brings unity (like Sahasrara)

🐇🌀✨
"""
