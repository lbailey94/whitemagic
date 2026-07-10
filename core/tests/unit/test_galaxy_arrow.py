# ruff: noqa: BLE001
"""Tests for Phase 3: Galaxy Export/Import with Arrow format.

Verifies that the Arrow export/import pipeline includes galaxy metadata
and that the Python-side methods handle galaxy filtering correctly.
Also validates the Rust Arrow bridge schema includes the galaxy column.
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_galaxy_arrow_"))

_SRC = Path(__file__).resolve().parent.parent.parent / "whitemagic"
_RUST_SRC = Path(__file__).resolve().parent.parent.parent / "whitemagic-rust" / "src"


class TestPythonArrowExportGalaxy(unittest.TestCase):
    """Verify arrow_export method signature includes galaxy parameter."""

    def test_export_has_galaxy_param(self):
        filepath = _SRC / "core/memory/unified.py"
        source = filepath.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) or isinstance(
                node, ast.FunctionDef
            ):
                if node.name == "arrow_export":
                    params = [a.arg for a in node.args.args]
                    self.assertIn(
                        "galaxy", params, "arrow_export must accept galaxy parameter"
                    )
                    return
        self.fail("arrow_export method not found")

    def test_export_passes_galaxy_to_search(self):
        filepath = _SRC / "core/memory/unified.py"
        source = filepath.read_text()
        # Check that galaxy is passed to backend.search
        self.assertIn(
            "galaxy=galaxy", source, "arrow_export must pass galaxy to backend.search"
        )

    def test_export_includes_galaxy_in_docs(self):
        filepath = _SRC / "core/memory/unified.py"
        source = filepath.read_text()
        self.assertIn(
            '"galaxy"', source, "arrow_export must include galaxy in export docs"
        )


class TestPythonArrowImportGalaxy(unittest.TestCase):
    """Verify arrow_import method passes galaxy to store()."""

    def test_import_passes_galaxy_to_store(self):
        filepath = _SRC / "core/memory/unified.py"
        source = filepath.read_text()
        # Find the arrow_import method and check it passes galaxy to store
        self.assertIn(
            'galaxy=doc.get("galaxy", "universal")',
            source,
            "arrow_import must pass galaxy to store()",
        )


class TestRustArrowSchemaGalaxy(unittest.TestCase):
    """Verify Rust Arrow schema includes galaxy field."""

    def test_schema_has_galaxy_field(self):
        filepath = _RUST_SRC / "ffi/arrow_bridge.rs"
        if not filepath.exists():
            self.skipTest("Rust source not found at expected path")
        source = filepath.read_text()
        self.assertIn(
            'Field::new("galaxy"', source, "Rust Arrow schema must include galaxy field"
        )

    def test_memory_record_has_galaxy(self):
        filepath = _RUST_SRC / "ffi/arrow_bridge.rs"
        if not filepath.exists():
            self.skipTest("Rust source not found at expected path")
        source = filepath.read_text()
        self.assertIn(
            "pub galaxy: String", source, "MemoryRecord struct must have galaxy field"
        )

    def test_memories_to_arrow_includes_galaxy(self):
        filepath = _RUST_SRC / "ffi/arrow_bridge.rs"
        if not filepath.exists():
            self.skipTest("Rust source not found at expected path")
        source = filepath.read_text()
        self.assertIn(
            "galaxy_builder", source, "memories_to_arrow must build galaxy column"
        )

    def test_arrow_to_memories_reads_galaxy(self):
        filepath = _RUST_SRC / "ffi/arrow_bridge.rs"
        if not filepath.exists():
            self.skipTest("Rust source not found at expected path")
        source = filepath.read_text()
        self.assertIn("galaxies", source, "arrow_to_memories must read galaxy column")
        self.assertIn(
            "galaxy: galaxies.value(i).to_string()",
            source,
            "arrow_to_memories must extract galaxy value",
        )


class TestGalaxyExportImportHandlersRegistered(unittest.TestCase):
    """Verify galaxy.export and galaxy.import are registered in dispatch."""

    def test_dispatch_has_export(self):
        filepath = _SRC / "tools/dispatch_memory.py"
        source = filepath.read_text()
        self.assertIn(
            '"galaxy.export"', source, "dispatch_memory.py must register galaxy.export"
        )

    def test_dispatch_has_import(self):
        filepath = _SRC / "tools/dispatch_memory.py"
        source = filepath.read_text()
        self.assertIn(
            '"galaxy.import"', source, "dispatch_memory.py must register galaxy.import"
        )


class TestGalaxyExportImportHandlersExist(unittest.TestCase):
    """Verify handler functions exist."""

    def test_handle_galaxy_export_exists(self):
        filepath = _SRC / "tools/handlers/galaxy.py"
        source = filepath.read_text()
        self.assertIn(
            "def handle_galaxy_export",
            source,
            "handle_galaxy_export must be defined",
        )

    def test_handle_galaxy_import_exists(self):
        filepath = _SRC / "tools/handlers/galaxy.py"
        source = filepath.read_text()
        self.assertIn(
            "def handle_galaxy_import",
            source,
            "handle_galaxy_import must be defined",
        )


class TestGalaxyExportImportToolDefs(unittest.TestCase):
    """Verify tool definitions exist for export/import."""

    def test_export_tool_def_exists(self):
        filepath = _SRC / "tools/registry_defs/galaxy.py"
        source = filepath.read_text()
        self.assertIn(
            'name="galaxy.export"', source, "galaxy.export tool definition must exist"
        )

    def test_import_tool_def_exists(self):
        filepath = _SRC / "tools/registry_defs/galaxy.py"
        source = filepath.read_text()
        self.assertIn(
            'name="galaxy.import"', source, "galaxy.import tool definition must exist"
        )


if __name__ == "__main__":
    unittest.main()
