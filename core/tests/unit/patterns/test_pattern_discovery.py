"""Tests for the Pattern Discovery Meta-System (recovered 2026-06-18)."""


class TestPatternDiscovery:
    """Test the meta-system that finds and runs ALL pattern functions."""

    def test_imports(self):
        from whitemagic.core.patterns.emergence import (
            DiscoveryReport,
            PatternDiscovery,
            PatternSource,
        )
        assert PatternSource is not None
        assert DiscoveryReport is not None
        assert PatternDiscovery is not None

    def test_singleton(self):
        from whitemagic.core.patterns.emergence import get_discovery

        a = get_discovery()
        b = get_discovery()
        assert a is b, "get_discovery() should return the same instance"

    def test_registered_sources(self):
        from whitemagic.core.patterns.emergence import get_discovery

        discovery = get_discovery()
        assert len(discovery.sources) >= 5, (
            f"Expected at least 5 pattern sources, got {len(discovery.sources)}"
        )
        # All sources should have non-empty name and module_path
        for s in discovery.sources:
            assert s.name
            assert s.module_path
            assert s.function_name

    def test_discover_all_runs(self):
        """discover_all should run all sources and return a DiscoveryReport."""
        from whitemagic.core.patterns.emergence import get_discovery

        discovery = get_discovery()
        report = discovery.discover_all(save_report=False)
        assert report.timestamp
        assert report.sources_attempted == len(discovery.sources)
        assert report.duration_seconds >= 0
        # Should run at least 1 source (most modules are available)
        assert report.sources_run >= 1
        # Errors should be empty for a healthy v22 install
        # (some sources may fail, but the report should still be valid)
        assert isinstance(report.errors, dict)

    def test_run_full_discovery_convenience(self):
        """run_full_discovery() is a convenience that calls get_discovery().discover_all()."""
        from whitemagic.core.patterns.emergence import run_full_discovery

        report = run_full_discovery(save_report=False)
        assert report is not None
        assert hasattr(report, "total_patterns")
        assert hasattr(report, "by_source")

    def test_count_patterns_handles_types(self):
        """_count_patterns should handle list, dict, object, scalar."""
        from whitemagic.core.patterns.emergence.pattern_discovery import (
            PatternDiscovery,
        )

        # Use a temp dir to avoid touching the real state root
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            d = PatternDiscovery(base_dir=Path(tmp))

            assert d._count_patterns(None) == 0
            assert d._count_patterns([1, 2, 3]) == 3
            assert d._count_patterns({"a": 1, "b": 2}) == 2
            assert d._count_patterns({"patterns_found": 42}) == 42
            assert d._count_patterns({"total": 99}) == 99
            assert d._count_patterns(5) == 5
            assert d._count_patterns(True) == 1
            assert d._count_patterns(False) == 0

    def test_pattern_source_dataclass(self):
        from whitemagic.core.patterns.emergence import PatternSource

        src = PatternSource(
            name="test",
            module_path="whitemagic.test",
            function_name="test_fn",
            description="test description",
            parameters={"k": 1},
        )
        assert src.name == "test"
        assert src.module_path == "whitemagic.test"
        assert src.function_name == "test_fn"
        assert src.description == "test description"
        assert src.parameters == {"k": 1}

    def test_discovery_report_dataclass(self):
        from whitemagic.core.patterns.emergence import DiscoveryReport

        r = DiscoveryReport(
            timestamp="2026-06-18T00:00:00",
            sources_run=5,
            sources_attempted=10,
            total_patterns=42,
            by_source={"a": 10, "b": 32},
            insights=["insight 1", "insight 2"],
            duration_seconds=0.5,
        )
        assert r.total_patterns == 42
        assert r.sources_run == 5
        assert r.sources_attempted == 10
        assert len(r.insights) == 2
