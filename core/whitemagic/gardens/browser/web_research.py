# ruff: noqa: BLE001
"""Web Research Engine — Fast-path web fetching, search, and deep research.

Provides three tiers of web access:
1. web_fetch  — httpx + html2text for instant read-only content (no browser needed)
2. web_search — DuckDuckGo HTML scraping for zero-API-key web search
3. research_topic — Orchestrator combining search + fetch + Rabbit Hole synthesis

This module is designed to replace external search MCP tools (like Exa) with
WhiteMagic's own internal capabilities, giving AI agents self-contained web
research without API keys or cloud dependencies.

Integration:
    Wired into the Browser Garden and Gan Ying Bus for resonance.
    Results can be stored as memories for future recall.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import html2text as _html2text

    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


@dataclass
class FetchResult:
    """Result from fetching a single URL."""

    url: str
    title: str = ""
    content: str = ""
    content_length: int = 0
    status_code: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def success(self) -> bool:
        """
        Perform the success operation.

        Returns:
            bool
        """
        return self.error is None and self.status_code in range(200, 400)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:500] + "..."
            if len(self.content) > 500
            else self.content,
            "content_length": self.content_length,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str = ""
    position: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
        }


@dataclass
class SearchResponse:
    """Response from a web search."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_results: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def success(self) -> bool:
        """
        Perform the success operation.

        Returns:
            bool
        """
        return self.error is None and len(self.results) > 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ResearchFinding:
    """A single finding from deep research."""

    url: str
    title: str
    content: str
    relevance: str = ""
    key_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "url": self.url,
            "title": self.title,
            "content_preview": self.content[:300] + "..."
            if len(self.content) > 300
            else self.content,
            "content_length": len(self.content),
            "relevance": self.relevance,
            "key_points": self.key_points,
        }


@dataclass
class ResearchReport:
    """Complete research report from deep topic exploration."""

    topic: str
    findings: list[ResearchFinding] = field(default_factory=list)
    synthesis: str = ""
    related_topics: list[str] = field(default_factory=list)
    sources_searched: int = 0
    sources_fetched: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "topic": self.topic,
            "findings": [f.to_dict() for f in self.findings],
            "synthesis": self.synthesis,
            "related_topics": self.related_topics,
            "sources_searched": self.sources_searched,
            "sources_fetched": self.sources_fetched,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


