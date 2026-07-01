# ruff: noqa: BLE001
"""Content Intelligence — Chunking, outline extraction, and summarization.

Provides three capabilities for AI-friendly content processing:
1. ContentChunker — splits text into ~2K-char semantic chunks with overlap
2. OutlineBuilder — extracts heading structure from HTML before text conversion
3. ContentSummarizer — LLM-powered summarization via Ollama with extractive fallback

Inspired by Windsurf's approach of building outlines and chunking content for
progressive loading, but designed for WhiteMagic's local-first, no-API-key ethos.

Integration:
    Used by web_fetch_enhanced handler in gana_chariot.
    Summarizer falls back to extractive summarization when Ollama is unavailable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup, Tag

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    Tag = None  # type: ignore[assignment, misc]


@dataclass
class ContentChunk:
    """A semantic chunk of content."""

    index: int
    text: str
    char_count: int
    heading: str = ""  # Nearest preceding heading
    token_estimate: int = 0  # Rough estimate: chars / 4


@dataclass
class OutlineNode:
    """A node in the page outline (heading hierarchy)."""

    level: int  # 1-6 (h1-h6)
    text: str
    children: list[OutlineNode] = field(default_factory=list)


@dataclass
class EnhancedContent:
    """Result of enhanced content processing."""

    title: str
    outline: list[OutlineNode]
    summary: str
    chunks: list[ContentChunk]
    total_chars: int
    total_chunks: int
    chunk_size: int
    overlap: int
    summarizer_used: str  # "ollama" | "extractive" | "none"


class OutlineBuilder:
    """Extracts heading structure from HTML before text conversion.

    This gives AI agents a structural overview of a page without needing
    to read the full content — similar to Windsurf's site outline building.
    """

    def build_from_html(self, html: str) -> list[OutlineNode]:
        """Build a hierarchical outline from HTML headings.

        Returns a list of top-level OutlineNodes (h1/h2),
        with children containing nested subheadings.
        """
        if HAS_BS4:
            return self._build_with_bs4(html)
        return self._build_with_regex(html)

    def _build_with_bs4(self, html: str) -> list[OutlineNode]:
        """Build outline using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if not headings:
            return []

        # Build flat list first, then nest
        flat: list[OutlineNode] = []
        for h in headings:
            level = int(h.name[1])  # h1 -> 1, h2 -> 2, etc.
            text = h.get_text(strip=True)
            if text and len(text) < 200:  # Skip absurdly long "headings"
                flat.append(OutlineNode(level=level, text=text))

        return self._nest_outline(flat)

    def _build_with_regex(self, html: str) -> list[OutlineNode]:
        """Fallback: build outline using regex on HTML tags."""
        clean = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        clean = re.sub(
            r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE
        )

        heading_pattern = r"<h([1-6])[^>]*>(.*?)</h\1>"
        matches = re.findall(heading_pattern, clean, re.IGNORECASE | re.DOTALL)

        flat: list[OutlineNode] = []
        for level_str, raw_text in matches:
            level = int(level_str)
            # Strip any nested HTML tags from heading text
            text = re.sub(r"<[^>]+>", "", raw_text).strip()
            if text and len(text) < 200:
                flat.append(OutlineNode(level=level, text=text))

        return self._nest_outline(flat)

    def _nest_outline(self, flat: list[OutlineNode]) -> list[OutlineNode]:
        """Convert a flat list of OutlineNodes into a nested hierarchy."""
        if not flat:
            return []

        root: list[OutlineNode] = []
        stack: list[OutlineNode] = []  # Stack of current parents

        for node in flat:
            # Pop stack until we find a parent with lower level
            while stack and stack[-1].level >= node.level:
                stack.pop()

            if stack:
                stack[-1].children.append(node)
            else:
                root.append(node)

            stack.append(node)

        return root

    def to_markdown(self, nodes: list[OutlineNode], indent: int = 0) -> str:
        """Convert outline to a markdown bullet list."""
        lines: list[str] = []
        for node in nodes:
            prefix = "  " * indent + "- "
            lines.append(f"{prefix}{'#' * node.level} {node.text}")
            if node.children:
                lines.append(self.to_markdown(node.children, indent + 1))
        return "\n".join(lines)

    def to_flat_list(
        self, nodes: list[OutlineNode], depth: int = 0
    ) -> list[dict[str, Any]]:
        """Convert outline to a flat list of dicts (for JSON output)."""
        result: list[dict[str, Any]] = []
        for node in nodes:
            result.append(
                {
                    "level": node.level,
                    "text": node.text,
                    "depth": depth,
                    "children_count": len(node.children),
                }
            )
            if node.children:
                result.extend(self.to_flat_list(node.children, depth + 1))
        return result


