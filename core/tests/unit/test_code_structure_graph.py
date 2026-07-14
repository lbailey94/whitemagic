"""Tests for Code Structure Graph — Phase 1.

Tests cover:
- Python AST extraction (functions, classes, imports, calls, inherits)
- Regex extraction for non-Python languages (Rust, TypeScript, Go, etc.)
- SQLite persistence (store + load)
- Incremental mode (skip unchanged files)
- Query operations (path, explain, communities, god_nodes, subgraph)
- Export/import JSON
- Singleton accessor
"""
import json
import os
import tempfile
import textwrap
from pathlib import Path

import pytest

from whitemagic.core.intelligence.code_structure_graph import (
    CodeEdge,
    CodeNode,
    CodeStructureGraph,
    _hash_content,
    _make_edge_id,
    _make_node_id,
    get_code_structure_graph,
)

# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    os.unlink(path)  # Remove so SQLite creates fresh
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def graph(tmp_db):
    return CodeStructureGraph(db_path=tmp_db)


@pytest.fixture
def sample_python_code():
    return textwrap.dedent("""\
        import os
        from pathlib import Path
        import json as json_mod

        class BaseWidget:
            def render(self):
                pass

        class MyWidget(BaseWidget):
            def __init__(self, name):
                self.name = name

            def render(self):
                print(self.name)
                return self.name

            async def fetch_data(self):
                return json_mod.loads("{}")

        def standalone_function(x):
            return x * 2

        def caller_function():
            result = standalone_function(5)
            widget = MyWidget("test")
            widget.render()
            return result
    """)


@pytest.fixture
def sample_rust_code():
    return textwrap.dedent("""\
        use std::collections::HashMap;
        use serde::Serialize;

        pub struct MyStruct {
            field: u32,
        }

        impl MyStruct {
            pub fn new() -> Self {
                Self { field: 0 }
            }
        }

        trait MyTrait {
            fn do_thing(&self);
        }

        fn helper_function(x: i32) -> i32 {
            x + 1
        }
    """)


@pytest.fixture
def sample_typescript_code():
    return textwrap.dedent("""\
        import { Component } from 'react';
        const axios = require('axios');

        interface MyInterface {
            id: number;
        }

        class MyComponent extends Component {
            render() {
                return null;
            }
        }

        function myFunction(x: number): number {
            return x * 2;
        }

        const arrowFn = (y: number) => y + 1;
    """)


@pytest.fixture
def sample_go_code():
    return textwrap.dedent("""\
        package main

        import "fmt"
        import "strings"

        type MyStruct struct {
            Field int
        }

        type MyInterface interface {
            DoThing() error
        }

        func MyFunction(x int) int {
            return x + 1
        }

        func (s *MyStruct) Method() error {
            fmt.Println(s.Field)
            return nil
        }
    """)


