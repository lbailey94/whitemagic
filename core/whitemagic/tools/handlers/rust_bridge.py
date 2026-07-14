"""Rust bridge tool handlers."""

from typing import Any, cast


import logging
logger = logging.getLogger(__name__)

def _load_rust() -> tuple[Any, Any]:
    from whitemagic.tools.unified_api import _load_rust

    return cast("tuple[Any, Any]", _load_rust())


def handle_rust_audit(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a rust audit event.

    Returns:
        dict[str, Any]
    """
    path = kwargs.get("path", ".")
    pattern = kwargs.get("pattern", "*.py")
    rust, rust_error = _load_rust()
    if rust is None or not hasattr(rust, "audit_directory"):
        # Python fallback: basic file listing
        import os

        from pathlib import Path

        search_path = Path(str(path))
        if not search_path.exists():
            return {"status": "error", "message": f"Path not found: {path}"}
        files = []
        for root, _dirs, fnames in os.walk(search_path):
            for fname in fnames:
                if Path(fname).match(pattern):
                    fpath = Path(root) / fname
                    try:
                        stat = fpath.stat()
                        files.append({
                            "path": str(fpath),
                            "size": stat.st_size,
                            "lines": 0,
                            "words": 0,
                            "summary": "",
                        })
                    except OSError:
                        logger.debug("Ignored OSError in rust_bridge.py:48")
                    if len(files) >= 1000:
                        break
        file_summaries = files[:100]
        return {
            "status": "success",
            "files_scanned": len(files),
            "files": file_summaries,
            "rust_error": rust_error if rust is None else "audit_directory not available",
        }
    files = rust.audit_directory(str(path), pattern, 1000)
    file_summaries = [
        {
            "path": info.path,
            "size": info.size,
            "lines": info.lines,
            "words": info.words,
            "summary": info.summary,
        }
        for info in files[:100]
    ]
    return {"status": "success", "files_scanned": len(files), "files": file_summaries}


def handle_rust_compress(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a rust compress event.

    Returns:
        dict[str, Any]
    """
    data = str(kwargs.get("data", ""))
    rust, rust_error = _load_rust()
    if rust is None or not hasattr(rust, "fast_compress"):
        import gzip

        compressed = gzip.compress(data.encode("utf-8"))
        return {
            "status": "success",
            "compressed_size": len(compressed),
            "rust_error": rust_error if rust is None else "fast_compress not available",
        }
    compressed = rust.fast_compress(data)
    return {"status": "success", "compressed_size": len(compressed)}


def handle_rust_similarity(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a rust similarity event.

    Returns:
        dict[str, Any]
    """
    text1 = kwargs.get("text1", "")
    text2 = kwargs.get("text2", "")
    rust, rust_error = _load_rust()
    if rust is not None and hasattr(rust, "rust_similarity"):
        similarity = rust.rust_similarity(text1, text2)
        return {"status": "success", "similarity": float(similarity)}
    if rust is not None and hasattr(rust, "fast_similarity"):
        similarity = rust.fast_similarity(text1, text2)
        return {"status": "success", "similarity": float(similarity)}
    from difflib import SequenceMatcher

    similarity = SequenceMatcher(None, text1, text2).ratio()
    return {"status": "success", "similarity": similarity, "rust_error": rust_error}


def handle_rust_status(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a rust status event.

    Returns:
        dict[str, Any]
    """
    rust, rust_error = _load_rust()
    if rust is None:
        return {"status": "success", "available": False, "rust_error": rust_error}
    functions = [
        "audit_directory",
        "read_file_fast",
        "read_files_fast",
        "fast_compress",
        "rust_similarity",
    ]
    return {
        "status": "success",
        "available": True,
        "version": getattr(rust, "__version__", "unknown"),
        "functions": [name for name in functions if hasattr(rust, name)],
    }
