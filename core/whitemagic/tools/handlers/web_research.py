"""Web research tool handlers — web_fetch, web_search, research_topic."""

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar
from whitemagic.utils.async_bridge import run_async as _run_async

T = TypeVar("T")


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying

    _emit_gan_ying(event_type, data)




def handle_web_fetch(**kwargs: Any) -> dict[str, Any]:
    """Fetch a URL and return clean text content (no browser needed)."""
    url = kwargs.get("url", "")
    if not url:
        raise ValueError("url is required")

    max_chars = int(kwargs.get("max_chars", 30_000))
    timeout = float(kwargs.get("timeout", 15.0))

    from whitemagic.gardens.browser.web_research import FetchResult, web_fetch

    async def _fetch() -> FetchResult:
        return await web_fetch(url, max_chars=max_chars, timeout=timeout)

    fetch_result = _run_async(_fetch())

    # Build response with full content (not truncated like to_dict())
    result = {
        "url": fetch_result.url,
        "title": fetch_result.title,
        "content": fetch_result.content,
        "content_length": fetch_result.content_length,
        "status_code": fetch_result.status_code,
        "duration_ms": round(fetch_result.duration_ms, 1),
        "success": fetch_result.success,
        "error": fetch_result.error,
    }

    _emit(
        "WEB_FETCH",
        {
            "url": url,
            "success": fetch_result.success,
            "length": fetch_result.content_length,
        },
    )
    return {"status": "success", **result}


def handle_web_search(**kwargs: Any) -> dict[str, Any]:
    """Search the web using DuckDuckGo (no API key needed)."""
    query = kwargs.get("query", "")
    if not query:
        raise ValueError("query is required")

    num_results = int(kwargs.get("num_results", 8))
    timeout = float(kwargs.get("timeout", 10.0))

    from whitemagic.gardens.browser.web_research import web_search

    async def _search() -> dict[str, Any]:
        result = await web_search(query, num_results=num_results, timeout=timeout)
        return result.to_dict()

    result = _run_async(_search())
    _emit("WEB_SEARCH", {"query": query, "results": result.get("total_results", 0)})
    return {"status": "success", **result}


def handle_web_search_and_read(**kwargs: Any) -> dict[str, Any]:
    """Search the web AND fetch content from top results in one call.

    Combines web_search + web_fetch for the most common research pattern.
    Returns search results with full page content for top hits.
    """
    query = kwargs.get("query", "")
    if not query:
        raise ValueError("query is required")

    num_results = int(kwargs.get("num_results", 5))
    max_fetch = int(kwargs.get("max_fetch", 3))
    max_chars_per_page = int(kwargs.get("max_chars_per_page", 15_000))

    from whitemagic.gardens.browser.web_research import web_fetch, web_search

    async def _search_and_read() -> dict[str, Any]:
        search_result = await web_search(query, num_results=num_results)
        if not search_result.success:
            return {"error": search_result.error, "results": []}

        urls = [r.url for r in search_result.results[:max_fetch]]
        fetch_tasks = [web_fetch(u, max_chars=max_chars_per_page) for u in urls]
        fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        enriched = []
        for sr in search_result.results:
            entry: dict[str, Any] = sr.to_dict()
            entry["content"] = None
            enriched.append(entry)

        for i, fetch_result in enumerate(fetched):
            if isinstance(fetch_result, BaseException) or not hasattr(
                fetch_result, "success"
            ):
                continue
            if fetch_result.success and i < len(enriched):
                enriched[i]["content"] = fetch_result.content  # type: ignore[union-attr]
                enriched[i]["content_length"] = fetch_result.content_length  # type: ignore[union-attr]
                enriched[i]["title"] = fetch_result.title or enriched[i].get(
                    "title", ""
                )  # type: ignore[union-attr]

        return {
            "query": query,
            "results": enriched,
            "total_results": len(enriched),
            "fetched_count": sum(1 for e in enriched if e.get("content")),
        }

    result = _run_async(_search_and_read())
    _emit(
        "WEB_SEARCH_AND_READ",
        {"query": query, "fetched": result.get("fetched_count", 0)},
    )
    return {"status": "success", **result}