@pytest.fixture
def sample_project(tmp_path):
    """Create a mini project with multiple language files."""
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from utils import helper
        import os

        class App:
            def run(self):
                helper()
                os.getcwd()

        def helper():
            pass
    """), encoding="utf-8")

    (tmp_path / "utils.py").write_text(textwrap.dedent("""\
        def helper():
            return 42

        def other():
            helper()
    """), encoding="utf-8")

    (tmp_path / "lib.rs").write_text(textwrap.dedent("""\
        use std::io::Read;

        pub struct Library {
            data: Vec<u8>,
        }

        impl Library {
            pub fn new() -> Self {
                Self { data: vec![] }
            }
        }

        fn init() -> Library {
            Library::new()
        }
    """), encoding="utf-8")

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.js").write_text("function skipped() {}", encoding="utf-8")

    return tmp_path


# ── Helper Function Tests ───────────────────────────────────────


class TestHelpers:
    def test_hash_content(self):
        h = _hash_content("hello")
        assert len(h) == 64
        assert h == _hash_content("hello")
        assert h != _hash_content("world")

    def test_make_node_id(self):
        assert _make_node_id("file.py", "foo", "function") == "file.py::foo"
        assert _make_node_id("file.py", "", "file") == "file.py"

    def test_make_edge_id(self):
        eid = _make_edge_id("a", "b", "calls")
        assert eid == "a->b:calls"


# ── Dataclass Tests ─────────────────────────────────────────────


class TestDataclasses:
    def test_code_node_to_dict(self):
        node = CodeNode(
            id="file.py::foo",
            node_type="function",
            name="foo",
            file_path="file.py",
            line_start=1,
            line_end=10,
            language="python",
        )
        d = node.to_dict()
        assert d["id"] == "file.py::foo"
        assert d["node_type"] == "function"
        assert d["name"] == "foo"

    def test_code_edge_to_dict(self):
        edge = CodeEdge(
            id="a->b:calls",
            source_id="a",
            target_id="b",
            edge_type="calls",
            confidence="EXTRACTED",
        )
        d = edge.to_dict()
        assert d["edge_type"] == "calls"
        assert d["confidence"] == "EXTRACTED"
        assert "created_at" in d


# ── Python AST Extraction Tests ─────────────────────────────────


class TestPythonExtraction:
    def test_extracts_functions(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        func_names = {n.name for n in nodes if n.node_type == "function"}
        assert "standalone_function" in func_names
        assert "caller_function" in func_names
        assert "render" in func_names
        assert "fetch_data" in func_names

    def test_extracts_classes(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        class_names = {n.name for n in nodes if n.node_type == "class"}
        assert "BaseWidget" in class_names
        assert "MyWidget" in class_names

    def test_extracts_file_node(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        file_nodes = [n for n in nodes if n.node_type == "file"]
        assert len(file_nodes) == 1
        assert file_nodes[0].name == "test.py"

    def test_extracts_defines_edges(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        defines = [e for e in edges if e.edge_type == "defines"]
        assert len(defines) >= 5  # file defines functions + classes

    def test_extracts_inherits_edges(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        inherits = [e for e in edges if e.edge_type == "inherits"]
        assert len(inherits) >= 1
        # MyWidget inherits from BaseWidget
        inherit_targets = [e.metadata.get("base") for e in inherits]
        assert "BaseWidget" in inherit_targets

    def test_extracts_imports(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        imports = [e for e in edges if e.edge_type == "imports"]
        assert len(imports) >= 3  # os, pathlib.Path, json
        import_targets = [e.metadata.get("module", "") + "." + e.metadata.get("name", "") for e in imports]
        assert any("os" in t for t in import_targets)
        assert any("pathlib" in t for t in import_targets)

    def test_extracts_calls(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        calls = [e for e in edges if e.edge_type == "calls"]
        # caller_function calls standalone_function, MyWidget, widget.render
        assert len(calls) >= 2

    def test_async_function_metadata(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        async_funcs = [n for n in nodes if n.node_type == "function" and n.metadata.get("is_async")]
        assert len(async_funcs) == 1
        assert async_funcs[0].name == "fetch_data"

    def test_line_numbers(self, graph, sample_python_code):
        nodes, edges = graph._extract_python("test.py", sample_python_code, _hash_content(sample_python_code))
        for node in nodes:
            if node.name == "standalone_function":
                assert node.line_start > 0
                assert node.line_end >= node.line_start
                break

    def test_syntax_error_handling(self, graph):
        nodes, edges = graph._extract_python("bad.py", "def broken(:", _hash_content("def broken(:"))
        # Should still get the file node
        assert len(nodes) == 1
        assert nodes[0].node_type == "file"
        assert len(edges) == 0


# ── Regex Extraction Tests ──────────────────────────────────────


class TestRegexExtraction:
    def test_rust_extraction(self, graph, sample_rust_code):
        nodes, edges = graph._extract_regex("lib.rs", sample_rust_code, "rust", _hash_content(sample_rust_code))
        names = {n.name for n in nodes}
        assert "MyStruct" in names
        assert "MyTrait" in names
        assert "helper_function" in names
        # Check for use/import edges
        imports = [e for e in edges if e.edge_type == "imports"]
        assert len(imports) >= 2

    def test_typescript_extraction(self, graph, sample_typescript_code):
        nodes, edges = graph._extract_regex("app.ts", sample_typescript_code, "typescript", _hash_content(sample_typescript_code))
        names = {n.name for n in nodes}
        assert "MyComponent" in names
        assert "MyInterface" in names
        assert "myFunction" in names
        assert "arrowFn" in names

    def test_go_extraction(self, graph, sample_go_code):
        nodes, edges = graph._extract_regex("main.go", sample_go_code, "go", _hash_content(sample_go_code))
        names = {n.name for n in nodes}
        assert "MyStruct" in names
        assert "MyInterface" in names
        assert "MyFunction" in names
        assert "Method" in names

    def test_file_node_always_created(self, graph):
        nodes, edges = graph._extract_regex("empty.rs", "", "rust", _hash_content(""))
        assert len(nodes) == 1
        assert nodes[0].node_type == "file"


# ── Build + Persistence Tests ───────────────────────────────────


class TestBuildAndPersistence:
    def test_build_creates_graph(self, graph, sample_project):
        result = graph.build(sample_project, incremental=False)
        assert result["status"] == "success"
        assert result["node_count"] > 0
        assert result["edge_count"] > 0
        assert result["files_processed"] >= 3  # main.py, utils.py, lib.rs
        assert result["parser"] == "python-ast-regex"

    def test_build_skips_node_modules(self, graph, sample_project):
        graph.build(sample_project, incremental=False)
        # node_modules/skip.js should be skipped
        node_files = {n.file_path for n in graph._nodes.values()}
        assert not any("node_modules" in f for f in node_files)

    def test_persistence_roundtrip(self, graph, sample_project, tmp_db):
        graph.build(sample_project, incremental=False)
        # Create new instance pointing to same DB
        graph2 = CodeStructureGraph(db_path=tmp_db)
        graph2._load_from_db()
        assert len(graph2._nodes) == len(graph._nodes)
        assert len(graph2._edges) == len(graph._edges)

    def test_incremental_skips_unchanged(self, graph, sample_project):
        # First build
        result1 = graph.build(sample_project, incremental=True)
        assert result1["files_processed"] >= 3

        # Second build — all files unchanged
        result2 = graph.build(sample_project, incremental=True)
        assert result2["files_skipped"] >= 3
        assert result2["files_processed"] == 0

    def test_incremental_reparses_changed(self, graph, sample_project):
        # First build
        graph.build(sample_project, incremental=True)

        # Modify a file
        (sample_project / "main.py").write_text(
            "def new_function():\n    pass\n", encoding="utf-8"
        )

        # Second build — only main.py should be reprocessed
        result2 = graph.build(sample_project, incremental=True)
        assert result2["files_processed"] >= 1

    def test_stats(self, graph, sample_project):
        graph.build(sample_project, incremental=False)
        stats = graph.stats()
        assert stats["node_count"] > 0
        assert stats["edge_count"] > 0
        assert "function" in stats["node_types"]
        assert "defines" in stats["edge_types"]
        assert stats["project_root"] != ""

    def test_db_schema_created(self, tmp_db):
        CodeStructureGraph(db_path=tmp_db)
        import sqlite3
        with sqlite3.connect(tmp_db) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "code_nodes" in tables
        assert "code_edges" in tables
        assert "code_graph_meta" in tables


# ── Query Operation Tests ───────────────────────────────────────


class TestQueryOperations:
    @pytest.fixture
    def built_graph(self, graph, sample_project):
        graph.build(sample_project, incremental=False)
        return graph

    def test_explain(self, built_graph):
        result = built_graph.explain("helper")
        assert result["status"] == "success"
        assert "degree" in result
        assert "in_degree" in result
        assert "out_degree" in result

    def test_explain_not_found(self, built_graph):
        result = built_graph.explain("nonexistent_symbol")
        assert result["status"] == "error"

    def test_god_nodes(self, built_graph):
        result = built_graph.god_nodes(limit=5)
        assert len(result) > 0
        assert "degree" in result[0]
        assert result[0]["degree"] >= result[-1]["degree"]  # sorted descending

    def test_communities(self, built_graph):
        result = built_graph.communities()
        assert isinstance(result, list)
        # At least one community should exist if there are edges
        if built_graph._edges:
            assert len(result) >= 1

    def test_subgraph(self, built_graph):
        result = built_graph.subgraph("helper", depth=2)
        assert result["status"] == "success"
        assert result["node_count"] >= 1

    def test_path_same_node(self, built_graph):
        result = built_graph.path("helper", "helper")
        assert result["status"] == "success"
        assert result["hops"] == 0

    def test_path_not_found(self, built_graph):
        result = built_graph.path("helper", "nonexistent")
        assert result["status"] == "error"

    def test_query_explain_pattern(self, built_graph):
        result = built_graph.query("explain helper")
        assert result["status"] == "success"

    def test_query_communities_pattern(self, built_graph):
        result = built_graph.query("what communities exist")
        assert "communities" in result

    def test_query_god_nodes_pattern(self, built_graph):
        result = built_graph.query("what are the god nodes")
        assert "god_nodes" in result

    def test_query_search_fallback(self, built_graph):
        result = built_graph.query("helper")
        assert result["status"] == "success"
        assert "results" in result


# ── Export/Import Tests ─────────────────────────────────────────


class TestExportImport:
    @pytest.fixture
    def built_graph(self, graph, sample_project):
        graph.build(sample_project, incremental=False)
        return graph

    def test_export_json(self, built_graph, tmp_path):
        out = tmp_path / "graph.json"
        result = built_graph.export_json(out)
        assert result["status"] == "success"
        assert result["node_count"] > 0
        data = json.loads(out.read_text())
        assert "nodes" in data
        assert "edges" in data
        assert data["version"] == "1.0"

    def test_import_json(self, graph, tmp_path):
        # Create a simple graph.json
        graph_data = {
            "version": "1.0",
            "generator": "test",
            "project_root": "/test",
            "nodes": [
                {"id": "a.py::foo", "type": "function", "name": "foo", "file": "a.py", "line_start": 1, "line_end": 5, "language": "python"},
                {"id": "a.py::bar", "type": "function", "name": "bar", "file": "a.py", "line_start": 6, "line_end": 10, "language": "python"},
            ],
            "edges": [
                {"source": "a.py::foo", "target": "a.py::bar", "type": "calls", "confidence": "EXTRACTED"},
            ],
        }
        json_file = tmp_path / "import.json"
        json_file.write_text(json.dumps(graph_data))
        result = graph.import_json(json_file)
        assert result["status"] == "success"
        assert result["node_count"] == 2
        assert result["edge_count"] == 1


# ── Singleton Tests ─────────────────────────────────────────────


class TestSingleton:
    def test_get_code_structure_graph(self, tmp_db):
        # Reset singleton
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        g = get_code_structure_graph(db_path=tmp_db)
        assert g is not None
        g2 = get_code_structure_graph()
        assert g is g2
        # Cleanup
        mod._graph = None


# ── Phase 3: GraphEngine Integration Tests ──────────────────────


class TestGraphEngineIntegration:
    @pytest.fixture
    def built_graph(self, graph, sample_project):
        graph.build(sample_project, incremental=False)
        return graph

    def test_inject_into_graph_engine(self, built_graph):
        """Test injecting code nodes/edges into a networkx graph."""
        import networkx as nx
        # Simulate a GraphEngine-like object
        class FakeEngine:
            _graph = nx.DiGraph()
        fake = FakeEngine()
        # Add a pre-existing node to test enrichment
        fake._graph.add_node("test_node", type="memory")
        result = built_graph.inject_into_graph_engine(fake)
        assert result["status"] == "success"
        assert result["injected_nodes"] > 0
        assert result["injected_edges"] > 0
        assert fake._graph.number_of_nodes() > result["injected_nodes"]
        # Check code metadata was added
        for nid in built_graph._nodes:
            if fake._graph.has_node(nid):
                assert fake._graph.nodes[nid].get("graph_source") == "code"
                break

    def test_inject_no_graph(self, built_graph):
        class FakeEngine:
            _graph = None
        result = built_graph.inject_into_graph_engine(FakeEngine())
        assert result["status"] == "error"

    def test_unified_centrality(self, built_graph):
        """Test unified centrality computation."""
        import networkx as nx
        class FakeEngine:
            _graph = nx.DiGraph()
        fake = FakeEngine()
        built_graph.inject_into_graph_engine(fake)
        result = built_graph.unified_centrality(fake, limit=5)
        assert result["status"] == "success"
        assert "top_symbols" in result
        assert len(result["top_symbols"]) <= 5
        if result["top_symbols"]:
            assert "unified_score" in result["top_symbols"][0]
            assert "code_degree" in result["top_symbols"][0]

    def test_link_memory(self, built_graph):
        """Test creating discussed_in edges."""
        # Find a real symbol
        node_names = [n.name for n in built_graph._nodes.values() if n.node_type == "function"]
        assert len(node_names) > 0
        symbol = node_names[0]

        result = built_graph.link_memory(symbol, "mem-123", context="bug fix")
        assert result["status"] == "success"
        assert result["symbol"] == symbol
        assert result["memory_id"] == "mem-123"

        # Verify edge exists
        discussed = [e for e in built_graph._edges.values() if e.edge_type == "discussed_in"]
        assert len(discussed) >= 1

    def test_link_memory_not_found(self, built_graph):
        result = built_graph.link_memory("nonexistent_xyz", "mem-123")
        assert result["status"] == "error"

    def test_memories_for_symbol(self, built_graph):
        """Test retrieving memories linked to a symbol."""
        node_names = [n.name for n in built_graph._nodes.values() if n.node_type == "function"]
        symbol = node_names[0]
        built_graph.link_memory(symbol, "mem-abc", context="design discussion")
        built_graph.link_memory(symbol, "mem-def", context="refactor")

        result = built_graph.memories_for_symbol(symbol)
        assert result["status"] == "success"
        assert result["memory_count"] >= 2
        mem_ids = [m["memory_id"] for m in result["memories"]]
        assert "mem-abc" in mem_ids
        assert "mem-def" in mem_ids

    def test_memories_for_symbol_not_found(self, built_graph):
        result = built_graph.memories_for_symbol("nonexistent_xyz")
        assert result["status"] == "error"

    def test_discussed_in_persisted(self, built_graph, tmp_db):
        """Test that discussed_in edges persist to SQLite."""
        node_names = [n.name for n in built_graph._nodes.values() if n.node_type == "function"]
        symbol = node_names[0]
        built_graph.link_memory(symbol, "mem-persist-test")

        # Reload from DB
        graph2 = CodeStructureGraph(db_path=tmp_db)
        graph2._load_from_db()
        discussed = [e for e in graph2._edges.values() if e.edge_type == "discussed_in"]
        assert len(discussed) >= 1


# ── Phase 4: Agent Nudge Middleware Tests ───────────────────────


class TestCodeNudgeMiddleware:
    def test_nudge_disabled(self):
        """Test that nudge is skipped when WM_CODE_NUDGE=0."""
        import os
        os.environ["WM_CODE_NUDGE"] = "0"
        try:
            from whitemagic.tools.middleware import DispatchContext, mw_code_nudge

            called = [False]
            def next_fn(ctx):
                called[0] = True
                return {"status": "success"}

            ctx = DispatchContext(tool_name="strata.analyze", kwargs={})
            result = mw_code_nudge(ctx, next_fn)
            assert called[0] is True
            assert result == {"status": "success"}
        finally:
            del os.environ["WM_CODE_NUDGE"]

    def test_nudge_passes_through_non_target(self):
        """Test that nudge passes through for non-target tools."""
        import os
        os.environ.setdefault("WM_CODE_NUDGE", "1")
        try:
            from whitemagic.tools.middleware import DispatchContext, mw_code_nudge

            called = [False]
            def next_fn(ctx):
                called[0] = True
                return {"status": "success"}

            ctx = DispatchContext(tool_name="gnosis", kwargs={})
            result = mw_code_nudge(ctx, next_fn)
            assert called[0] is True
            assert result == {"status": "success"}
        finally:
            os.environ.pop("WM_CODE_NUDGE", None)

    def test_nudge_adds_suggestion_for_stale_graph(self):
        """Test that nudge adds a suggestion when code graph is stale."""
        import os

        # Reset singleton to ensure stale graph
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        os.environ["WM_CODE_GRAPH_DB"] = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_NUDGE"] = "1"
        try:
            import whitemagic.tools.middleware as mw_mod
            from whitemagic.tools.middleware import (
                DispatchContext,
                mw_code_nudge,
            )
            mw_mod._last_nudge_time = 0.0  # Reset cooldown

            def next_fn(ctx):
                return {"status": "success", "findings": []}

            ctx = DispatchContext(tool_name="strata.analyze", kwargs={})
            result = mw_code_nudge(ctx, next_fn)
            assert isinstance(result, dict)
            # Should have nudges since graph is empty
            if "_nudges" in result:
                assert any(n["type"] == "code_graph_stale" for n in result["_nudges"])
        finally:
            os.environ.pop("WM_CODE_NUDGE", None)
            os.environ.pop("WM_CODE_GRAPH_DB", None)
            mod._graph = None


# ── Phase 5: ContextEnricher Upgrade Tests ──────────────────────


class TestContextEnricherUpgrade:
    def test_context_enricher_fallback_without_graph(self, tmp_path):
        """Test that ContextEnricher falls back to AST when graph not built."""
        from whitemagic.tools.strata.context import ContextEnricher

        # Create a Python file
        py_file = tmp_path / "test.py"
        py_file.write_text(textwrap.dedent("""\
            def my_function():
                x = 1
                return x
        """), encoding="utf-8")

        # Reset singleton to ensure no graph
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None

        enricher = ContextEnricher(tmp_path)
        result = enricher.enrich("test.py", 2)
        assert result is not None
        assert "my_function" in result

    def test_context_enricher_uses_graph(self, tmp_path):
        """Test that ContextEnricher uses code graph when available."""
        import os
        import tempfile

        import whitemagic.core.intelligence.code_structure_graph as mod
        from whitemagic.tools.strata.context import ContextEnricher

        # Create a Python file
        py_file = tmp_path / "test.py"
        py_file.write_text(textwrap.dedent("""\
            class MyClass:
                def method_one(self):
                    return 42

                def method_two(self):
                    return 99
        """), encoding="utf-8")

        # Build code graph
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        mod._graph = None
        try:
            from whitemagic.core.intelligence.code_structure_graph import (
                get_code_structure_graph,
            )
            g = get_code_structure_graph()
            g.build(tmp_path, incremental=False)

            enricher = ContextEnricher(tmp_path)
            # Line 3 is inside method_one
            result = enricher.enrich("test.py", 3)
            assert result is not None
            assert "method_one" in result

            # Line 6 is inside method_two
            result2 = enricher.enrich("test.py", 6)
            assert result2 is not None
            assert "method_two" in result2
        finally:
            os.environ.pop("WM_CODE_GRAPH_DB", None)
            mod._graph = None
            if os.path.exists(db_path):
                os.unlink(db_path)


# ── Phase 6: Dream Cycle Integration Tests ──────────────────────


class TestDreamCycleCodeGraph:
    def test_dream_code_graph_skipped_no_graph(self):
        """Test that dream code_graph phase skips when graph not built."""
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        try:
            from whitemagic.core.dreaming.dream_cycle import DreamCycle
            dc = DreamCycle()
            result = dc._dream_code_graph()
            assert result["skipped"] is True
            assert "reason" in result
        finally:
            mod._graph = None

    def test_dream_code_graph_with_built_graph(self, tmp_path):
        """Test that dream code_graph phase analyzes a built graph."""
        import os
        import tempfile

        import whitemagic.core.intelligence.code_structure_graph as mod

        # Create a project with some code
        (tmp_path / "app.py").write_text(textwrap.dedent("""\
            import os
            from utils import helper

            class App:
                def run(self):
                    helper()
                    os.getcwd()

            def helper():
                pass
        """), encoding="utf-8")

        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        mod._graph = None
        try:
            from whitemagic.core.intelligence.code_structure_graph import (
                get_code_structure_graph,
            )
            g = get_code_structure_graph()
            g.build(tmp_path, incremental=False)

            from whitemagic.core.dreaming.dream_cycle import DreamCycle
            dc = DreamCycle()
            result = dc._dream_code_graph()
            assert result["skipped"] is False
            assert result["node_count"] > 0
            assert result["edge_count"] > 0
            assert "hypotheses" in result
            assert "language_distribution" in result
            assert "python" in result["language_distribution"]
        finally:
            os.environ.pop("WM_CODE_GRAPH_DB", None)
            mod._graph = None
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_dream_phase_enum_has_code_graph(self):
        """Test that DreamPhase enum includes CODE_GRAPH."""
        from whitemagic.core.dreaming.dream_cycle import DreamPhase
        assert hasattr(DreamPhase, "CODE_GRAPH")
        assert DreamPhase.CODE_GRAPH.value == "code_graph"


# ── Phase 7: Cross-Repo + Graphify Compatibility Tests ──────────


class TestCrossRepoGraph:
    @pytest.fixture
    def repo_a(self, tmp_path):
        repo = tmp_path / "repo_a"
        repo.mkdir()
        (repo / "main.py").write_text(textwrap.dedent("""\
            from utils import helper

            class App:
                def run(self):
                    helper()

            def helper():
                pass
        """), encoding="utf-8")
        return repo

    @pytest.fixture
    def repo_b(self, tmp_path):
        repo = tmp_path / "repo_b"
        repo.mkdir()
        (repo / "lib.py").write_text(textwrap.dedent("""\
            import os

            class Library:
                def fetch(self):
                    os.getcwd()

            def init():
                return Library()
        """), encoding="utf-8")
        return repo

    def test_cross_repo_merge(self, repo_a, repo_b):
        """Test merging two repos into a cross-repo graph."""
        from whitemagic.core.intelligence.cross_repo_graph import CrossRepoGraph

        crg = CrossRepoGraph()
        r1 = crg.add_repo("repo_a", repo_a, incremental=False)
        assert r1["status"] == "success"
        assert r1["merged_nodes"] > 0

        r2 = crg.add_repo("repo_b", repo_b, incremental=False)
        assert r2["status"] == "success"
        assert r2["merged_nodes"] > 0

        stats = crg.stats()
        assert stats["repo_count"] == 2
        assert "repo_a" in stats["repos"]
        assert "repo_b" in stats["repos"]
        assert stats["node_count"] > r1["merged_nodes"]

    def test_cross_repo_prefixed_ids(self, repo_a):
        """Test that node IDs are repo-prefixed."""
        from whitemagic.core.intelligence.cross_repo_graph import CrossRepoGraph

        crg = CrossRepoGraph()
        crg.add_repo("myrepo", repo_a, incremental=False)

        for node_id in crg.merged_graph._nodes:
            if node_id != "myrepo:" and not node_id.startswith("module:"):
                assert node_id.startswith("myrepo:"), f"Node {node_id} not prefixed"

    def test_cross_repo_stats(self, repo_a, repo_b):
        """Test cross-repo stats include per-repo info."""
        from whitemagic.core.intelligence.cross_repo_graph import CrossRepoGraph

        crg = CrossRepoGraph()
        crg.add_repo("alpha", repo_a, incremental=False)
        crg.add_repo("beta", repo_b, incremental=False)

        stats = crg.stats()
        assert stats["repo_count"] == 2
        assert stats["repos"]["alpha"]["node_count"] > 0
        assert stats["repos"]["beta"]["node_count"] > 0

    def test_cross_repo_export(self, repo_a, tmp_path):
        """Test exporting cross-repo graph to JSON."""
        from whitemagic.core.intelligence.cross_repo_graph import CrossRepoGraph

        crg = CrossRepoGraph()
        crg.add_repo("myrepo", repo_a, incremental=False)

        out = tmp_path / "cross_repo.json"
        result = crg.export_json(out)
        assert result["status"] == "success"

        data = json.loads(out.read_text())
        assert data["version"] == "1.0"
        assert len(data["nodes"]) > 0


class TestGraphifyCompatibility:
    def test_graphify_format_export(self, graph, sample_project, tmp_path):
        """Test that export produces Graphify-compatible format."""
        graph.build(sample_project, incremental=False)
        out = tmp_path / "graph.json"
        result = graph.export_json(out)
        assert result["status"] == "success"

        data = json.loads(out.read_text())
        # Graphify format: version, generator, nodes, edges
        assert data["version"] == "1.0"
        assert "generator" in data
        assert "nodes" in data
        assert "edges" in data
        # Each node should have id, type, name, file
        for node in data["nodes"][:5]:
            assert "id" in node
            assert "type" in node
            assert "name" in node
            assert "file" in node

    def test_graphify_format_import(self, graph, tmp_path):
        """Test importing a Graphify-format graph.json."""
        graphify_data = {
            "version": "1.0",
            "generator": "graphify",
            "project_root": "/test",
            "nodes": [
                {"id": "test.py::foo", "type": "function", "name": "foo", "file": "test.py", "line_start": 1, "line_end": 5, "language": "python"},
                {"id": "test.py::bar", "type": "function", "name": "bar", "file": "test.py", "line_start": 6, "line_end": 10, "language": "python"},
                {"id": "test.py", "type": "file", "name": "test.py", "file": "test.py", "line_start": 1, "line_end": 10, "language": "python"},
            ],
            "edges": [
                {"source": "test.py", "target": "test.py::foo", "type": "defines", "confidence": "EXTRACTED"},
                {"source": "test.py", "target": "test.py::bar", "type": "defines", "confidence": "EXTRACTED"},
                {"source": "test.py::foo", "target": "test.py::bar", "type": "calls", "confidence": "EXTRACTED"},
            ],
        }
        json_file = tmp_path / "graphify_import.json"
        json_file.write_text(json.dumps(graphify_data))

        result = graph.import_json(json_file)
        assert result["status"] == "success"
        assert result["node_count"] == 3
        assert result["edge_count"] == 3

        # Verify nodes are queryable
        explain = graph.explain("foo")
        assert explain["status"] == "success"

    def test_code_import_handler(self, graph, tmp_path):
        """Test the code.import MCP handler."""
        graphify_data = {
            "version": "1.0",
            "generator": "test",
            "project_root": "/test",
            "nodes": [
                {"id": "a.py::func", "type": "function", "name": "func", "file": "a.py", "line_start": 1, "line_end": 3, "language": "python"},
            ],
            "edges": [],
        }
        json_file = tmp_path / "import_test.json"
        json_file.write_text(json.dumps(graphify_data))

        from whitemagic.tools.handlers.code_graph import handle_code_import
        result = handle_code_import(path=str(json_file))
        assert result["status"] == "success"
        assert result["node_count"] == 1


# ── Gap-Fill Tests: affected_by, correlate, diff_graphs, checkers ──


class TestAffectedBy:
    def _setup_graph(self, project_path):
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        import os
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        g = mod.get_code_structure_graph()
        g.build(project_path, incremental=False)
        return g, db_path

    def _teardown_graph(self, db_path):
        import os

        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        os.environ.pop("WM_CODE_GRAPH_DB", None)
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_affected_by_finds_callers(self, sample_project):
        """Test that affected_by finds symbols that call the target."""
        g, db_path = self._setup_graph(sample_project)
        try:
            result = g.affected_by("helper", max_depth=3)
            assert result["status"] == "success"
            assert result["total_affected"] > 0
            found = False
            for hop_nodes in result["by_hop"].values():
                for n in hop_nodes:
                    if n["name"] == "run":
                        found = True
                        break
            assert found, "run should be affected by changes to helper"
        finally:
            self._teardown_graph(db_path)

    def test_affected_by_symbol_not_found(self):
        """Test affected_by returns error for unknown symbol."""
        g, db_path = self._setup_graph(Path(tempfile.mkdtemp()))
        try:
            result = g.affected_by("nonexistent_symbol")
            assert result["status"] == "error"
        finally:
            self._teardown_graph(db_path)

    def test_affected_by_handler(self, sample_project):
        """Test the code.affected_by MCP handler."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.handlers.code_graph import handle_code_affected_by
            result = handle_code_affected_by(symbol="helper", max_depth=2)
            assert result["status"] == "success"
            assert result["total_affected"] >= 0
        finally:
            self._teardown_graph(db_path)


