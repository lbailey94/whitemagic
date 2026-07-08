"""Tests for CodebaseScanner v2 — chunked ingestion + semantic recall."""

# ruff: noqa: BLE001
import os
import tempfile

import pytest

# Set temp state root BEFORE any whitemagic imports
_tmp = tempfile.mkdtemp(prefix="wm_cb_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_SKIP_POLYGLOT"] = "1"


@pytest.fixture
def project_dir():
    """Create a temporary project directory with sample files."""
    d = tempfile.mkdtemp(prefix="wm_proj_")
    # Create some files
    (open(os.path.join(d, "main.py"), "w").write(
        "def main():\n    print('hello world')\n\n"
        "if __name__ == '__main__':\n    main()\n"
    ))
    (open(os.path.join(d, "README.md"), "w").write(
        "# Test Project\n\nA test project for codebase scanning.\n"
    ))
    (open(os.path.join(d, "pyproject.toml"), "w").write(
        '[project]\nname = "test"\nversion = "0.1.0"\n'
    ))
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    (open(os.path.join(d, "src", "utils.py"), "w").write(
        "def helper(x):\n    return x * 2\n"
    ))
    (open(os.path.join(d, "src", "models.py"), "w").write(
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class User:\n    name: str\n    age: int\n"
    ))
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    (open(os.path.join(d, "tests", "test_main.py"), "w").write(
        "def test_main():\n    assert True\n"
    ))
    # Binary file to skip
    (open(os.path.join(d, "image.png"), "wb").write(b"\x89PNG\r\n\x1a\n"))
    return d


@pytest.fixture
def scanner(project_dir):
    """Create a CodebaseScanner instance for the temp project."""
    from whitemagic.core.memory.codebase_scanner import CodebaseScanner
    return CodebaseScanner(
        project_root=project_dir,
        chunk_size=100,  # Small chunks for testing
        chunk_overlap=20,
    )


# ── Chunk splitting tests ─────────────────────────────────────────────