def handle_research_topic(**kwargs: Any) -> dict[str, Any]:
    """Deep research on a topic: search, fetch, synthesize.

    Single-call replacement for multi-step Exa workflows.
    Pipeline: search → fetch top results → extract key points → synthesize.
    """
    topic = kwargs.get("topic", "")
    if not topic:
        raise ValueError("topic is required")

    num_search_results = int(kwargs.get("num_search_results", 6))
    max_sources = int(kwargs.get("max_sources", 4))
    max_chars_per_source = int(kwargs.get("max_chars_per_source", 15_000))

    from whitemagic.gardens.browser.web_research import research_topic

    async def _research() -> dict[str, Any]:
        result = await research_topic(
            topic,
            num_search_results=num_search_results,
            max_sources_to_fetch=max_sources,
            max_chars_per_source=max_chars_per_source,
        )
        # Include full content in findings (not truncated)
        data = result.to_dict()
        data["findings"] = [
            {
                **f.to_dict(),
                "content": f.content,
                "content_length": len(f.content),
            }
            for f in result.findings
        ]
        return data

    result = _run_async(_research())
    _emit(
        "RESEARCH_TOPIC",
        {
            "topic": topic,
            "sources": result.get("sources_fetched", 0),
            "duration_ms": result.get("duration_ms"),
        },
    )
    return {"status": "success", **result}


def handle_web_search_category(**kwargs: Any) -> dict[str, Any]:
    """Search the web with category filters (people, company, academic, code, docs, news)."""
    query = kwargs.get("query", "")
    if not query:
        raise ValueError("query is required")

    category = kwargs.get("category", "general")
    num_results = int(kwargs.get("num_results", 8))
    timeout = float(kwargs.get("timeout", 10.0))

    from whitemagic.gardens.browser.web_research import web_search

    async def _search() -> dict[str, Any]:
        result = await web_search(
            query, num_results=num_results, timeout=timeout, category=category
        )
        return result.to_dict()

    result = _run_async(_search())
    _emit(
        "WEB_SEARCH",
        {
            "query": query,
            "category": category,
            "results": result.get("total_results", 0),
        },
    )
    return {"status": "success", "category": category, **result}


def handle_deep_fetch(**kwargs: Any) -> dict[str, Any]:
    """Fetch a URL with full-content retrieval (up to 200K chars, no chunk skimming)."""
    url = kwargs.get("url", "")
    if not url:
        raise ValueError("url is required")

    max_chars = int(kwargs.get("max_chars", 200_000))
    timeout = float(kwargs.get("timeout", 30.0))

    from whitemagic.gardens.browser.web_research import DeepFetchResult, deep_fetch

    async def _fetch() -> DeepFetchResult:
        return await deep_fetch(url, max_chars=max_chars, timeout=timeout)

    fetch_result = _run_async(_fetch())

    result = {
        "url": fetch_result.url,
        "title": fetch_result.title,
        "content": fetch_result.content,
        "content_length": fetch_result.content_length,
        "status_code": fetch_result.status_code,
        "duration_ms": round(fetch_result.duration_ms, 1),
        "pages_fetched": fetch_result.pages_fetched,
        "success": fetch_result.success,
        "error": fetch_result.error,
    }

    _emit(
        "DEEP_FETCH",
        {
            "url": url,
            "success": fetch_result.success,
            "length": fetch_result.content_length,
            "pages": fetch_result.pages_fetched,
        },
    )
    return {"status": "success", **result}


def handle_research_repo(**kwargs: Any) -> dict[str, Any]:
    """Research a GitHub repo by fetching docs and storing as memories for Q&A."""
    repo = kwargs.get("repo", "")
    if not repo:
        raise ValueError("repo is required")

    max_pages = int(kwargs.get("max_pages", 5))
    max_chars_per_page = int(kwargs.get("max_chars_per_page", 50_000))
    store_memories = kwargs.get("store_memories", True)

    from whitemagic.gardens.browser.web_research import (
        RepoResearchResult,
        research_repo,
    )

    async def _research() -> RepoResearchResult:
        return await research_repo(
            repo,
            max_pages=max_pages,
            max_chars_per_page=max_chars_per_page,
            store_memories=store_memories,
        )

    result = _run_async(_research())

    _emit(
        "RESEARCH_REPO",
        {
            "repo": repo,
            "pages": result.pages_fetched,
            "memories": len(result.memory_ids),
        },
    )
    return {"status": "success", **result.to_dict()}


