"""Browser Automation Garden.

AI-driven browser automation using Chrome DevTools Protocol (CDP).
Enables AI agents to navigate, interact with, and extract data from web pages.

Features:
- CDP WebSocket connection to Chrome/Chromium
- DOM distillation (strip to interactables)
- Visual capture (screenshots)
- AI-friendly actions (click, type, navigate)

Usage:
    from whitemagic.gardens.browser import BrowserSession

    async with BrowserSession() as browser:
        await browser.navigate("https://example.com")
        dom = await browser.extract_dom()
        await browser.click("#login-button")

Requires: Chrome/Chromium with --remote-debugging-port=9222
"""

from .actions import BrowserActions, BrowserSession
from .cdp import CDPConnection, connect_to_chrome
from .distiller import DOMDistiller, SimplifiedElement
from .screenshot import capture_element, capture_screenshot
from .web_research import (
    BrowserSessionManager,
    BatchSearchResult,
    DeepFetchResult,
    FetchResult,
    RepoResearchResult,
    SearchResponse,
    URLResearchResult,
    SearchResult,
    research_topic,
    deep_fetch,
    research_repo,
    research_url,
    web_fetch,
    web_search_batch,
    web_search,
)

__all__ = [
    # CDP Connection
    "CDPConnection",
    "connect_to_chrome",
    # DOM Distillation
    "DOMDistiller",
    "SimplifiedElement",
    # Screenshots
    "capture_screenshot",
    "capture_element",
    # Actions
    "BrowserActions",
    "BrowserSession",
    # Web Research
    "web_fetch",
    "web_search",
    "research_topic",
    "FetchResult",
    "SearchResult",
    "SearchResponse",
    "BrowserSessionManager",
]

__version__ = "0.2.0"
