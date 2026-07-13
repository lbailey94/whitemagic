"""Integration tests for P4 Research Systems: DiLoCo, Warp Marketplace, Mesh Inference Router.

Tests the end-to-end flow for all three P4 modules:
1. DiLoCo distributed training — init, register workers, submit gradients, sync
2. Warp marketplace — publish, discover, download, broadcast
3. Mesh inference router — register nodes, route requests, switch strategies
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

_tmpdir = tempfile.mkdtemp(prefix="wm_p4_")
os.environ.setdefault("WM_STATE_ROOT", _tmpdir)
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")


# ── DiLoCo Tests ──────────────────────────────────────────────────────────


class TestDiLoCo:
    """Tests for DiLoCo distributed training coordinator."""

    def test_init_and_status(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({
            "layer1.weight": [[0.1, 0.2], [0.3, 0.4]],
            "layer1.bias": [0.01, 0.02],
        })
        status = coordinator.get_status()
        assert status["param_count"] == 2
        assert status["h"] > 0
        assert status["sync_count"] == 0
        assert status["pending_gradients"] == 0

    def test_register_worker(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        result = coordinator.register_worker("test_worker_0", compute_capacity=2.0)
        assert result is True
        status = coordinator.get_status()
        assert status["pool"]["active_workers"] >= 1
        assert any(w["worker_id"] == "test_worker_0" for w in status["pool"]["workers"])

    def test_submit_gradient_and_sync(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({
            "layer1.weight": [[0.1, 0.2], [0.3, 0.4]],
        })
        coordinator.register_worker("sync_test_worker")

        gradients = {
            "layer1.weight": [[0.01, 0.02], [0.03, 0.04]],
        }
        result = coordinator.submit_gradient("sync_test_worker", gradients)
        assert result["status"] == "success"

        sync_result = coordinator.sync_step()
        assert sync_result["status"] == "success"
        assert sync_result["gradients_averaged"] == 1
        assert sync_result["sync_count"] >= 1

    def test_sparseloco_compression(self):
        from whitemagic.mesh.dilo_co import SparseLoCoCompressor

        compressor = SparseLoCoCompressor(k_ratio=0.1)
        gradients = {
            "layer1": np.random.randn(100).astype(np.float32),
        }
        compressed = compressor.compress(gradients)
        assert "layer1" in compressed
        assert len(compressed["layer1"]["indices"]) <= 10
        assert len(compressed["layer1"]["values"]) <= 10

        decompressed = compressor.decompress(compressed)
        assert decompressed["layer1"].shape == gradients["layer1"].shape

        stats = compressor.get_stats()
        assert stats["compress_count"] > 0
        assert stats["k_ratio"] == 0.1

    def test_sync_empty_pool(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({"dummy": [0.0]})
        result = coordinator.sync_step()
        assert result["status"] == "skipped"

    def test_param_hash_changes_after_sync(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({"weight": [1.0, 2.0, 3.0]})
        coordinator.register_worker("hash_test_worker")

        hash_before = coordinator.get_status()["param_hash"]
        coordinator.submit_gradient("hash_test_worker", {"weight": [0.1, 0.2, 0.3]})
        coordinator.sync_step()
        hash_after = coordinator.get_status()["param_hash"]
        assert hash_before != hash_after

    def test_multiple_workers_gradient_averaging(self):
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({"w": [0.0]})
        coordinator.register_worker("avg_w0")
        coordinator.register_worker("avg_w1")

        coordinator.submit_gradient("avg_w0", {"w": [1.0]})
        coordinator.submit_gradient("avg_w1", {"w": [3.0]})

        result = coordinator.sync_step()
        assert result["status"] == "success"
        assert result["gradients_averaged"] == 2

        params = coordinator.get_params()
        # avg gradient = (1+3)/2 = 2.0, param = 0 - lr_outer * 2.0
        assert abs(params["w"][0] - (-2.0)) < 0.01


# ── Warp Marketplace Tests ────────────────────────────────────────────────


class TestWarpMarketplace:
    """Tests for the P2P warp preset marketplace."""

    def test_publish_and_status(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {
            "name": "test_research_warp",
            "description": "A test warp for research",
            "tools_allowed": ["memory_create", "search"],
            "inference_tier": "local_small",
            "research_domains": ["cognitive"],
            "execution_mode": "autonomous",
        }
        result = mp.publish(
            warp_name="test_research_warp",
            warp_data=warp_data,
            author_id="test_agent",
            description="Test warp for integration testing",
        )
        assert result["status"] == "success"
        assert "listing_id" in result

        status = mp.get_status()
        assert status["total_listings"] >= 1
        assert "test_research_warp" in status["warp_names"]

    def test_discover(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        result = mp.discover(query="research")
        assert result["status"] == "success"
        assert result["total"] >= 1

        result2 = mp.discover(capability="memory_create")
        assert result2["status"] == "success"
        assert any("test_research_warp" in l["warp_name"] for l in result2["results"])

    def test_discover_by_inference_tier(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        result = mp.discover(inference_tier="local_small")
        assert result["status"] == "success"
        for listing in result["results"]:
            assert listing["inference_tier"] == "local_small"

    def test_download(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        # First publish
        warp_data = {
            "name": "downloadable_warp",
            "description": "A warp to download",
            "tools_allowed": ["gnosis"],
            "inference_tier": "edge",
        }
        pub_result = mp.publish(
            warp_name="downloadable_warp",
            warp_data=warp_data,
            author_id="test_agent",
        )
        assert pub_result["status"] == "success"
        listing_id = pub_result["listing_id"]

        # Download
        dl_result = mp.download(listing_id=listing_id, target_warp_name="downloaded_warp")
        assert dl_result["status"] == "success"
        assert dl_result["warp_name"] == "downloaded_warp"
        assert dl_result["imported"] is True

    def test_negotiate_free_warp(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {
            "name": "free_warp",
            "description": "Free warp",
            "tools_allowed": [],
        }
        pub = mp.publish(warp_name="free_warp", warp_data=warp_data)
        result = mp.negotiate(pub["listing_id"], offer_xrp=0.0)
        assert result["status"] == "accepted"

    def test_publish_dedup(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {
            "name": "dedup_warp",
            "description": "Dedup test",
            "tools_allowed": ["gnosis"],
        }
        r1 = mp.publish(warp_name="dedup_warp", warp_data=warp_data)
        r2 = mp.publish(warp_name="dedup_warp", warp_data=warp_data)
        assert r1["status"] == "success"
        assert r2["status"] == "exists"
        assert r1["listing_id"] == r2["listing_id"]

    def test_get_listing(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {"name": "get_listing_warp", "description": "test"}
        pub = mp.publish(warp_name="get_listing_warp", warp_data=warp_data)
        listing = mp.get_listing(pub["listing_id"])
        assert listing is not None
        assert listing["warp_name"] == "get_listing_warp"

    def test_remove_listing(self):
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {"name": "removable_warp", "description": "test"}
        pub = mp.publish(warp_name="removable_warp", warp_data=warp_data)
        result = mp.remove(pub["listing_id"])
        assert result["status"] == "success"
        assert mp.get_listing(pub["listing_id"]) is None


# ── Mesh Inference Router Tests ───────────────────────────────────────────


class TestInferenceRouter:
    """Tests for the mesh inference router."""

    def test_register_node(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        result = router.register_node(
            node_id="test_node_0",
            address="localhost:50052",
            models=["qwen3-1.7b", "qwen3-4b"],
            reputation=0.8,
        )
        assert result["status"] == "success"
        nodes = router.get_nodes()
        assert any(n["node_id"] == "test_node_0" for n in nodes)

    def test_route_fastest(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(
            node_id="fast_node",
            models=["test_model"],
            reputation=0.9,
        )
        router.update_node_health("fast_node", tokens_per_sec=100.0, rtt_ms=10.0)

        # Register a slower node
        router.register_node(
            node_id="slow_node",
            models=["test_model"],
            reputation=0.5,
        )
        router.update_node_health("slow_node", tokens_per_sec=10.0, rtt_ms=100.0)

        decision = router.route(model="test_model", strategy="fastest")
        assert decision.node_id == "fast_node"
        assert decision.strategy == "fastest"

    def test_route_local_first(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(
            node_id="remote_node_lf",
            models=["lf_model"],
            reputation=0.9,
        )
        # Make local node have the model too
        router.update_node_models(router._local_node_id, ["lf_model"])

        decision = router.route(model="lf_model", strategy="local_first")
        assert decision.node_id == router._local_node_id

    def test_route_round_robin(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="rr_node_a", models=["rr_model"], reputation=0.9)
        router.register_node(node_id="rr_node_b", models=["rr_model"], reputation=0.9)

        decisions = [router.route(model="rr_model", strategy="round_robin") for _ in range(4)]
        node_ids = [d.node_id for d in decisions]
        # Should cycle through nodes
        assert len(set(node_ids)) >= 2

    def test_route_capacity(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="cap_busy", models=["cap_model"], reputation=0.9)
        router.register_node(node_id="cap_idle", models=["cap_model"], reputation=0.9)
        router.update_node_health("cap_busy", queue_depth=10, tokens_per_sec=50.0)
        router.update_node_health("cap_idle", queue_depth=0, tokens_per_sec=50.0)

        decision = router.route(model="cap_model", strategy="capacity")
        assert decision.node_id == "cap_idle"

    def test_route_reputation(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="rep_low", models=["rep_model"], reputation=0.3)
        router.register_node(node_id="rep_high", models=["rep_model"], reputation=0.95)

        decision = router.route(model="rep_model", strategy="reputation")
        assert decision.node_id == "rep_high"

    def test_route_fallback_no_model(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        decision = router.route(model="nonexistent_model_xyz")
        assert decision.fallback is True
        assert decision.node_id == router._local_node_id

    def test_update_node_health(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="health_node", models=["hm"])
        router.update_node_health(
            "health_node",
            status="busy",
            queue_depth=5,
            tokens_per_sec=42.0,
            rtt_ms=15.0,
        )
        nodes = router.get_nodes()
        node = next(n for n in nodes if n["node_id"] == "health_node")
        assert node["queue_depth"] == 5
        assert node["tokens_per_sec"] == 42.0
        assert node["status"] == "busy"

    def test_get_available_nodes_filtered(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="filter_a", models=["filter_model"], reputation=0.9)
        router.register_node(node_id="filter_b", models=["other_model"], reputation=0.9)

        nodes = router.get_available_nodes(model="filter_model")
        node_ids = [n["node_id"] for n in nodes]
        assert "filter_a" in node_ids
        assert "filter_b" not in node_ids

    def test_set_strategy(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        result = router.set_strategy("round_robin")
        assert result["status"] == "success"
        assert router._strategy.value == "round_robin"

        result = router.set_strategy("invalid_strategy")
        assert result["status"] == "error"

    def test_router_status(self):
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        status = router.get_status()
        assert "strategy" in status
        assert "total_nodes" in status
        assert "active_nodes" in status
        assert "stats" in status
        assert "nodes" in status


# ── Cross-Module Integration ──────────────────────────────────────────────


class TestP4CrossModule:
    """Tests that exercise multiple P4 modules together."""

    def test_warp_marketplace_with_inference_tier(self):
        """Publish a warp with an inference tier, then route to that tier."""
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace
        from whitemagic.mesh.inference_router import get_inference_router

        # Publish warp with local_small tier
        mp = get_warp_marketplace()
        warp_data = {
            "name": "tiered_warp",
            "description": "Warp with inference tier",
            "inference_tier": "local_small",
            "tools_allowed": ["mesh.route"],
        }
        pub = mp.publish(warp_name="tiered_warp", warp_data=warp_data)

        # Discover by inference tier
        result = mp.discover(inference_tier="local_small")
        assert any(l["listing_id"] == pub["listing_id"] for l in result["results"])

        # Router should have local node available
        router = get_inference_router()
        nodes = router.get_available_nodes()
        assert len(nodes) >= 1  # At least local node

    def test_dilo_co_status_after_operations(self):
        """Verify DiLoCo status reflects all operations."""
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({"x": [1.0, 2.0], "y": [3.0]})
        coordinator.register_worker("status_worker_0")
        coordinator.register_worker("status_worker_1")

        coordinator.submit_gradient("status_worker_0", {"x": [0.1, 0.2], "y": [0.3]})
        coordinator.sync_step()

        status = coordinator.get_status()
        assert status["pool"]["active_workers"] >= 2
        assert status["sync_count"] >= 1
        assert status["compressor"]["compress_count"] > 0
        assert status["param_count"] == 2

    def test_full_p4_pipeline(self):
        """Full pipeline: init DiLoCo → train → route inference → publish warp."""
        # 1. DiLoCo init + train
        from whitemagic.mesh.dilo_co import get_dilo_co

        coordinator = get_dilo_co()
        coordinator.init_params({"model.weight": [0.5, 0.5]})
        coordinator.register_worker("pipeline_worker")
        coordinator.submit_gradient("pipeline_worker", {"model.weight": [0.01, 0.02]})
        sync_result = coordinator.sync_step()
        assert sync_result["status"] == "success"

        # 2. Route inference
        from whitemagic.mesh.inference_router import get_inference_router

        router = get_inference_router()
        router.register_node(node_id="pipeline_inference", models=["pipeline_model"])
        decision = router.route(model="pipeline_model")
        assert decision.model == "pipeline_model"

        # 3. Publish warp with trained model info
        from whitemagic.mesh.warp_marketplace import get_warp_marketplace

        mp = get_warp_marketplace()
        warp_data = {
            "name": "pipeline_trained_warp",
            "description": "Warp after DiLoCo training pipeline",
            "inference_tier": "local_small",
            "metadata": {"trained_with": "dilo_co", "sync_count": sync_result["sync_count"]},
        }
        pub = mp.publish(warp_name="pipeline_trained_warp", warp_data=warp_data)
        assert pub["status"] == "success"

        # 4. Verify all systems report activity
        assert coordinator.get_status()["sync_count"] >= 1
        assert router.get_status()["stats"]["total_requests"] >= 1
        assert mp.get_status()["total_listings"] >= 1