def handle_research_url(**kwargs: Any) -> dict[str, Any]:
    """Fetch full content from any URL and store as a memory for Q&A."""
    url = kwargs.get("url", "")
    if not url:
        raise ValueError("url is required")

    max_chars = int(kwargs.get("max_chars", 200_000))
    timeout = float(kwargs.get("timeout", 30.0))
    store_memory = kwargs.get("store_memory", True)

    from whitemagic.gardens.browser.web_research import URLResearchResult, research_url

    async def _research() -> URLResearchResult:
        return await research_url(
            url, max_chars=max_chars, timeout=timeout, store_memory=store_memory
        )

    result = _run_async(_research())

    _emit(
        "RESEARCH_URL",
        {"url": url, "success": result.success, "memory_id": result.memory_id},
    )
    return {"status": "success", **result.to_dict()}


def handle_parallel_reason(**kwargs: Any) -> dict[str, Any]:
    """Run parallel multi-branch reasoning with branching, backtracking, and revision."""
    question = kwargs.get("question", "")
    if not question:
        raise ValueError("question is required")

    max_branches = int(kwargs.get("max_branches", 4))
    max_depth = int(kwargs.get("max_depth", 6))
    fork_threshold = float(kwargs.get("fork_threshold", 0.5))

    import asyncio

    from whitemagic.core.intelligence.parallel_reasoning import ParallelReasoningTree

    tree = ParallelReasoningTree(question=question)

    async def _explore():
        return await tree.explore(
            max_branches=max_branches,
            max_depth=max_depth,
            fork_threshold=fork_threshold,
        )

    try:
        asyncio.get_running_loop()
        # We're in an async context, use thread pool
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(asyncio.run, _explore()).result()
    except RuntimeError:
        result = asyncio.run(_explore())

    _emit(
        "PARALLEL_REASON",
        {
            "question": question,
            "branches": len(result.branches),
            "best": result.best_branch_id,
        },
    )
    return {"status": "success", **result.to_dict()}


def handle_web_search_batch(**kwargs: Any) -> dict[str, Any]:
    """Search multiple queries in parallel -- batch web search for rapid research."""
    queries = kwargs.get("queries", [])
    if not queries:
        raise ValueError("queries list is required")

    num_results = int(kwargs.get("num_results_per_query", 5))
    timeout = float(kwargs.get("timeout", 10.0))
    category = kwargs.get("category")

    from whitemagic.gardens.browser.web_research import (
        BatchSearchResult,
        web_search_batch,
    )

    async def _batch() -> BatchSearchResult:
        return await web_search_batch(
            queries,
            num_results_per_query=num_results,
            timeout=timeout,
            category=category,
        )

    result = _run_async(_batch())
    _emit("WEB_SEARCH_BATCH", {"queries": len(queries), "total": result.total_results})
    return {"status": "success", **result.to_dict()}


def handle_rabbit_hole_research(**kwargs: Any) -> dict[str, Any]:
    """Deep recursive spiral research -- batched web search + deep_fetch + synthesis.

    Explores a topic by:
    1. Searching for the topic
    2. Extracting unfamiliar terms from results
    3. Batch-searching all terms in parallel
    4. Deep-fetching top results
    5. Recursing to max_depth levels
    6. Cross-referencing and synthesizing

    Stores results as memories for Q&A and caches content for re-reading.
    """
    topic = kwargs.get("topic", "")
    if not topic:
        raise ValueError("topic is required")

    max_depth = int(kwargs.get("max_depth", 3))
    max_parallel_terms = int(kwargs.get("max_parallel_terms", 12))
    num_search_results = int(kwargs.get("num_search_results", 5))
    fetch_top_results = int(kwargs.get("fetch_top_results", 3))
    max_chars_per_fetch = int(kwargs.get("max_chars_per_fetch", 50_000))
    store_memories = kwargs.get("store_memories", True)
    cache_content = kwargs.get("cache_content", True)
    initial_temperature = float(kwargs.get("initial_temperature", 0.0))
    temperature_rise = float(kwargs.get("temperature_rise", 0.25))
    novelty_floor = float(kwargs.get("novelty_floor", 0.15))

    from whitemagic.gardens.wisdom.rabbit_hole import RabbitHoleExplorer

    explorer = RabbitHoleExplorer(max_depth=max_depth)

    async def _explore():
        return await explorer.web_explore(
            topic=topic,
            max_depth=max_depth,
            max_parallel_terms=max_parallel_terms,
            num_search_results=num_search_results,
            fetch_top_results=fetch_top_results,
            max_chars_per_fetch=max_chars_per_fetch,
            store_memories=store_memories,
            cache_content=cache_content,
            initial_temperature=initial_temperature,
            temperature_rise=temperature_rise,
            novelty_floor=novelty_floor,
        )

    report = _run_async(_explore())

    result = {
        "status": "success",
        "title": report.title,
        "topics": report.topics,
        "entries_count": len(report.entries),
        "synthesis": report.synthesis,
        "connections_count": len(report.connections),
        "new_holes": report.new_holes,
        "temperature_curve": report.temperature_curve,
        "novelty_by_level": report.novelty_by_level,
        "entries": [
            {
                "term": e.term,
                "definition": e.definition[:200],
                "source": e.source,
                "depth": e.depth,
                "novelty_score": round(e.novelty_score, 3),
                "related_terms": e.related_terms[:5],
            }
            for e in report.entries
        ],
    }

    _emit(
        "RABBIT_HOLE",
        {"topic": topic, "entries": len(report.entries), "depth": max_depth},
    )
    return result


