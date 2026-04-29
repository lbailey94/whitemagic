"""Browser tool handlers — CDP-based browser automation.

Wraps the gardens.browser package to provide sync MCP tool handlers.
All async operations use _run_async from web_research handler pattern.
"""
import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


def handle_browser_navigate(**kwargs: Any) -> dict[str, Any]:
    """Navigate browser to a URL."""
    url = kwargs.get("url", "")
    if not url:
        return {"status": "error", "error_code": "invalid_params", "message": "url is required"}

    from whitemagic.gardens.browser import BrowserSession

    async def _navigate() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            result = await browser.navigate(url)
            return {"success": result.success, "message": result.message}
        finally:
            await browser.disconnect()

    result = _run_async(_navigate())
    return {"status": "success", **result}


def handle_browser_click(**kwargs: Any) -> dict[str, Any]:
    """Click an element by CSS selector."""
    selector = kwargs.get("selector", "")
    if not selector:
        return {"status": "error", "error_code": "invalid_params", "message": "selector is required"}

    from whitemagic.gardens.browser import BrowserSession

    async def _click() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            result = await browser.click(selector)
            return {"success": result.success, "message": result.message}
        finally:
            await browser.disconnect()

    result = _run_async(_click())
    return {"status": "success", **result}


def handle_browser_type(**kwargs: Any) -> dict[str, Any]:
    """Type text into an element by CSS selector."""
    selector = kwargs.get("selector", "")
    text = kwargs.get("text", "")
    if not selector:
        return {"status": "error", "error_code": "invalid_params", "message": "selector is required"}

    from whitemagic.gardens.browser import BrowserSession

    async def _type() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            result = await browser.type_text(selector, text)
            return {"success": result.success, "message": result.message}
        finally:
            await browser.disconnect()

    result = _run_async(_type())
    return {"status": "success", **result}


def handle_browser_extract_dom(**kwargs: Any) -> dict[str, Any]:
    """Extract simplified DOM from current page."""
    from whitemagic.gardens.browser import BrowserSession, DOMDistiller

    async def _extract() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            cdp = browser._cdp
            if not cdp:
                return {"error": "CDP not connected"}
            # Get document root
            doc = await cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})
            root_node = doc.get("root", {})
            distiller = DOMDistiller()
            simplified = distiller.distill(root_node)
            return {
                "title": simplified.title,
                "url": simplified.url,
                "elements_count": len(simplified.elements),
                "elements": [e.to_dict() for e in simplified.elements[:50]],
            }
        finally:
            await browser.disconnect()

    result = _run_async(_extract())
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}


def handle_browser_screenshot(**kwargs: Any) -> dict[str, Any]:
    """Capture a screenshot of the current page."""
    from whitemagic.gardens.browser import BrowserSession, capture_screenshot

    async def _screenshot() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            cdp = browser._cdp
            if not cdp:
                return {"error": "CDP not connected"}
            b64 = await capture_screenshot(cdp)
            return {"screenshot_base64": b64, "format": "png"}
        finally:
            await browser.disconnect()

    result = _run_async(_screenshot())
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}


def handle_browser_get_interactables(**kwargs: Any) -> dict[str, Any]:
    """Get list of interactable elements on current page."""
    from whitemagic.gardens.browser import BrowserSession, DOMDistiller

    async def _get() -> dict[str, Any]:
        browser = BrowserSession()
        try:
            await browser.connect()
            cdp = browser._cdp
            if not cdp:
                return {"error": "CDP not connected"}
            doc = await cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})
            root_node = doc.get("root", {})
            distiller = DOMDistiller()
            simplified = distiller.distill(root_node)
            interactables = [e for e in simplified.elements if e.interactable]
            return {
                "count": len(interactables),
                "elements": [
                    {
                        "tag": e.tag,
                        "text": e.text[:100] if e.text else "",
                        "selector": e.selector,
                        "type": e.element_type,
                    }
                    for e in interactables[:100]
                ],
            }
        finally:
            await browser.disconnect()

    result = _run_async(_get())
    if "error" in result:
        return {"status": "error", "error_code": "internal_error", "message": result["error"]}
    return {"status": "success", **result}
