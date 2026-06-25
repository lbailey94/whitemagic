"""Unit tests for probabilistic data structures — HLL, Count-Min Sketch, MemoryAnalytics."""
from whitemagic.core.memory.probabilistic import (
    CountMinSketch,
    HyperLogLog,
    MemoryAnalytics,
)


class TestHyperLogLog:
    """Test HyperLogLog cardinality estimation."""

    def test_basic_estimation(self):
        hll = HyperLogLog(precision=12)
        for i in range(1000):
            hll.add(f"memory_{i}")
        estimate = hll.estimate()
        # Should be within ~10% of 1000
        assert abs(estimate - 1000) < 100, f"Estimate {estimate} too far from 1000"

    def test_empty_estimate(self):
        hll = HyperLogLog(precision=10)
        est = hll.estimate()
        assert est >= 0

    def test_duplicates_ignored(self):
        hll = HyperLogLog(precision=12)
        for _ in range(100):
            hll.add("same_key")
        estimate = hll.estimate()
        # Should be close to 1
        assert estimate < 5, f"Expected ~1, got {estimate}"

    def test_large_cardinality(self):
        hll = HyperLogLog(precision=14)
        for i in range(10000):
            hll.add(f"item_{i}")
        estimate = hll.estimate()
        # Within ~5% for 10K with p=14
        assert abs(estimate - 10000) / 10000 < 0.10, f"Estimate {estimate} too far from 10000"

    def test_merge(self):
        hll1 = HyperLogLog(precision=12)
        hll2 = HyperLogLog(precision=12)
        for i in range(500):
            hll1.add(f"item_{i}")
        for i in range(500, 1000):
            hll2.add(f"item_{i}")
        hll1.merge(hll2)
        estimate = hll1.estimate()
        assert abs(estimate - 1000) < 150, f"Merged estimate {estimate} too far from 1000"

    def test_merge_different_precision_raises(self):
        hll1 = HyperLogLog(precision=10)
        hll2 = HyperLogLog(precision=12)
        try:
            hll1.merge(hll2)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_reset(self):
        hll = HyperLogLog(precision=10)
        hll.add("test")
        hll.reset()
        assert all(r == 0 for r in hll.registers)

    def test_memory_bytes(self):
        hll = HyperLogLog(precision=10)
        assert hll.memory_bytes() == 1024  # 2^10 = 1024 bytes

    def test_serialization_roundtrip(self):
        hll = HyperLogLog(precision=10)
        for i in range(100):
            hll.add(f"item_{i}")
        data = hll.to_dict()
        restored = HyperLogLog.from_dict(data)
        assert restored.precision == hll.precision
        assert restored.estimate() == hll.estimate()

    def test_invalid_precision(self):
        try:
            HyperLogLog(precision=3)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
        try:
            HyperLogLog(precision=17)
            assert False, "Should raise ValueError"
        except ValueError:
            pass