class TestCorrelateMemories:
    def _setup_graph(self, project_path):
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        import os
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        g = mod.get_code_structure_graph()
        g.build(project_path, incremental=False)
        return g, db_path

    def _teardown_graph(self, db_path):
        import os

        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        os.environ.pop("WM_CODE_GRAPH_DB", None)
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_correlate_memories_no_linked(self, sample_project):
        """Test correlate_memories when no memories are linked."""
        g, db_path = self._setup_graph(sample_project)
        try:
            result = g.correlate_memories("helper")
            assert result["status"] == "success"
            assert result["linked_count"] == 0
            assert isinstance(result["semantic_matches"], list)
        finally:
            self._teardown_graph(db_path)

    def test_correlate_with_linked_memory(self, sample_project):
        """Test correlate_memories with a linked memory."""
        g, db_path = self._setup_graph(sample_project)
        try:
            g.link_memory("helper", "mem-001", context="discusses helper function")
            result = g.correlate_memories("helper")
            assert result["status"] == "success"
            assert result["linked_count"] == 1
            assert result["linked_memories"][0]["memory_id"] == "mem-001"
        finally:
            self._teardown_graph(db_path)

    def test_correlate_handler(self, sample_project):
        """Test the code.correlate MCP handler."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.handlers.code_graph import handle_code_correlate
            result = handle_code_correlate(symbol="helper")
            assert result["status"] == "success"
        finally:
            self._teardown_graph(db_path)


class TestDiffGraphs:
    def test_diff_graphs_empty_old(self, graph, sample_project):
        """Test diff_graphs with no old graph (everything is 'added')."""
        graph.build(sample_project, incremental=False)
        # Don't persist, so diff against empty old
        result = graph.diff_graphs(old_graph={"nodes": [], "edges": []})
        assert result["status"] == "success"
        assert result["summary"]["nodes_added"] > 0

    def test_diff_graphs_no_changes(self, graph, sample_project):
        """Test diff_graphs when old and current are identical."""
        graph.build(sample_project, incremental=False)
        # Export current as old
        current_nodes = {n_id: n.to_dict() for n_id, n in graph._nodes.items()}
        current_edges = {e_id: e.to_dict() for e_id, e in graph._edges.items()}
        old = {"nodes": list(current_nodes.values()), "edges": list(current_edges.values())}
        result = graph.diff_graphs(old_graph=old)
        assert result["status"] == "success"
        assert result["summary"]["nodes_added"] == 0
        assert result["summary"]["nodes_removed"] == 0

    def test_diff_graphs_added_node(self, graph, sample_project):
        """Test diff_graphs detects added nodes."""
        graph.build(sample_project, incremental=False)
        old = {"nodes": [], "edges": []}
        result = graph.diff_graphs(old_graph=old)
        assert result["summary"]["nodes_added"] == len(graph._nodes)


class TestGraphAnomalyChecker:
    def _setup_graph(self, project_path):
        """Build code graph and set as singleton for checker access."""
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        import os
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        g = mod.get_code_structure_graph()
        g.build(project_path, incremental=False)
        return g, db_path

    def _teardown_graph(self, db_path):
        import os

        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        os.environ.pop("WM_CODE_GRAPH_DB", None)
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_god_class_checker(self, sample_project):
        """Test that god class checker runs without errors."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.strata.checkers.graph_anomaly import check_god_classes
            from whitemagic.tools.strata.file_index import FileIndex
            from whitemagic.tools.strata.models import Finding

            fi = FileIndex(sample_project)
            findings: list[Finding] = []
            check_god_classes(sample_project, fi, findings)
            assert isinstance(findings, list)
        finally:
            self._teardown_graph(db_path)

    def test_circular_dependency_checker(self, sample_project):
        """Test that circular dependency checker runs without errors."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.strata.checkers.graph_anomaly import (
                check_circular_dependencies,
            )
            from whitemagic.tools.strata.file_index import FileIndex
            from whitemagic.tools.strata.models import Finding

            fi = FileIndex(sample_project)
            findings: list[Finding] = []
            check_circular_dependencies(sample_project, fi, findings)
            assert isinstance(findings, list)
        finally:
            self._teardown_graph(db_path)

    def test_dead_code_checker(self, sample_project):
        """Test that dead code checker runs without errors."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.strata.checkers.graph_anomaly import check_dead_code
            from whitemagic.tools.strata.file_index import FileIndex
            from whitemagic.tools.strata.models import Finding

            fi = FileIndex(sample_project)
            findings: list[Finding] = []
            check_dead_code(sample_project, fi, findings)
            assert isinstance(findings, list)
        finally:
            self._teardown_graph(db_path)

    def test_bridge_module_checker(self, sample_project):
        """Test that bridge module checker runs without errors."""
        g, db_path = self._setup_graph(sample_project)
        try:
            from whitemagic.tools.strata.checkers.graph_anomaly import (
                check_bridge_modules,
            )
            from whitemagic.tools.strata.file_index import FileIndex
            from whitemagic.tools.strata.models import Finding

            fi = FileIndex(sample_project)
            findings: list[Finding] = []
            check_bridge_modules(sample_project, fi, findings)
            assert isinstance(findings, list)
        finally:
            self._teardown_graph(db_path)

    def test_god_class_detects_high_degree(self, tmp_path):
        """Test that god class checker detects a node with very high degree."""
        code = "def target():\n    pass\n\n"
        for i in range(20):
            code += f"def caller_{i}():\n    target()\n\n"
        (tmp_path / "god.py").write_text(code, encoding="utf-8")
        g, db_path = self._setup_graph(tmp_path)
        try:
            from whitemagic.tools.strata.checkers.graph_anomaly import check_god_classes
            from whitemagic.tools.strata.file_index import FileIndex
            from whitemagic.tools.strata.models import Finding

            fi = FileIndex(tmp_path)
            findings: list[Finding] = []
            check_god_classes(tmp_path, fi, findings)
            assert len(findings) > 0
            assert any("target" in f.message for f in findings)
        finally:
            self._teardown_graph(db_path)


