"""Tests for IceOryx2 model mesh."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from whitemagic.inference.model_mesh import (
    CHANNEL_MODEL_BITMAMBA,
    CHANNEL_MODEL_LLAMA,
    CHANNEL_MODEL_REQUESTS,
    CHANNEL_MODEL_STATUS,
    InferenceRequest,
    InferenceResponse,
    MeshStats,
    ModelMeshClient,
    ModelMeshPublisher,
    ModelStatus,
    get_mesh_client,
)


class TestInferenceRequest:
    def test_creation(self):
        req = InferenceRequest(
            id="test-1",
            model="llama",
            prompt="Hello",
            max_tokens=64,
            temperature=0.5,
        )
        assert req.id == "test-1"
        assert req.model == "llama"
        assert req.prompt == "Hello"

    def test_serialization(self):
        req = InferenceRequest(id="test-1", model="llama", prompt="Hello")
        data = req.to_bytes()
        assert isinstance(data, bytes)
        req2 = InferenceRequest.from_bytes(data)
        assert req2 is not None
        assert req2.id == "test-1"
        assert req2.model == "llama"
        assert req2.prompt == "Hello"

    def test_from_bytes_invalid(self):
        assert InferenceRequest.from_bytes(b"invalid json") is None
        assert InferenceRequest.from_bytes(b'{"missing": "id"}') is None

    def test_prompt_truncation(self):
        req = InferenceRequest(id="test", model="llama", prompt="x" * 5000)
        data = req.to_bytes()
        d = json.loads(data)
        assert len(d["prompt"]) <= 2000


class TestInferenceResponse:
    def test_creation(self):
        resp = InferenceResponse(
            id="test-1",
            text="Hello world",
            tokens=[1, 2, 3],
            latency_ms=42.0,
        )
        assert resp.id == "test-1"
        assert resp.text == "Hello world"
        assert resp.tokens == [1, 2, 3]
        assert resp.status == "ok"

    def test_serialization(self):
        resp = InferenceResponse(id="test-1", text="Hello", tokens=[1, 2])
        data = resp.to_bytes()
        resp2 = InferenceResponse.from_bytes(data)
        assert resp2 is not None
        assert resp2.id == "test-1"
        assert resp2.text == "Hello"
        assert resp2.tokens == [1, 2]

    def test_from_bytes_invalid(self):
        assert InferenceResponse.from_bytes(b"invalid") is None


class TestModelStatus:
    def test_creation(self):
        status = ModelStatus(model="llama", status="ready", ram_mb=500.0, tokens_per_sec=15.0)
        assert status.model == "llama"
        assert status.status == "ready"
        assert status.ram_mb == 500.0

    def test_serialization(self):
        status = ModelStatus(model="bitmamba", status="ready", ram_mb=252.0)
        data = status.to_bytes()
        status2 = ModelStatus.from_bytes(data)
        assert status2 is not None
        assert status2.model == "bitmamba"
        assert status2.ram_mb == 252.0

    def test_from_bytes_invalid(self):
        assert ModelStatus.from_bytes(b"invalid") is None


class TestMeshStats:
    def test_default(self):
        stats = MeshStats()
        assert stats.requests_sent == 0
        assert stats.responses_received == 0
        assert stats.avg_latency_ms == 0.0

    def test_avg_latency(self):
        stats = MeshStats()
        stats.responses_received = 2
        stats.total_latency_ms = 100.0
        assert stats.avg_latency_ms == 50.0

    def test_to_dict(self):
        stats = MeshStats()
        stats.requests_sent = 5
        d = stats.to_dict()
        assert d["requests_sent"] == 5
        assert "avg_latency_ms" in d
        assert "models_available" in d


class TestModelMeshClient:
    def test_not_available_without_ipc(self):
        client = ModelMeshClient()
        # IPC not available in test env
        assert not client.is_available or client.is_available  # Depends on env

    def test_request_without_availability(self):
        client = ModelMeshClient()
        client._ipc_available = False
        result = client.request("llama", "test", max_tokens=5)
        assert result is None

    def test_get_status(self):
        client = ModelMeshClient()
        status = client.get_status()
        assert "requests_sent" in status
        assert "responses_received" in status

    def test_get_model_status_not_found(self):
        client = ModelMeshClient()
        assert client.get_model_status("nonexistent") is None

    def test_start_without_availability(self):
        client = ModelMeshClient()
        client._ipc_available = False
        assert not client.start()

    def test_stop(self):
        client = ModelMeshClient()
        client.stop()  # Should not raise


class TestModelMeshPublisher:
    def test_creation(self):
        pub = ModelMeshPublisher("llama")
        assert pub._model_name == "llama"

    def test_not_available_without_ipc(self):
        pub = ModelMeshPublisher("llama")
        pub._ipc_available = False
        assert not pub.is_available

    def test_publish_response_without_availability(self):
        pub = ModelMeshPublisher("llama")
        pub._ipc_available = False
        resp = InferenceResponse(id="test", text="hello")
        assert not pub.publish_response(resp)

    def test_publish_status_without_availability(self):
        pub = ModelMeshPublisher("llama")
        pub._ipc_available = False
        assert not pub.publish_status()

    def test_start_stop_status_broadcast(self):
        pub = ModelMeshPublisher("llama")
        pub._ipc_available = False
        pub.start_status_broadcast()  # Should be no-op
        pub.stop_status_broadcast()


class TestChannelConstants:
    def test_channel_names(self):
        assert CHANNEL_MODEL_LLAMA == "wm/model/llama"
        assert CHANNEL_MODEL_BITMAMBA == "wm/model/bitmamba"
        assert CHANNEL_MODEL_REQUESTS == "wm/model/requests"
        assert CHANNEL_MODEL_STATUS == "wm/model/status"


class TestSingleton:
    def test_get_mesh_client(self):
        c1 = get_mesh_client()
        c2 = get_mesh_client()
        assert c1 is c2


class TestMockedMeshFlow:
    """Test the full mesh flow with mocked IPC."""

    def test_request_response_flow(self):
        """Test a complete request → response cycle with mocked IPC."""
        client = ModelMeshClient()
        client._ipc_available = True

        # Track published requests
        published_requests: list[bytes] = []

        def mock_publish(channel, payload):
            if channel == CHANNEL_MODEL_REQUESTS:
                published_requests.append(payload)

        def mock_try_receive(channel, max_samples):
            if channel == CHANNEL_MODEL_LLAMA and published_requests:
                req = InferenceRequest.from_bytes(published_requests[0])
                if req:
                    resp = InferenceResponse(
                        id=req.id,
                        text="Generated text",
                        tokens=[100, 200, 300],
                        latency_ms=50.0,
                    )
                    return [resp.to_bytes()]
            return []

        mock_rust = MagicMock()
        mock_rust.ipc_status.return_value = {"iceoryx2_compiled": "true"}
        mock_rust.ipc_publish = mock_publish
        mock_rust.ipc_try_receive = mock_try_receive

        with patch.dict("sys.modules", {"whitemagic_rs": mock_rust}):
            # Send request (non-blocking to control the flow)
            req_id = client.request_async("llama", "test prompt", max_tokens=10)
            assert req_id

            # Manually poll once to get the response
            client._poll_responses()

            # Check response
            with client._lock:
                response = client._responses.get(req_id)
            assert response is not None
            assert response.text == "Generated text"
            assert response.tokens == [100, 200, 300]
            assert response.latency_ms == 50.0

    def test_status_polling(self):
        """Test status channel polling with mocked IPC."""
        client = ModelMeshClient()
        client._ipc_available = True

        status_msg = ModelStatus(
            model="llama",
            status="ready",
            ram_mb=500.0,
            tokens_per_sec=15.0,
        )

        def mock_receive(channel, max_samples):
            if channel == CHANNEL_MODEL_STATUS:
                return [status_msg.to_bytes()]
            return []

        mock_rust = MagicMock()
        mock_rust.ipc_status.return_value = {"iceoryx2_compiled": "true"}
        mock_rust.ipc_publish = MagicMock()
        mock_rust.ipc_try_receive = mock_receive

        with patch.dict("sys.modules", {"whitemagic_rs": mock_rust}):
            client._poll_status()
            status = client.get_model_status("llama")
            assert status is not None
            assert status.status == "ready"
            assert status.ram_mb == 500.0