class TestCountMinSketch:
    """Test Count-Min Sketch frequency estimation."""

    def test_basic_count(self):
        cms = CountMinSketch(width=1024, depth=5)
        for _ in range(10):
            cms.add("apple")
        assert cms.estimate("apple") >= 10  # Over-estimate possible

    def test_no_underestimate(self):
        cms = CountMinSketch(width=1024, depth=5)
        for _ in range(50):
            cms.add("banana")
        # CMS never under-estimates
        assert cms.estimate("banana") >= 50

    def test_zero_for_unseen(self):
        cms = CountMinSketch(width=1024, depth=5)
        assert cms.estimate("unseen") >= 0

    def test_multiple_elements(self):
        cms = CountMinSketch(width=2048, depth=7)
        for _ in range(100):
            cms.add("a")
        for _ in range(50):
            cms.add("b")
        for _ in range(25):
            cms.add("c")
        assert cms.estimate("a") >= 100
        assert cms.estimate("b") >= 50
        assert cms.estimate("c") >= 25

    def test_merge(self):
        cms1 = CountMinSketch(width=1024, depth=5)
        cms2 = CountMinSketch(width=1024, depth=5)
        for _ in range(10):
            cms1.add("shared")
        for _ in range(20):
            cms2.add("shared")
        cms1.merge(cms2)
        assert cms1.estimate("shared") >= 30

    def test_merge_different_dims_raises(self):
        cms1 = CountMinSketch(width=1024, depth=5)
        cms2 = CountMinSketch(width=2048, depth=5)
        try:
            cms1.merge(cms2)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_reset(self):
        cms = CountMinSketch(width=1024, depth=5)
        cms.add("test")
        cms.reset()
        assert cms.estimate("test") == 0
        assert cms.total == 0

    def test_memory_bytes(self):
        cms = CountMinSketch(width=1024, depth=5)
        assert cms.memory_bytes() == 1024 * 5 * 8

    def test_serialization_roundtrip(self):
        cms = CountMinSketch(width=512, depth=3)
        for _ in range(10):
            cms.add("test_item")
        data = cms.to_dict()
        restored = CountMinSketch.from_dict(data)
        assert restored.estimate("test_item") == cms.estimate("test_item")

    def test_count_increment(self):
        cms = CountMinSketch(width=1024, depth=5)
        cms.add("item", count=5)
        assert cms.estimate("item") >= 5
        assert cms.total == 5


class TestMemoryAnalytics:
    """Test the MemoryAnalytics aggregator."""

    def test_distinct_memory_count(self):
        analytics = MemoryAnalytics(hll_precision=12)
        for i in range(500):
            analytics.observe_memory(f"mem_{i}", tags=["test"], source="unit_test")
        estimate = analytics.estimate_distinct_count()
        assert abs(estimate - 500) < 75, f"Estimate {estimate} too far from 500"

    def test_tag_frequency(self):
        analytics = MemoryAnalytics(cms_width=2048, cms_depth=7)
        for _ in range(100):
            analytics.observe_memory("mem_1", tags=["important"])
        for _ in range(50):
            analytics.observe_memory("mem_2", tags=["casual"])
        assert analytics.estimate_tag_count("important") >= 100
        assert analytics.estimate_tag_count("casual") >= 50

    def test_source_frequency(self):
        analytics = MemoryAnalytics(cms_width=2048, cms_depth=7)
        for _ in range(30):
            analytics.observe_memory("mem_1", source="ollama")
        for _ in range(20):
            analytics.observe_memory("mem_2", source="user")
        assert analytics.estimate_source_count("ollama") >= 30
        assert analytics.estimate_source_count("user") >= 20

    def test_access_frequency(self):
        analytics = MemoryAnalytics(cms_width=2048, cms_depth=7)
        for _ in range(50):
            analytics.observe_access("hot_memory")
        assert analytics.estimate_access_count("hot_memory") >= 50

    def test_summary(self):
        analytics = MemoryAnalytics(hll_precision=10, cms_width=512, cms_depth=3)
        analytics.observe_memory("mem_1", tags=["a"], source="test")
        analytics.observe_access("mem_1")
        summary = analytics.summary()
        assert "distinct_memories" in summary
        assert "memory_bytes" in summary
        assert summary["memory_bytes"] > 0

    def test_memory_efficient(self):
        """Verify that analytics uses much less memory than storing all items."""
        analytics = MemoryAnalytics(hll_precision=14, cms_width=4096, cms_depth=5)
        # Simulate 100K memories
        for i in range(100_000):
            analytics.observe_memory(f"mem_{i}", tags=[f"tag_{i % 10}"], source="test")
        analytics_bytes = analytics.memory_bytes()
        # Should be well under 1MB (4 CMS instances + HLL = ~508KB)
        assert analytics_bytes < 600_000, f"Analytics using {analytics_bytes} bytes, expected < 600K"
        # Estimate should be reasonable
        est = analytics.estimate_distinct_count()
        assert abs(est - 100_000) / 100_000 < 0.10, f"Estimate {est} too far from 100K"