class TestDataFlowTaintChecker:
    def test_taint_checker_runs(self, tmp_path):
        """Test that data flow taint checker runs without errors."""
        from whitemagic.tools.strata.checkers.data_flow_taint import (
            check_data_flow_taint,
        )
        from whitemagic.tools.strata.file_index import FileIndex
        from whitemagic.tools.strata.models import Finding

        (tmp_path / "safe.py").write_text(
            "import html\n\ndef handler(request):\n"
            "    name = request.get('name', '')\n"
            "    safe_name = html.escape(name)\n"
            "    return safe_name\n",
            encoding="utf-8",
        )
        fi = FileIndex(tmp_path)
        findings: list[Finding] = []
        check_data_flow_taint(tmp_path, fi, findings)
        assert isinstance(findings, list)

    def test_taint_detects_unsanitized_sql(self, tmp_path):
        """Test that taint checker detects unsanitized SQL injection."""
        from whitemagic.tools.strata.checkers.data_flow_taint import (
            check_data_flow_taint,
        )
        from whitemagic.tools.strata.file_index import FileIndex
        from whitemagic.tools.strata.models import Finding

        (tmp_path / "vuln.py").write_text(
            "def handler(request):\n"
            "    user_input = request.GET.get('id', '')\n"
            "    cursor.execute('SELECT * FROM users WHERE id = ' + user_input)\n",
            encoding="utf-8",
        )
        fi = FileIndex(tmp_path)
        findings: list[Finding] = []
        check_data_flow_taint(tmp_path, fi, findings)
        assert len(findings) > 0
        assert any("SQL" in f.message or "taint" in f.message.lower() for f in findings)