def handle_web_cache_list(**kwargs: Any) -> dict[str, Any]:
    """List all cached web content files with metadata."""
    from whitemagic.gardens.browser.web_research import list_cached_content

    items = list_cached_content()
    return {"status": "success", "count": len(items), "items": items}


def handle_web_cache_clear(**kwargs: Any) -> dict[str, Any]:
    """Clear cached web content. Optionally only older than N hours."""
    from whitemagic.gardens.browser.web_research import clear_cached_content

    older_than = kwargs.get("older_than_hours")
    if older_than:
        older_than = int(older_than)
    removed = clear_cached_content(older_than_hours=older_than)
    return {"status": "success", "removed": removed}


def handle_codegenome_validate(**kwargs: Any) -> dict[str, Any]:
    """Recursive self-improvement pipeline: reason -> generate -> analyze -> score -> iterate.

    Wires ParallelReasoningTree + CodeGenome + STRATA + Monte Carlo into an
    iterative improvement loop. Each iteration:
    1. ParallelReasoningTree explores implementation approaches
    2. CodeGenome generates code from the best approach
    3. STRATA runs static analysis on the output
    4. Monte Carlo scores confidence
    5. If score is low, STRATA issues feed back as revision triggers
    6. Lessons persisted to AutonomousLearner
    """
    prompt = kwargs.get("prompt", "")
    if not prompt:
        raise ValueError("prompt is required")

    max_iterations = int(kwargs.get("max_iterations", 3))
    score_threshold = float(kwargs.get("score_threshold", 0.8))
    repo_path = kwargs.get("repo_path")

    from whitemagic.core.intelligence.self_improvement import run_self_improvement

    result = run_self_improvement(
        prompt=prompt,
        max_iterations=max_iterations,
        score_threshold=score_threshold,
        repo_path=repo_path,
    )

    _emit(
        "CODEGENOME_VALIDATE",
        {
            "prompt": prompt[:50],
            "iterations": len(result.get("iterations", [])),
            "score": result.get("final_score", 0),
        },
    )
    return {"status": "success", **result}


def handle_alchemical_cycle(**kwargs: Any) -> dict[str, Any]:
    """Run the alchemical procession meta-loop: yin/yang zodiacal cycle.

    Chains tools in an adaptive loop across alchemical stages:
    Yang (creative): calcination -> dissolution -> separation -> conjunction ->
                     fermentation -> distillation -> coagulation
    Yin (receptive): Same stages in reflective mode (analyze, score, learn)
    Fixed hubs: Stability checkpoints (Taurus, Leo, Scorpio, Aquarius)

    Each cycle's output becomes the next cycle's input, creating
    iterative refinement through alchemical transformation.
    """
    task = kwargs.get("task", "")
    if not task:
        raise ValueError("task is required")

    cycles = int(kwargs.get("cycles", 2))

    from whitemagic.core.intelligence.alchemical_loop import run_alchemical_cycle

    result = run_alchemical_cycle(task=task, cycles=cycles)

    _emit(
        "ALCHEMICAL_CYCLE",
        {
            "task": task[:50],
            "cycles": len(result.get("cycles", [])),
            "success": result.get("success"),
        },
    )
    return {"status": "success", **result}


