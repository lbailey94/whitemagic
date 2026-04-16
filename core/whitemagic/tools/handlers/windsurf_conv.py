"""Windsurf conversation reader tool handlers."""
from typing import Any


def handle_windsurf_list_conversations(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    return {"status": "success", "conversations": reader.list_conversations()}


def handle_windsurf_read_conversation(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    path = kwargs.get("path")
    if not path:
        return {"status": "error", "error": "path is required"}
    conv = reader.read_conversation(path)
    return {"status": "success", **conv.to_dict()}


def handle_windsurf_export_conversation(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    path = kwargs.get("path")
    if not path:
        return {"status": "error", "error": "path is required"}
    content = reader.export_conversation(path, kwargs.get("format", "markdown"))
    return {"status": "success", "content": content}


def handle_windsurf_search_conversations(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    query = kwargs.get("query")
    if not query:
        return {"status": "error", "error": "query is required"}
    results = reader.search_conversations(query)
    return {"status": "success", "results": results}


def handle_windsurf_stats(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.archaeology.windsurf_reader import WindsurfConversationReader
    reader = WindsurfConversationReader()
    return {"status": "success", **reader.stats()}