class TestPhylogeneticsCodeLineage:
    def test_record_code_lineage(self):
        """Test recording cross-repo code lineage."""
        from whitemagic.core.memory.phylogenetics import PhylogeneticTracker
        tracker = PhylogeneticTracker()
        edge = tracker.record_code_lineage(
            source_symbol="helper_func",
            source_repo="repo_a",
            target_symbol="helper_func",
            target_repo="repo_b",
            lineage_type="copy",
        )
        assert edge is not None
        assert edge.edge_type == "code_lineage"
        assert edge.mechanism == "copy"


class TestKGIntegration:
    def test_ingest_code_symbols_empty(self):
        """Test KG ingest with empty code graph."""
        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        try:
            from whitemagic.core.intelligence.knowledge_graph_v2 import KnowledgeGraphV2
            kg = KnowledgeGraphV2()
            result = kg.ingest_code_symbols()
            assert result["status"] in ("skipped", "error")
        finally:
            mod._graph = None

    def test_ingest_code_symbols_with_graph(self, sample_project):
        """Test KG ingest with a built code graph."""
        import os
        import tempfile

        import whitemagic.core.intelligence.code_structure_graph as mod
        mod._graph = None
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["WM_CODE_GRAPH_DB"] = db_path
        try:
            g = mod.get_code_structure_graph()
            g.build(sample_project, incremental=False)
            from whitemagic.core.intelligence.knowledge_graph_v2 import KnowledgeGraphV2
            kg = KnowledgeGraphV2()
            result = kg.ingest_code_symbols()
            assert result["status"] == "success"
            assert result["entities_added"] > 0
        finally:
            mod._graph = None
            os.environ.pop("WM_CODE_GRAPH_DB", None)
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestNLURouting:
    def test_nlu_routes_code_graph_build(self):
        """Test NLU routing for 'build code graph'."""

        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        for pattern, gana, tool in _ROUTING_PATTERNS:
            if tool == "code.graph":
                assert pattern.search("build code graph for this project")
                break

    def test_nlu_routes_code_query(self):
        """Test NLU routing for 'code query'."""
        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        for pattern, gana, tool in _ROUTING_PATTERNS:
            if tool == "code.query":
                assert pattern.search("code query what calls helper")
                break

    def test_nlu_routes_code_affected_by(self):
        """Test NLU routing for 'code affected by'."""
        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        for pattern, gana, tool in _ROUTING_PATTERNS:
            if tool == "code.affected_by":
                assert pattern.search("code affected by change to helper")
                break

    def test_nlu_routes_code_correlate(self):
        """Test NLU routing for 'code correlate'."""
        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        for pattern, gana, tool in _ROUTING_PATTERNS:
            if tool == "code.correlate":
                assert pattern.search("code correlate memory with helper")
                break

    def test_nlu_routes_code_cross_repo(self):
        """Test NLU routing for 'code cross repo query'."""
        from whitemagic.tools.handlers.meta_tool import _ROUTING_PATTERNS
        for pattern, gana, tool in _ROUTING_PATTERNS:
            if tool == "code.cross_repo_query":
                assert pattern.search("cross repo query for helper")
                break


class TestNudgeExtended:
    def test_nudge_fires_on_codebase_recall(self):
        """Test that nudge middleware fires on codebase.recall."""
        from whitemagic.tools.middleware import _CODE_NUDGE_TOOLS
        assert "codebase.recall" in _CODE_NUDGE_TOOLS

    def test_nudge_fires_on_fragment_search(self):
        """Test that nudge middleware fires on fragment.search."""
        from whitemagic.tools.middleware import _CODE_NUDGE_TOOLS
        assert "fragment.search" in _CODE_NUDGE_TOOLS


class TestCrossRepoQueryHandler:
    def test_cross_repo_query_handler(self):
        """Test the code.cross_repo_query MCP handler."""
        from whitemagic.tools.handlers.code_graph import handle_code_cross_repo_query

        # This handler creates a fresh CrossRepoGraph (empty), so just verify it doesn't crash
        result = handle_code_cross_repo_query(query="helper")
        assert "status" in result