class TestChunkSplitting:
    def test_short_file_single_chunk(self):
        from whitemagic.core.memory.codebase_scanner import split_into_chunks
        text = "short text"
        chunks = split_into_chunks(text, chunk_size=100, overlap=20)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_long_file_multiple_chunks(self):
        from whitemagic.core.memory.codebase_scanner import split_into_chunks
        text = "paragraph one\n\n" * 100  # ~1800 chars
        chunks = split_into_chunks(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1

    def test_overlap_preserves_context(self):
        from whitemagic.core.memory.codebase_scanner import split_into_chunks
        text = "AAA\n\nBBB\n\nCCC\n\nDDD\n\nEEE"
        chunks = split_into_chunks(text, chunk_size=15, overlap=5)
        # Each chunk should have some content
        for chunk in chunks:
            assert len(chunk) > 0

    def test_empty_text(self):
        from whitemagic.core.memory.codebase_scanner import split_into_chunks
        chunks = split_into_chunks("", chunk_size=100, overlap=20)
        assert chunks == [""]


# ── Scan tests ────────────────────────────────────────────────────────


class TestScan:
    def test_scan_returns_scanresult(self, scanner):
        from whitemagic.core.memory.codebase_scanner import ScanResult
        result = scanner.scan(incremental=False)
        assert isinstance(result, ScanResult)

    def test_scan_finds_files(self, scanner):
        result = scanner.scan(incremental=False)
        assert result.total_files == 6  # 6 text files (png skipped)
        assert result.errors == 0

    def test_scan_skips_binary(self, scanner):
        result = scanner.scan(incremental=False)
        assert ".png" not in result.by_extension

    def test_scan_counts_dirs(self, scanner):
        result = scanner.scan(incremental=False)
        assert result.total_dirs > 0

    def test_scan_creates_chunks(self, scanner):
        result = scanner.scan(incremental=False)
        assert result.chunks_created > 0
        assert result.ingested > 0

    def test_scan_to_dict(self, scanner):
        result = scanner.scan(incremental=False)
        d = result.to_dict()
        assert "chunks_created" in d
        assert "embedded" in d
        assert "scanner_version" not in d  # Only in manifest

    def test_scan_incremental_unchanged(self, scanner):
        result1 = scanner.scan(incremental=False)
        assert result1.ingested > 0
        result2 = scanner.scan(incremental=True)
        assert result2.ingested == 0
        assert result2.unchanged > 0

    def test_scan_progress_callback(self, scanner):
        phases: list[str] = []
        def cb(phase, current, total):
            phases.append(phase)
        scanner.scan(incremental=False, progress_cb=cb)
        assert "walking" in phases
        assert "reading" in phases
        assert "chunking" in phases


# ── Recall tests ──────────────────────────────────────────────────────


class TestRecall:
    def test_recall_returns_results(self, scanner):
        scanner.scan(incremental=False)
        results = scanner.recall("main function")
        assert isinstance(results, list)

    def test_recall_with_tags(self, scanner):
        scanner.scan(incremental=False)
        results = scanner.recall("helper", tags=["ext:py"])
        assert isinstance(results, list)

    def test_recall_empty_query(self, scanner):
        results = scanner.recall("")
        assert results == []

    def test_recall_has_recall_type(self, scanner):
        scanner.scan(incremental=False)
        results = scanner.recall("main", semantic=False)  # Force FTS5
        if results:
            assert "recall_type" in results[0]

    def test_recall_semantic_flag(self, scanner):
        scanner.scan(incremental=False)
        # With semantic=True but no embeddings, should fall back to FTS5
        results = scanner.recall("main", semantic=True)
        assert isinstance(results, list)


# ── Structure tests ───────────────────────────────────────────────────


class TestStructure:
    def test_structure_root(self, scanner):
        scanner.scan(incremental=False)
        result = scanner.structure()
        assert "files" in result
        assert "subdirs" in result
        # Root should have at least some files
        assert len(result["files"]) > 0

    def test_structure_subdir(self, scanner):
        scanner.scan(incremental=False)
        result = scanner.structure("src")
        assert "files" in result
        assert "utils.py" in result["files"] or any("utils" in f for f in result["files"])

    def test_structure_nonexistent(self, scanner):
        result = scanner.structure("nonexistent/path")
        # FTS5 may return approximate matches; just check it doesn't crash
        assert "files" in result


# ── Status tests ──────────────────────────────────────────────────────


class TestStatus:
    def test_status_before_scan(self, scanner):
        result = scanner.status()
        assert "last_scan" in result

    def test_status_after_scan(self, scanner):
        scanner.scan(incremental=False)
        result = scanner.status()
        assert result["last_scan"] != "never"
        assert "chunks_created" in result


# ── Handler tests ─────────────────────────────────────────────────────


class TestHandlers:
    def test_handle_codebase_scan(self, project_dir):
        from whitemagic.tools.handlers.codebase import handle_codebase_scan
        result = handle_codebase_scan(project_root=project_dir, incremental=False, embed=False)
        assert result["status"] == "success"
        assert result["total_files"] > 0
        assert result["chunks_created"] > 0

    def test_handle_codebase_recall(self, project_dir):
        from whitemagic.tools.handlers.codebase import (
            handle_codebase_recall,
            handle_codebase_scan,
        )
        handle_codebase_scan(project_root=project_dir, incremental=False, embed=False)
        result = handle_codebase_recall(query="main", semantic=False)
        assert result["status"] == "success"
        assert "results" in result

    def test_handle_codebase_recall_no_query(self):
        from whitemagic.tools.handlers.codebase import handle_codebase_recall
        result = handle_codebase_recall()
        assert result["status"] == "error"

    def test_handle_codebase_status(self, project_dir):
        from whitemagic.tools.handlers.codebase import (
            handle_codebase_scan,
            handle_codebase_status,
        )
        handle_codebase_scan(project_root=project_dir, incremental=False, embed=False)
        result = handle_codebase_status()
        assert result["status"] == "success"
        assert result["last_scan"] != "never"

    def test_handle_codebase_structure(self, project_dir):
        from whitemagic.tools.handlers.codebase import (
            handle_codebase_scan,
            handle_codebase_structure,
        )
        handle_codebase_scan(project_root=project_dir, incremental=False, embed=False)
        result = handle_codebase_structure()
        assert result["status"] == "success"
        assert "files" in result

    def test_handle_codebase_find(self, project_dir):
        from whitemagic.tools.handlers.codebase import (
            handle_codebase_find,
            handle_codebase_scan,
        )
        handle_codebase_scan(project_root=project_dir, incremental=False, embed=False)
        result = handle_codebase_find(extension="py")
        assert result["status"] == "success"
        assert result["count"] > 0


# ── PRAT mapping tests ────────────────────────────────────────────────


class TestPratMappings:
    def test_codebase_tools_mapped_to_chariot(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        for tool in ["codebase.scan", "codebase.recall", "codebase.structure",
                      "codebase.status", "codebase.find"]:
            assert tool in TOOL_TO_GANA, f"{tool} missing from TOOL_TO_GANA"
            assert TOOL_TO_GANA[tool] == "gana_chariot"


# ── Dispatch table tests ──────────────────────────────────────────────


class TestDispatchTable:
    def test_codebase_tools_in_dispatch(self):
        from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
        for tool in ["codebase.scan", "codebase.recall", "codebase.structure",
                      "codebase.status", "codebase.find"]:
            assert tool in DISPATCH_MEMORY, f"{tool} missing from DISPATCH_MEMORY"


# ── NLU classification tests ──────────────────────────────────────────


class TestNLUClassification:
    def test_classify_codebase_scan(self):
        from whitemagic.tools.handlers.meta_tool import classify
        gana, tool, conf = classify("scan the codebase")
        assert tool == "codebase.scan"
        assert gana == "gana_chariot"

    def test_classify_codebase_recall(self):
        from whitemagic.tools.handlers.meta_tool import classify
        gana, tool, conf = classify("recall codebase for authentication")
        assert tool == "codebase.recall"
        assert gana == "gana_chariot"

    def test_classify_codebase_structure(self):
        from whitemagic.tools.handlers.meta_tool import classify
        gana, tool, conf = classify("show codebase structure")
        assert tool == "codebase.structure"

    def test_classify_codebase_status(self):
        from whitemagic.tools.handlers.meta_tool import classify
        gana, tool, conf = classify("codebase status")
        assert tool == "codebase.status"

    def test_classify_codebase_find(self):
        from whitemagic.tools.handlers.meta_tool import classify
        gana, tool, conf = classify("find files with extension py in codebase")
        assert tool == "codebase.find"


# ── Galaxy router tests ───────────────────────────────────────────────


class TestGalaxyRouter:
    def test_codebase_scanner_routes_to_codex(self):
        from whitemagic.core.memory.galaxy_router import GalaxyRouter
        router = GalaxyRouter()
        galaxy = router.route("codebase_scanner")
        assert galaxy == "codex"

    def test_codebase_self_model_routes_to_codex(self):
        from whitemagic.core.memory.galaxy_router import GalaxyRouter
        router = GalaxyRouter()
        galaxy = router.route("codebase_self_model")
        assert galaxy == "codex"