def handle_browser_session_status(**kwargs: Any) -> dict[str, Any]:
    """Get the status of the persistent browser session."""
    from whitemagic.gardens.browser.web_research import BrowserSessionManager

    mgr = BrowserSessionManager.get()
    return {"status": "success", **mgr.status()}


def handle_web_fetch_enhanced(**kwargs: Any) -> dict[str, Any]:
    """Enhanced web fetch with outline extraction, content chunking, and summarization.

    Fetches a URL, then processes the content through three stages:
    1. Outline Builder — extracts heading hierarchy from HTML
    2. Content Chunker — splits text into ~2K-char semantic chunks with overlap
    3. Content Summarizer — generates summary via Ollama (extractive fallback)

    Supports progressive loading: return outline + summary + chunk metadata first,
    then load individual chunks on demand via the chunk_index parameter.

    When chunk_index is specified, returns only that chunk's full text.
    """
    url = kwargs.get("url", "")
    if not url:
        raise ValueError("url is required")

    chunk_size = int(kwargs.get("chunk_size", 2000))
    overlap = int(kwargs.get("overlap", 200))
    summarize = kwargs.get("summarize", True)
    focus = kwargs.get("focus", "")
    ollama_model = kwargs.get("ollama_model", "gemma3:4b")
    max_chars = int(kwargs.get("max_chars", 50_000))
    chunk_index = kwargs.get("chunk_index")

    from whitemagic.gardens.browser.content_intelligence import (
        enhanced_to_dict,
        process_content,
    )
    from whitemagic.gardens.browser.web_research import web_fetch

    async def _fetch():
        return await web_fetch(url, max_chars=max_chars)

    fetch_result = _run_async(_fetch())

    if not fetch_result.success:
        return {
            "status": "error",
            "error": fetch_result.error or "Fetch failed",
            "url": url,
        }

    if chunk_index is not None:
        # Re-fetch and re-process to get the specific chunk
        # (In production, we'd cache the EnhancedContent, but this keeps it stateless)
        enhanced = process_content(
            html=fetch_result.content,  # We only have text, but process_content handles it
            text=fetch_result.content,
            title=fetch_result.title,
            chunk_size=chunk_size,
            overlap=overlap,
            summarize=False,  # Don't re-summarize for chunk retrieval
            focus=focus,
            ollama_model=ollama_model,
        )
        idx = int(chunk_index)
        if idx < 0 or idx >= len(enhanced.chunks):
            return {
                "status": "error",
                "error": f"chunk_index {idx} out of range (0-{len(enhanced.chunks) - 1})",
            }
        chunk = enhanced.chunks[idx]
        return {
            "status": "success",
            "url": url,
            "title": enhanced.title,
            "chunk_index": idx,
            "chunk_text": chunk.text,
            "char_count": chunk.char_count,
            "heading": chunk.heading,
            "token_estimate": chunk.token_estimate,
        }

    # Full processing: outline + summary + chunks
    # web_fetch already converted to text, so we re-fetch raw HTML
    raw_html = fetch_result.content  # Fallback: use text as-is
    try:
        import httpx

        async def _fetch_raw():
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": "WhiteMagic/1.0"},
            ) as client:
                resp = await client.get(url)
                if resp.status_code in range(200, 400):
                    return resp.text
                return ""

        raw_html = _run_async(_fetch_raw()) or fetch_result.content
    except Exception:
        pass

    enhanced = process_content(
        html=raw_html,
        text=fetch_result.content,
        title=fetch_result.title,
        chunk_size=chunk_size,
        overlap=overlap,
        summarize=summarize,
        focus=focus,
        ollama_model=ollama_model,
    )

    result = enhanced_to_dict(enhanced, include_chunks=True)
    result["status"] = "success"
    result["url"] = url

    _emit(
        "WEB_FETCH_ENHANCED",
        {
            "url": url,
            "outline_nodes": len(enhanced.outline),
            "chunks": enhanced.total_chunks,
            "summarizer": enhanced.summarizer_used,
        },
    )

    return result