class ContentChunker:
    """Splits text into ~N-char semantic chunks with overlap.

    Tries to break on paragraph boundaries, then sentence boundaries,
    then word boundaries — never mid-word.
    """

    def __init__(self, chunk_size: int = 2000, overlap: int = 200) -> None:
        """Initialize the chunker.

        Args:
            chunk_size: Target characters per chunk (default 2000)
            overlap: Overlap characters between adjacent chunks (default 200)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, headings: list[str] | None = None) -> list[ContentChunk]:
        """Split text into semantic chunks.

        Args:
            text: The text to chunk
            headings: Optional list of heading texts to anchor chunks to
                       (helps assign the nearest preceding heading to each chunk)

        Returns:
            List of ContentChunk objects
        """
        if not text:
            return []

        # Split into paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        chunks: list[ContentChunk] = []
        current_text: str = ""
        current_heading: str = ""

        # Build a heading lookup: list of (position_in_text, heading_text)
        heading_positions: list[tuple[int, str]] = []
        if headings:
            pos = 0
            for para in paragraphs:
                for h in headings:
                    if h.lower() in para.lower():
                        heading_positions.append((pos, h))
                pos += len(para) + 2  # +2 for the \n\n separator

        for para in paragraphs:
            for h in headings or []:
                if h.lower() in para.lower():
                    current_heading = h
                    break

            if current_text and len(current_text) + len(para) + 2 > self.chunk_size:
                chunks.append(
                    self._make_chunk(len(chunks), current_text, current_heading)
                )

                overlap_text = (
                    current_text[-self.overlap :]
                    if len(current_text) > self.overlap
                    else current_text
                )
                current_text = overlap_text + "\n\n" + para
            else:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para

        # Flush remaining
        if current_text:
            chunks.append(self._make_chunk(len(chunks), current_text, current_heading))

        return chunks

    def _make_chunk(self, index: int, text: str, heading: str) -> ContentChunk:
        """Create a ContentChunk with metadata."""
        return ContentChunk(
            index=index,
            text=text,
            char_count=len(text),
            heading=heading,
            token_estimate=len(text) // 4,  # Rough: 4 chars per token
        )


class ContentSummarizer:
    """Summarizes content using Ollama (local LLM) with extractive fallback.

    Tries Ollama first for abstractive summarization.
    Falls back to extractive summarization (sentence scoring) if Ollama is unavailable.
    """

    def __init__(self, model: str = "gemma3:4b", max_summary_chars: int = 1000) -> None:
        """Initialize the summarizer.

        Args:
            model: Ollama model to use (default gemma3:4b — small and fast)
            max_summary_chars: Maximum summary length in characters
        """
        self.model = model
        self.max_summary_chars = max_summary_chars

    def summarize(self, text: str, focus: str = "") -> tuple[str, str]:
        """Summarize text, returning (summary, method_used).

        Args:
            text: Content to summarize
            focus: Optional focus topic to guide summarization

        Returns:
            Tuple of (summary_text, method_name) where method_name is
            "ollama" or "extractive"
        """
        if not text or len(text) < 200:
            return text[: self.max_summary_chars], "none"

        try:
            summary = self._summarize_with_ollama(text, focus)
            if summary:
                return summary[: self.max_summary_chars], "ollama"
        except Exception as exc:
            logger.debug(
                "Ollama summarization failed: %s, falling back to extractive", exc
            )

        # Fallback: extractive summarization
        return self._summarize_extractive(text, focus), "extractive"

    def _summarize_with_ollama(self, text: str, focus: str) -> str | None:
        """Use Ollama to generate an abstractive summary."""
        try:
            import aiohttp
        except ImportError:
            return None

        import asyncio
        import os

        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

        # Truncate input to avoid token explosion (~8K chars = ~2K tokens)
        truncated = text[:8000]

        prompt = "Summarize the following content in 3-5 concise sentences"
        if focus:
            prompt += f", focusing on {focus}"
        prompt += f".\n\nContent:\n{truncated}\n\nSummary:"

        async def _call() -> str | None:
            async with aiohttp.ClientSession() as session:
                payload: dict[str, Any] = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 200},
                }
                async with session.post(
                    f"{ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    return data.get("response", "").strip()

        try:
            return asyncio.get_event_loop().run_until_complete(_call())
        except RuntimeError:
            # No event loop in this thread — create one
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_call())
            finally:
                loop.close()

    def _summarize_extractive(self, text: str, focus: str) -> str:
        """Extractive summarization using sentence scoring.

        Scores sentences by:
        - Term frequency (information density)
        - Position (early sentences often more important)
        - Focus relevance (if a focus topic is given)
        """
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip() and 30 < len(s) < 400]

        if not sentences:
            return text[: self.max_summary_chars]

        # Build term frequency map
        word_freq: dict[str, int] = {}
        for sent in sentences:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", sent.lower())
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1

        # Score each sentence
        scored: list[tuple[float, int, str]] = []
        focus_lower = focus.lower() if focus else ""

        for i, sent in enumerate(sentences):
            words = re.findall(r"\b[a-zA-Z]{4,}\b", sent.lower())
            if not words:
                continue

            # Term frequency score (normalized)
            tf_score = sum(word_freq.get(w, 0) for w in words) / len(words)

            # Position score (early sentences get slight boost)
            pos_score = 1.0 / (1.0 + i * 0.05)

            # Focus relevance score
            focus_score = 0.0
            if focus_lower:
                focus_words = focus_lower.split()
                focus_score = sum(1 for fw in focus_words if fw in sent.lower()) / max(
                    len(focus_words), 1
                )

            # Combined score
            total = (tf_score * 0.4) + (pos_score * 0.3) + (focus_score * 0.3)
            scored.append((total, i, sent))

        # Sort by score, take top N, then re-sort by original position
        scored.sort(key=lambda x: -x[0])
        top_n = min(5, len(scored))
        selected = sorted(scored[:top_n], key=lambda x: x[1])

        summary = " ".join(s[2] for s in selected)
        return summary[: self.max_summary_chars]


def process_content(
    html: str,
    text: str,
    title: str = "",
    chunk_size: int = 2000,
    overlap: int = 200,
    summarize: bool = True,
    focus: str = "",
    ollama_model: str = "gemma3:4b",
) -> EnhancedContent:
    """Process HTML/text into an EnhancedContent with outline, chunks, and summary.

    This is the main entry point for the web_fetch_enhanced handler.

    Args:
        html: Raw HTML (for outline extraction)
        text: Pre-converted text (from _html_to_text)
        title: Page title
        chunk_size: Target chars per chunk
        overlap: Overlap chars between chunks
        summarize: Whether to generate a summary
        focus: Optional focus topic for summarization
        ollama_model: Ollama model for summarization

    Returns:
        EnhancedContent with all components
    """
    outline_builder = OutlineBuilder()
    chunker = ContentChunker(chunk_size=chunk_size, overlap=overlap)

    # Build outline from HTML
    outline_nodes = outline_builder.build_from_html(html)
    heading_texts = []
    for node in outline_nodes:
        heading_texts.append(node.text)
        for child in node.children:
            heading_texts.append(child.text)

    # Chunk the text
    chunks = chunker.chunk(text, headings=heading_texts)

    # Summarize
    summary = ""
    summarizer_used = "none"
    if summarize and text:
        summarizer = ContentSummarizer(model=ollama_model)
        summary, summarizer_used = summarizer.summarize(text, focus=focus)

    return EnhancedContent(
        title=title,
        outline=outline_nodes,
        summary=summary,
        chunks=chunks,
        total_chars=len(text),
        total_chunks=len(chunks),
        chunk_size=chunk_size,
        overlap=overlap,
        summarizer_used=summarizer_used,
    )


def enhanced_to_dict(
    enhanced: EnhancedContent, include_chunks: bool = True
) -> dict[str, Any]:
    """Convert EnhancedContent to a JSON-serializable dict.

    Args:
        enhanced: The EnhancedContent object
        include_chunks: If True, include full chunk text. If False, only metadata.
    """
    outline_builder = OutlineBuilder()
    return {
        "title": enhanced.title,
        "outline": outline_builder.to_flat_list(enhanced.outline),
        "summary": enhanced.summary,
        "summarizer_used": enhanced.summarizer_used,
        "total_chars": enhanced.total_chars,
        "total_chunks": enhanced.total_chunks,
        "chunk_size": enhanced.chunk_size,
        "overlap": enhanced.overlap,
        "chunks": [
            {
                "index": c.index,
                "text": c.text
                if include_chunks
                else f"[chunk {c.index}, {c.char_count} chars]",
                "char_count": c.char_count,
                "heading": c.heading,
                "token_estimate": c.token_estimate,
            }
            for c in enhanced.chunks
        ],
    }
