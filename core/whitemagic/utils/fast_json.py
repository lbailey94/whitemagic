"""Fast JSON serialization via orjson with stdlib fallback.

Drop-in replacement for json.dumps/json.loads that uses orjson when available.
orjson is 3-10x faster than stdlib json for serialization.

Usage:
    from whitemagic.utils.fast_json import dumps, dumps_bytes, loads, dumps_str

    # bytes output (fastest — use for HTTP responses, IPC, file I/O)
    data = dumps_bytes({"key": "value"})  # explicit bytes intent
    data = dumps({"key": "value"})         # same thing

    # str output (for APIs that need str, not bytes — ~60% slower)
    data = dumps_str({"key": "value"})

    # deserialization
    obj = loads(b'{"key": "value"}')
"""

from __future__ import annotations

import json as _json
from typing import Any

try:
    import orjson as _orjson

    def dumps(obj: Any, **kwargs: Any) -> bytes:
        """Serialize to JSON bytes using orjson."""
        opts = _orjson.OPT_NON_STR_KEYS
        if kwargs.get("indent"):
            opts |= _orjson.OPT_INDENT_2
        if kwargs.get("sort_keys"):
            opts |= _orjson.OPT_SORT_KEYS
        default = kwargs.get("default")
        return _orjson.dumps(obj, option=opts, default=default)

    def dumps_str(obj: Any, **kwargs: Any) -> str:
        """Serialize to JSON string using orjson (decode bytes to str)."""
        return dumps(obj, **kwargs).decode("utf-8")

    def loads(data: bytes | str) -> Any:
        """Deserialize JSON using orjson."""
        return _orjson.loads(data)

    # Explicit bytes alias — use in bytes-native paths (HTTP, IPC, file I/O)
    # to signal intent and avoid accidental .decode() overhead
    dumps_bytes = dumps

    BACKEND = "orjson"

except ImportError:
    def dumps(obj: Any, **kwargs: Any) -> bytes:
        """Serialize to JSON bytes using stdlib json."""
        return _json.dumps(obj, **kwargs).encode("utf-8")

    def dumps_str(obj: Any, **kwargs: Any) -> str:
        """Serialize to JSON string using stdlib json."""
        return _json.dumps(obj, **kwargs)

    def loads(data: bytes | str) -> Any:
        """Deserialize JSON using stdlib json."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return _json.loads(data)

    # Explicit bytes alias for API parity with orjson path
    dumps_bytes = dumps

    BACKEND = "json"