_DEFAULT_HEADERS = {
    "User-Agent": "WhiteMagic/15.0 (Research Agent; +https://github.com/whitemagic-ai/whitemagic)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


def _html_to_text(html: str, max_chars: int = 50_000) -> str:
    """Convert HTML to clean markdown-ish text, optimized for AI consumption."""
    if HAS_HTML2TEXT:
        h = _html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap
        h.skip_internal_links = True
        h.inline_links = True
        h.protect_links = True
        h.unicode_snob = True
        text = h.handle(html)
    elif HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    else:
        # Desperate fallback: regex strip
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text[:max_chars].strip()


def _extract_title(html: str) -> str:
    """Extract page title from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Clean HTML entities
        title = re.sub(r"&amp;", "&", title)
        title = re.sub(r"&lt;", "<", title)
        title = re.sub(r"&gt;", ">", title)
        title = re.sub(r"&#\d+;", "", title)
        return title[:200]
    return ""


async def web_fetch(
    url: str,
    max_chars: int = 30_000,
    timeout: float = 15.0,
    follow_redirects: bool = True,
) -> FetchResult:
    """Fetch a URL and return clean text content.

    Uses httpx for fast async HTTP — no browser needed.
    Converts HTML to clean text optimized for AI token usage.

    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return (default 30K)
        timeout: Request timeout in seconds
        follow_redirects: Follow HTTP redirects

    Returns:
        FetchResult with clean text content
    """
    if not HAS_HTTPX:
        return FetchResult(url=url, error="httpx not installed: pip install httpx")

    start = time.monotonic()

    try:
        async with httpx.AsyncClient(
            headers=_DEFAULT_HEADERS,
            follow_redirects=follow_redirects,
            timeout=timeout,
        ) as client:
            response = await client.get(url)
            duration = (time.monotonic() - start) * 1000

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type or "application/xhtml" in content_type:
                html = response.text
                title = _extract_title(html)
                content = _html_to_text(html, max_chars=max_chars)
            elif "text/plain" in content_type or "application/json" in content_type:
                title = urlparse(url).path.split("/")[-1] or url
                content = response.text[:max_chars]
            else:
                title = urlparse(url).path.split("/")[-1] or url
                content = (
                    f"[Binary content: {content_type}, {len(response.content)} bytes]"
                )

            return FetchResult(
                url=str(response.url),
                title=title,
                content=content,
                content_length=len(content),
                status_code=response.status_code,
                duration_ms=duration,
            )

    except httpx.TimeoutException:
        return FetchResult(
            url=url,
            error=f"Timeout after {timeout}s",
            duration_ms=(time.monotonic() - start) * 1000,
        )
    except Exception as e:
        return FetchResult(
            url=url,
            error=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


async def _brave_search(
    query: str,
    num_results: int = 8,
    timeout: float = 10.0,
) -> SearchResponse | None:
    """Search via Brave Search API (free tier: 2000 queries/month).

    Returns None if Brave API key is not configured, allowing DDG fallback.
    Set BRAVE_SEARCH_API_KEY env var to enable.
    """
    from whitemagic.security.sanitization import get_env_var

    try:
        api_key = get_env_var("BRAVE_SEARCH_API_KEY", required=False)
    except ValueError:
        return None

    if not api_key or not HAS_HTTPX:
        return None

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": min(num_results, 20)},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )
            duration = (time.monotonic() - start) * 1000

            if response.status_code != 200:
                logger.debug(
                    "Brave search returned %s, falling back to DDG",
                    response.status_code,
                    exc_info=True,
                )
                return None

            data = response.json()
            results: list[SearchResult] = []
            for i, item in enumerate(data.get("web", {}).get("results", [])):
                if i >= num_results:
                    break
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                        position=i + 1,
                    )
                )

            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                duration_ms=duration,
            )
    except Exception as e:
        logger.debug("Brave search failed (%s), falling back to DDG", e, exc_info=True)
        return None


_CATEGORY_MODIFIERS: dict[str, list[str]] = {
    "people": ["site:linkedin.com/in", "site:github.com", "site:twitter.com"],
    "company": ["site:linkedin.com/company", "site:crunchbase.com", "site:github.com"],
    "academic": [
        "site:arxiv.org",
        "site:scholar.google.com",
        "site:semanticscholar.org",
        "site:doi.org",
    ],
    "code": [
        "site:github.com",
        "site:stackoverflow.com",
        "site:gitlab.com",
        "site:docs.python.org",
    ],
    "docs": ["site:docs.", "site:readthedocs.io", "site:dev.to", "site:medium.com"],
    "news": [
        "site:news.ycombinator.com",
        "site:techcrunch.com",
        "site:reuters.com",
        "site:bbc.co.uk",
    ],
}


def _apply_category(query: str, category: str | None) -> str:
    """Modify search query based on category filter (like Exa's category:people/company)."""
    if not category or category == "general":
        return query
    modifiers = _CATEGORY_MODIFIERS.get(category.lower())
    if not modifiers:
        return query
    # Use OR to join site modifiers for broader coverage
    site_filter = " OR ".join(modifiers)
    return f"({query}) ({site_filter})"


_search_cache: dict[str, tuple[float, SearchResponse]] = {}
_SEARCH_CACHE_TTL = 3600  # 1 hour


def _search_cache_key(query: str, num_results: int, category: str | None) -> str:
    """Build a cache key for search parameters."""
    cat = category or "none"
    return f"{query}::{num_results}::{cat}"


def _get_cached_search(
    query: str, num_results: int, category: str | None
) -> SearchResponse | None:
    """Return cached search result if still valid."""
    import time as _time

    key = _search_cache_key(query, num_results, category)
    if key in _search_cache:
        ts, result = _search_cache[key]
        if _time.time() - ts < _SEARCH_CACHE_TTL:
            logger.debug("Search cache hit: %s", query[:50])
            return result
        del _search_cache[key]
    return None


def _store_cached_search(
    query: str, num_results: int, category: str | None, result: SearchResponse
) -> None:
    """Store search result in cache."""
    import time as _time

    key = _search_cache_key(query, num_results, category)
    _search_cache[key] = (_time.time(), result)
    # Evict expired entries to prevent unbounded growth
    now = _time.time()
    expired = [
        k for k, (ts, _) in _search_cache.items() if now - ts > _SEARCH_CACHE_TTL
    ]
    for k in expired:
        del _search_cache[k]


def clear_search_cache() -> int:
    """Clear the in-memory search cache. Returns count of entries removed."""
    count = len(_search_cache)
    _search_cache.clear()
    return count


async def web_search(
    query: str,
    num_results: int = 8,
    timeout: float = 10.0,
    category: str | None = None,
    force_refresh: bool = False,
) -> SearchResponse:
    """Search the web using Brave API (preferred) or DuckDuckGo HTML (fallback).

    If BRAVE_SEARCH_API_KEY is set, uses Brave Search API (fast, reliable,
    2000 free queries/month). Otherwise falls back to DuckDuckGo HTML scraping.

    Args:
        query: Search query string
        num_results: Maximum number of results to return
        timeout: Request timeout in seconds
        category: Optional category filter — 'people', 'company', 'academic',
                  'code', 'docs', 'news' — modifies query with site filters
                  (analogous to Exa's category:people / category:company)

    Returns:
        SearchResponse with list of results
    """
    if not force_refresh:
        cached = _get_cached_search(query, num_results, category)
        if cached is not None:
            return cached

    modified_query = _apply_category(query, category)

    brave_result = await _brave_search(modified_query, num_results, timeout)
    if brave_result is not None:
        _store_cached_search(query, num_results, category, brave_result)
        return brave_result

    # Fallback: DuckDuckGo HTML scraping (no API key needed)
    if not HAS_HTTPX:
        return SearchResponse(
            query=query, error="httpx not installed: pip install httpx"
        )
    if not HAS_BS4:
        return SearchResponse(
            query=query,
            error="beautifulsoup4 not installed: pip install beautifulsoup4",
        )

    start = time.monotonic()

    try:
        encoded_query = quote_plus(modified_query)
        # Use DuckDuckGo HTML-only endpoint (no JavaScript required)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        headers = {
            **_DEFAULT_HEADERS,
            "Referer": "https://duckduckgo.com/",
        }

        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            response = await client.get(url)
            duration = (time.monotonic() - start) * 1000

            if response.status_code != 200:
                return SearchResponse(
                    query=query,
                    error=f"Search returned status {response.status_code}",
                    duration_ms=duration,
                )

            soup = BeautifulSoup(response.text, "lxml")
            results: list[SearchResult] = []

            # DuckDuckGo HTML results are in .result elements
            for i, result_div in enumerate(soup.select(".result")):
                if i >= num_results:
                    break

                # Extract title and URL
                title_tag = result_div.select_one(".result__a")
                snippet_tag = result_div.select_one(".result__snippet")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")

                # DuckDuckGo wraps URLs in redirects, extract actual URL
                if isinstance(href, str) and "uddg=" in href:
                    # Extract from redirect: //duckduckgo.com/l/?uddg=ENCODED_URL&...
                    from urllib.parse import parse_qs
                    from urllib.parse import urlparse as _urlparse

                    parsed = _urlparse(href)
                    params = parse_qs(parsed.query)
                    actual_urls = params.get("uddg", [])
                    if actual_urls:
                        href = actual_urls[0]
                elif isinstance(href, str) and href.startswith("//"):
                    href = "https:" + href

                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if title and href:
                    results.append(
                        SearchResult(
                            title=title,
                            url=str(href),
                            snippet=snippet,
                            position=i + 1,
                        )
                    )

            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                duration_ms=duration,
            )

    except httpx.TimeoutException:
        return SearchResponse(
            query=query,
            error=f"Search timeout after {timeout}s",
            duration_ms=(time.monotonic() - start) * 1000,
        )
    except Exception as e:
        return SearchResponse(
            query=query,
            error=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


async def research_topic(
    topic: str,
    num_search_results: int = 6,
    max_sources_to_fetch: int = 4,
    max_chars_per_source: int = 15_000,
    timeout_per_fetch: float = 12.0,
) -> ResearchReport:
    """Deep research on a topic: search → fetch top results → synthesize.

    This is the high-level orchestrator that replaces multi-step
    Exa search + fetch workflows with a single call.

    Pipeline:
        1. Web search for the topic
        2. Fetch top N results in parallel
        3. Extract key points from each source
        4. Cross-reference and find patterns
        5. Generate synthesis with source comparison
        6. Identify related topics for further exploration

    Args:
        topic: The research topic or question
        num_search_results: How many search results to get
        max_sources_to_fetch: How many of the top results to fetch content from
        max_chars_per_source: Max characters per source
        timeout_per_fetch: Timeout per fetch in seconds

    Returns:
        ResearchReport with findings and synthesis
    """
    start = time.monotonic()

    search_result = await web_search(topic, num_results=num_search_results)

    if not search_result.success:
        return ResearchReport(
            topic=topic,
            error=f"Search failed: {search_result.error}",
            duration_ms=(time.monotonic() - start) * 1000,
        )

    urls_to_fetch = [r.url for r in search_result.results[:max_sources_to_fetch]]
    search_meta = {r.url: r for r in search_result.results}

    fetch_tasks = [
        web_fetch(url, max_chars=max_chars_per_source, timeout=timeout_per_fetch)
        for url in urls_to_fetch
    ]

    fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    findings: list[ResearchFinding] = []
    all_content_blocks: list[str] = []

    for result in fetched:
        if isinstance(result, Exception):
            continue
        if not isinstance(result, FetchResult) or not result.success:
            continue
        if not result.content or len(result.content.strip()) < 50:
            continue

        # Extract key points (sentences containing the topic or key terms)
        key_points = _extract_key_points(result.content, topic)

        meta = search_meta.get(result.url)
        relevance = meta.snippet if meta else ""

        finding = ResearchFinding(
            url=result.url,
            title=result.title or (meta.title if meta else ""),
            content=result.content,
            relevance=relevance,
            key_points=key_points[:10],
        )
        findings.append(finding)
        all_content_blocks.append(result.content)

    synthesis = _synthesize_findings(topic, findings)

    related = _extract_related_topics(topic, all_content_blocks)

    duration = (time.monotonic() - start) * 1000

    # Emit to Gan Ying if available
    _emit_research_event(topic, len(findings), duration)

    return ResearchReport(
        topic=topic,
        findings=findings,
        synthesis=synthesis,
        related_topics=related,
        sources_searched=len(search_result.results),
        sources_fetched=len(findings),
        duration_ms=duration,
    )


def _extract_key_points(content: str, topic: str, max_points: int = 10) -> list[str]:
    """Extract key sentences related to the topic from content."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", content)

    topic_words = set(topic.lower().split())
    scored: list[tuple[float, str]] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 30 or len(sentence) > 500:
            continue

        words = set(sentence.lower().split())
        overlap = len(topic_words & words)
        if overlap > 0:
            score = overlap / len(topic_words)
            scored.append((score, sentence))

    # Sort by relevance, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_points]]


def _synthesize_findings(topic: str, findings: list[ResearchFinding]) -> str:
    """Generate a synthesis from multiple research findings."""
    if not findings:
        return "No sources could be fetched for this topic."

    parts = [f"## Research Synthesis: {topic}\n"]
    parts.append(f"**{len(findings)} sources analyzed.**\n")

    # Source overview
    parts.append("### Sources\n")
    for i, f in enumerate(findings, 1):
        parts.append(f"{i}. [{f.title}]({f.url})")

    # Key points aggregation
    all_points = []
    for f in findings:
        all_points.extend(f.key_points)

    if all_points:
        parts.append("\n### Key Points Across Sources\n")
        seen = set()
        for point in all_points[:15]:
            # Deduplicate similar points
            key = point[:60].lower()
            if key not in seen:
                seen.add(key)
                parts.append(f"- {point}")

    # Cross-reference note
    if len(findings) >= 2:
        parts.append("\n### Cross-Reference Notes\n")
        parts.append(
            f"Information gathered from {len(findings)} independent sources. "
            "Points appearing across multiple sources have higher confidence."
        )

    return "\n".join(parts)


def _extract_related_topics(
    topic: str, content_blocks: list[str], max_topics: int = 10
) -> list[str]:
    """Extract related topics from content for further rabbit-hole exploration."""
    combined = " ".join(content_blocks)[:50_000]

    # Find capitalized multi-word phrases that aren't the topic itself
    pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    matches = re.findall(pattern, combined)

    topic_lower = topic.lower()
    counts: dict[str, int] = {}
    for match in matches:
        if match.lower() != topic_lower and len(match) > 5:
            counts[match] = counts.get(match, 0) + 1

    # Sort by frequency, return top N
    sorted_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in sorted_topics[:max_topics]]


def _emit_research_event(topic: str, num_findings: int, duration_ms: float) -> None:
    """Emit research completion to Gan Ying Bus."""
    try:
        from whitemagic.core.resonance.gan_ying import (
            EventType,
            ResonanceEvent,
            get_bus,
        )

        bus = get_bus()
        bus.emit(
            ResonanceEvent(
                source="browser.web_research",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "topic": topic,
                    "findings": num_findings,
                    "duration_ms": round(duration_ms, 1),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                confidence=0.8,
            )
        )
    except (ImportError, Exception):
        pass


class BrowserSessionManager:
    """Singleton manager for persistent browser sessions.

    Solves the session-per-call problem where each browser tool handler
    creates and destroys its own session. This manager keeps a session
    alive across multiple tool calls for chained interactions.
    """

    _instance: BrowserSessionManager | None = None
    _lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None

    def __init__(self) -> None:
        self._session: Any = None
        self._last_url: str = ""
        self._created_at: str = ""

    @classmethod
    def get(cls) -> BrowserSessionManager:
        """
        Perform the get operation.

        Args:
            cls: Parameter description.

        Returns:
            BrowserSessionManager
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_session(self) -> Any:
        """Get or create a persistent browser session."""
        from .actions import BrowserSession

        if self._session is None:
            self._session = BrowserSession()
            try:
                await self._session.connect()
                self._created_at = datetime.now(UTC).isoformat()
            except (ConnectionError, TimeoutError, OSError) as e:
                self._session = None
                raise RuntimeError(
                    f"Cannot connect to Chrome: {e}. "
                    "Start Chrome with: google-chrome --remote-debugging-port=9222"
                ) from e
        return self._session

    async def close(self) -> None:
        """Close the persistent session."""
        if self._session is not None:
            try:
                await self._session.disconnect()
            except (ConnectionError, TimeoutError, OSError):
                logger.debug("Swallowed exception", exc_info=True)
            self._session = None
            self._last_url = ""

    @property
    def is_connected(self) -> bool:
        """
        Check whether the connected condition holds.

        Returns:
            bool
        """
        return self._session is not None

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        return {
            "connected": self.is_connected,
            "last_url": self._last_url,
            "created_at": self._created_at,
        }


def _run_async(coro: Any) -> Any:
    """Run async coroutine from sync context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


def sync_web_fetch(
    url: str, max_chars: int = 30_000, timeout: float = 15.0
) -> FetchResult:
    """Synchronous wrapper for web_fetch."""
    result: FetchResult = _run_async(
        web_fetch(url, max_chars=max_chars, timeout=timeout)
    )
    return result


def sync_web_search(
    query: str, num_results: int = 8, timeout: float = 10.0, category: str | None = None
) -> SearchResponse:
    """Synchronous wrapper for web_search."""
    result: SearchResponse = _run_async(
        web_search(query, num_results=num_results, timeout=timeout, category=category)
    )
    return result


def sync_research_topic(topic: str, **kwargs: Any) -> ResearchReport:
    """Synchronous wrapper for research_topic."""
    result: ResearchReport = _run_async(research_topic(topic, **kwargs))
    return result


def sync_deep_fetch(
    url: str, max_chars: int = 200_000, timeout: float = 30.0
) -> DeepFetchResult:
    """Synchronous wrapper for deep_fetch."""
    result: DeepFetchResult = _run_async(
        deep_fetch(url, max_chars=max_chars, timeout=timeout)
    )
    return result


def sync_research_repo(
    repo: str,
    max_pages: int = 5,
    max_chars_per_page: int = 50_000,
    store_memories: bool = True,
) -> RepoResearchResult:
    """Synchronous wrapper for research_repo."""
    result: RepoResearchResult = _run_async(
        research_repo(
            repo,
            max_pages=max_pages,
            max_chars_per_page=max_chars_per_page,
            store_memories=store_memories,
        )
    )
    return result


def sync_research_url(
    url: str, max_chars: int = 200_000, timeout: float = 30.0, store_memory: bool = True
) -> URLResearchResult:
    """Synchronous wrapper for research_url."""
    result: URLResearchResult = _run_async(
        research_url(
            url, max_chars=max_chars, timeout=timeout, store_memory=store_memory
        )
    )
    return result


@dataclass
class DeepFetchResult:
    """Result from deep_fetch -- full page content with pagination metadata."""

    url: str
    title: str = ""
    content: str = ""
    content_length: int = 0
    status_code: int = 0
    duration_ms: float = 0.0
    pages_fetched: int = 0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def success(self) -> bool:
        return self.error is None and self.status_code in range(200, 400)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content_length": self.content_length,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 1),
            "pages_fetched": self.pages_fetched,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


def _detect_next_page(html: str, current_url: str) -> str | None:
    """Detect a 'next page' link from HTML content."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            rel = a_tag.get("rel", [])
            classes = a_tag.get("class", [])
            text = a_tag.get_text(strip=True).lower()
            if (
                "next" in rel
                or "next" in classes
                or text in ("next", "next page", "\u00bb", "\u2192", "more")
            ):
                href = a_tag["href"]
                if href and not href.startswith("#"):
                    from urllib.parse import urljoin

                    return urljoin(current_url, href)
        return None
    except Exception:
        return None


async def deep_fetch(
    url: str,
    max_chars: int = 200_000,
    timeout: float = 30.0,
    follow_redirects: bool = True,
) -> DeepFetchResult:
    """Fetch a URL with full-content retrieval -- no chunk skimming.

    Unlike web_fetch (which caps at 30K chars), deep_fetch retrieves the
    entire page content up to max_chars (default 200K). For paginated
    content, it follows next-page links when detectable.

    Args:
        url: The URL to fetch
        max_chars: Maximum total characters to return (default 200K)
        timeout: Request timeout in seconds
        follow_redirects: Follow HTTP redirects

    Returns:
        DeepFetchResult with full page content
    """
    if not HAS_HTTPX:
        return DeepFetchResult(url=url, error="httpx not installed: pip install httpx")

    start = time.monotonic()
    all_content: list[str] = []
    total_length = 0
    pages = 0
    current_url = url
    title = ""
    last_status = 0

    for _page in range(10):
        if total_length >= max_chars:
            break

        try:
            async with httpx.AsyncClient(
                headers=_DEFAULT_HEADERS,
                follow_redirects=follow_redirects,
                timeout=timeout,
            ) as client:
                response = await client.get(current_url)
                last_status = response.status_code
                pages += 1

                content_type = response.headers.get("content-type", "")

                if "text/html" in content_type or "application/xhtml" in content_type:
                    html = response.text
                    if not title:
                        title = _extract_title(html)
                    page_content = _html_to_text(
                        html, max_chars=max_chars - total_length
                    )
                elif "text/plain" in content_type or "application/json" in content_type:
                    page_content = response.text[: max_chars - total_length]
                    if not title:
                        title = urlparse(current_url).path.split("/")[-1] or current_url
                else:
                    page_content = f"[Binary content: {content_type}, {len(response.content)} bytes]"

                all_content.append(page_content)
                total_length += len(page_content)

                next_url = (
                    _detect_next_page(response.text, current_url) if HAS_BS4 else None
                )
                if not next_url or next_url == current_url:
                    break
                current_url = next_url

        except httpx.TimeoutException:
            if pages > 0:
                break
            return DeepFetchResult(
                url=url,
                error=f"Timeout after {timeout}s",
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            if pages > 0:
                break
            return DeepFetchResult(
                url=url,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    content = (
        "\n\n---\n\n".join(all_content)
        if len(all_content) > 1
        else (all_content[0] if all_content else "")
    )

    return DeepFetchResult(
        url=url,
        title=title,
        content=content,
        content_length=len(content),
        status_code=last_status,
        duration_ms=(time.monotonic() - start) * 1000,
        pages_fetched=pages,
    )


@dataclass
class RepoResearchResult:
    """Result from research_repo -- repo docs fetched and stored as memories."""

    repo: str
    pages_fetched: int = 0
    total_chars: int = 0
    memory_ids: list[str] = field(default_factory=list)
    wiki_url: str = ""
    readme_url: str = ""
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def success(self) -> bool:
        return self.error is None and self.pages_fetched > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pages_fetched": self.pages_fetched,
            "total_chars": self.total_chars,
            "memory_ids": self.memory_ids,
            "wiki_url": self.wiki_url,
            "readme_url": self.readme_url,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


_GITHUB_DOC_PATHS = [
    "README.md",
    "README.rst",
    "docs/README.md",
    "docs/index.md",
    "docs/getting-started.md",
    "docs/architecture.md",
    "docs/configuration.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "AGENTS.md",
    ".github/README.md",
]


async def research_repo(
    repo: str,
    max_pages: int = 5,
    max_chars_per_page: int = 50_000,
    store_memories: bool = True,
) -> RepoResearchResult:
    """Research a GitHub repository by fetching its documentation.

    Fetches README, docs, wiki pages from a GitHub repo, then optionally
    stores them as WhiteMagic memories for later Q&A via hybrid_recall.
    This replaces DeepWiki's instant repo Q&A with a self-contained approach.

    Args:
        repo: GitHub repo in owner/repo format (e.g. 'facebook/react')
        max_pages: Maximum number of pages to fetch (default 5)
        max_chars_per_page: Max chars per page (default 50K)
        store_memories: Store fetched content as memories (default True)

    Returns:
        RepoResearchResult with fetched pages and memory IDs
    """
    import re as _re

    if not _re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return RepoResearchResult(
            repo=repo,
            error="Invalid repo format. Use owner/repo (e.g. 'facebook/react')",
        )

    pages_fetched = 0
    total_chars = 0
    memory_ids: list[str] = []
    wiki_url = f"https://github.com/{repo}/wiki"
    readme_url = f"https://raw.githubusercontent.com/{repo}/HEAD/README.md"

    urls_to_try: list[str] = []
    for path in _GITHUB_DOC_PATHS[: max_pages + 1]:
        urls_to_try.append(f"https://raw.githubusercontent.com/{repo}/HEAD/{path}")
    urls_to_try.append(f"https://raw.githubusercontent.com/{repo}/HEAD/Home.md")

    fetch_tasks = [
        web_fetch(u, max_chars=max_chars_per_page, timeout=15.0)
        for u in urls_to_try[: max_pages + 2]
    ]
    fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    contents_to_store: list[dict[str, str]] = []
    for i, result in enumerate(fetched):
        if isinstance(result, Exception) or not hasattr(result, "success"):
            continue
        if not result.success or not result.content or len(result.content.strip()) < 50:
            continue
        pages_fetched += 1
        total_chars += result.content_length
        source_url = urls_to_try[i] if i < len(urls_to_try) else ""
        contents_to_store.append(
            {
                "url": source_url,
                "title": result.title or f"{repo} doc page {pages_fetched}",
                "content": result.content,
            }
        )

    if store_memories and contents_to_store:
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory()
            for item in contents_to_store:
                try:
                    mem_id = mem.store(
                        content=item["content"],
                        metadata={
                            "type": "repo_research",
                            "repo": repo,
                            "source_url": item["url"],
                            "title": item["title"],
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                        tags=["repo_research", repo, "documentation"],
                    )
                    if mem_id:
                        memory_ids.append(str(mem_id))
                except Exception as e:
                    logger.debug(
                        "Failed to store repo research memory: %s", e, exc_info=True
                    )
        except Exception as e:
            logger.debug(
                "Memory system unavailable for repo research: %s", e, exc_info=True
            )

    return RepoResearchResult(
        repo=repo,
        pages_fetched=pages_fetched,
        total_chars=total_chars,
        memory_ids=memory_ids,
        wiki_url=wiki_url,
        readme_url=readme_url,
    )


@dataclass
class URLResearchResult:
    """Result from research_url -- URL content fetched and stored as memory."""

    url: str
    title: str = ""
    content_length: int = 0
    memory_id: str | None = None
    pages_fetched: int = 0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def success(self) -> bool:
        return self.error is None and self.content_length > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content_length": self.content_length,
            "memory_id": self.memory_id,
            "pages_fetched": self.pages_fetched,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


async def research_url(
    url: str,
    max_chars: int = 200_000,
    timeout: float = 30.0,
    store_memory: bool = True,
) -> URLResearchResult:
    """Fetch full content from any URL and store as a WhiteMagic memory.

    Generalizes the research_repo approach to any URL on the open net.
    Uses deep_fetch for full-content retrieval (no chunk skimming), then
    stores the result as a memory for later Q&A via hybrid_recall.

    Args:
        url: The URL to research
        max_chars: Maximum characters to retrieve (default 200K)
        timeout: Request timeout in seconds
        store_memory: Store content as a memory (default True)

    Returns:
        URLResearchResult with fetched content and memory ID
    """
    result = await deep_fetch(url, max_chars=max_chars, timeout=timeout)

    if not result.success:
        return URLResearchResult(
            url=url,
            error=result.error or "Fetch failed",
            content_length=0,
            pages_fetched=0,
        )

    memory_id = None
    if store_memory and result.content:
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory()
            mem_id = mem.store(
                content=result.content,
                metadata={
                    "type": "url_research",
                    "source_url": url,
                    "title": result.title,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                tags=["url_research", "web_content"],
            )
            if mem_id:
                memory_id = str(mem_id)
        except Exception as e:
            logger.debug(
                "Memory system unavailable for URL research: %s", e, exc_info=True
            )

    return URLResearchResult(
        url=url,
        title=result.title,
        content_length=result.content_length,
        memory_id=memory_id,
        pages_fetched=result.pages_fetched,
    )


@dataclass
class BatchSearchResult:
    """Result from web_search_batch -- multiple queries searched in parallel."""

    queries: list[str]
    total_results: int = 0
    results_by_query: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "queries": self.queries,
            "total_results": self.total_results,
            "results_by_query": self.results_by_query,
            "duration_ms": round(self.duration_ms, 1),
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


async def web_search_batch(
    queries: list[str],
    num_results_per_query: int = 5,
    timeout: float = 10.0,
    category: str | None = None,
) -> BatchSearchResult:
    """Search multiple queries in parallel via asyncio.gather.

    This is the batch equivalent of web_search -- instead of searching
    one query at a time, it runs all queries simultaneously, dramatically
    speeding up multi-faceted research (e.g. rabbit hole exploration).

    Args:
        queries: List of search queries to run in parallel
        num_results_per_query: Results per query (default 5, lower for batch)
        timeout: Timeout per search in seconds
        category: Optional category filter applied to all queries

    Returns:
        BatchSearchResult with results grouped by query
    """
    start = time.monotonic()

    tasks = [
        web_search(
            q, num_results=num_results_per_query, timeout=timeout, category=category
        )
        for q in queries
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    batch = BatchSearchResult(queries=queries)
    for i, result in enumerate(results):
        query = queries[i]
        if isinstance(result, Exception):
            batch.errors.append(f"{query}: {result}")
            batch.results_by_query[query] = []
        else:
            batch.results_by_query[query] = result.to_dict().get("results", [])
            batch.total_results += len(batch.results_by_query[query])

    batch.duration_ms = (time.monotonic() - start) * 1000
    return batch


def sync_web_search_batch(
    queries: list[str],
    num_results_per_query: int = 5,
    timeout: float = 10.0,
    category: str | None = None,
) -> BatchSearchResult:
    """Synchronous wrapper for web_search_batch."""
    result: BatchSearchResult = _run_async(
        web_search_batch(
            queries,
            num_results_per_query=num_results_per_query,
            timeout=timeout,
            category=category,
        )
    )
    return result


def _get_cache_dir() -> Path:
    """Get the web content cache directory under WM_STATE_ROOT."""
    from whitemagic.config.paths import get_state_root

    cache_dir = get_state_root() / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_key(url: str) -> str:
    """Generate a safe filename from a URL."""
    import hashlib

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_")[:30]
    return f"{domain}_{url_hash}"


def cache_web_content(
    url: str, content: str, title: str = "", metadata: dict[str, Any] | None = None
) -> Path:
    """Save web content to the cache directory for later re-reading.

    Stores content as markdown files with frontmatter metadata.
    Images are noted but not downloaded (binary content tracked separately).

    Args:
        url: Source URL
        content: Text content to cache
        title: Page title
        metadata: Additional metadata dict

    Returns:
        Path to the cached file
    """
    cache_dir = _get_cache_dir()
    key = _cache_key(url)
    filepath = cache_dir / f"{key}.md"

    frontmatter_lines = [
        "---",
        f"url: {url}",
        f"title: {title}",
        f"cached_at: {datetime.now(UTC).isoformat()}",
    ]
    if metadata:
        for k, v in metadata.items():
            frontmatter_lines.append(f"{k}: {v}")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")

    full_content = "\n".join(frontmatter_lines) + content
    filepath.write_text(full_content, encoding="utf-8")
    logger.debug("Cached web content: %s -> %s", url, filepath)
    return filepath


def read_cached_content(url: str) -> str | None:
    """Read previously cached content for a URL.

    Returns None if not cached.
    """
    cache_dir = _get_cache_dir()
    key = _cache_key(url)
    filepath = cache_dir / f"{key}.md"
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return None


def list_cached_content() -> list[dict[str, Any]]:
    """List all cached web content files with metadata."""
    cache_dir = _get_cache_dir()
    results = []
    for f in cache_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            # Extract frontmatter
            if content.startswith("---"):
                end = content.index("---", 3)
                frontmatter = content[3:end].strip()
                meta = {}
                for line in frontmatter.split("\n"):
                    if ": " in line:
                        k, v = line.split(": ", 1)
                        meta[k.strip()] = v.strip()
                results.append(
                    {
                        "file": str(f),
                        "filename": f.name,
                        "size_bytes": f.stat().st_size,
                        **meta,
                    }
                )
        except Exception:
            results.append(
                {"file": str(f), "filename": f.name, "error": "parse_failed"}
            )
    return results


def clear_cached_content(older_than_hours: int | None = None) -> int:
    """Clear cached web content. Returns count of files removed.

    Args:
        older_than_hours: Only remove files older than this many hours.
                         If None, removes all.
    """
    import time as _time

    cache_dir = _get_cache_dir()
    removed = 0
    cutoff = _time.time() - (older_than_hours * 3600) if older_than_hours else None

    for f in cache_dir.glob("*.md"):
        if cutoff and f.stat().st_mtime > cutoff:
            continue
        f.unlink()
        removed += 1
    return removed


def extract_image_urls(html: str, base_url: str = "") -> list[dict[str, str]]:
    """Extract image URLs from HTML content.

    Returns list of dicts with url, alt, and src attributes.
    """
    images = []
    try:
        from urllib.parse import urljoin

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src or src.startswith("data:"):
                continue
            alt = img.get("alt", "")
            if base_url:
                src = urljoin(base_url, src)
            images.append({"url": src, "alt": alt})
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)
    return images


async def download_image(
    url: str, dest_dir: Path, timeout: float = 10.0
) -> Path | None:
    """Download an image to the specified directory.

    Returns the path to the downloaded file, or None on failure.
    """
    if not HAS_HTTPX:
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                return None

            # Generate filename from URL
            import hashlib

            url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
            ext = content_type.split("/")[-1].split(";")[0]
            if ext == "jpeg":
                ext = "jpg"
            filename = f"img_{url_hash}.{ext}"
            filepath = dest_dir / filename
            filepath.write_bytes(response.content)
            return filepath
    except Exception:
        return None


async def download_page_images(
    html: str,
    base_url: str,
    dest_dir: Path,
    max_images: int = 10,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Extract and download all images from a page.

    Returns list of dicts with url, alt, local_path, and success status.
    """
    images = extract_image_urls(html, base_url)
    dest_dir.mkdir(parents=True, exist_ok=True)

    results = []
    tasks = []
    for img in images[:max_images]:
        tasks.append(download_image(img["url"], dest_dir, timeout=timeout))

    downloaded = await asyncio.gather(*tasks, return_exceptions=True)

    for i, img in enumerate(images[:max_images]):
        result = {"url": img["url"], "alt": img["alt"], "success": False}
        if (
            i < len(downloaded)
            and not isinstance(downloaded[i], Exception)
            and downloaded[i]
        ):
            result["local_path"] = str(downloaded[i])
            result["success"] = True
        elif isinstance(downloaded[i], Exception):
            result["error"] = str(downloaded[i])
        results.append(result)

    return results


async def cached_deep_fetch(
    url: str,
    max_chars: int = 200_000,
    timeout: float = 30.0,
    force_refresh: bool = False,
    download_images: bool = False,
) -> DeepFetchResult:
    """Deep fetch with caching — returns cached content if available.

    Args:
        url: URL to fetch
        max_chars: Max content size
        timeout: Request timeout
        force_refresh: Skip cache and re-fetch
        download_images: Also download images from the page

    Returns:
        DeepFetchResult (from cache or fresh fetch)
    """
    if not force_refresh:
        cached = read_cached_content(url)
        if cached:
            content = cached
            title = ""
            if cached.startswith("---"):
                end = cached.index("---", 3)
                frontmatter = cached[3:end].strip()
                for line in frontmatter.split("\n"):
                    if line.startswith("title: "):
                        title = line[7:]
                content = cached[end + 3 :].strip()

            return DeepFetchResult(
                url=url,
                title=title,
                content=content,
                content_length=len(content),
                status_code=200,
                duration_ms=0.0,
                pages_fetched=0,
            )

    # Fresh fetch
    result = await deep_fetch(url, max_chars=max_chars, timeout=timeout)

    if result.success and result.content:
        # Cache the content
        cache_web_content(
            url,
            result.content,
            result.title,
            metadata={
                "pages_fetched": result.pages_fetched,
                "status_code": result.status_code,
            },
        )

        # Download images if requested
        if download_images and HAS_HTTPX:
            try:
                cache_dir = _get_cache_dir()
                img_dir = cache_dir / "images" / _cache_key(url)
                # Re-fetch HTML for image extraction (deep_fetch converts to text)
                async with httpx.AsyncClient(
                    timeout=timeout, follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        imgs = await download_page_images(
                            response.text,
                            url,
                            img_dir,
                            max_images=10,
                            timeout=timeout,
                        )
                        result.metadata = {
                            "images_downloaded": sum(1 for i in imgs if i["success"])
                        }
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

    return result


_DEPTH_CATEGORIES = {
    0: None,  # Level 0: General search
    1: "academic",  # Level 1: Academic/authoritative sources
    2: "code",  # Level 2: Code/implementation sources
    3: "docs",  # Level 3: Documentation sources
    4: "news",  # Level 4: News/recent developments
}


def get_depth_category(depth: int) -> str | None:
    """Get the recommended search category for a given rabbit hole depth."""
    return _DEPTH_CATEGORIES.get(depth, "docs")


class AdaptiveBatchSizer:
    """Dynamically adjusts batch size based on observed response times.

    Starts with a default batch size and adapts:
    - Fast responses (< 2s) -> increase batch size
    - Slow responses (> 5s) -> decrease batch size
    - Errors -> decrease batch size more aggressively
    """

    def __init__(
        self, initial_size: int = 8, min_size: int = 2, max_size: int = 20
    ) -> None:
        self.current_size = initial_size
        self.min_size = min_size
        self.max_size = max_size
        self._response_times: list[float] = []
        self._error_count = 0

    def record_response(self, duration_ms: float, error: bool = False) -> None:
        """Record a response time and adjust batch size."""
        if error:
            self._error_count += 1
            self.current_size = max(self.min_size, self.current_size - 2)
            return

        self._response_times.append(duration_ms / 1000.0)
        if len(self._response_times) > 10:
            self._response_times = self._response_times[-10:]

        if len(self._response_times) >= 3:
            avg_time = sum(self._response_times) / len(self._response_times)
            if avg_time < 2.0:
                self.current_size = min(self.max_size, self.current_size + 1)
            elif avg_time > 5.0:
                self.current_size = max(self.min_size, self.current_size - 1)

    def get_batch_size(self) -> int:
        """Get the current recommended batch size."""
        return self.current_size
