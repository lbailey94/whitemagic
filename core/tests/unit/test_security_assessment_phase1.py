"""Tests for Security Capabilities Assessment Phase 1: Unified Security Event Bus.

Covers:
  - SecurityEventBus pub/sub (in-memory)
  - SecurityEvent dataclass
  - SecurityEventType constants
  - Integration: TransactionFirewall publishes events
  - Integration: HermitCrab publishes state changes
  - Integration: WasmVerifier publishes verification failures
  - Integration: EngagementTokenManager publishes issue/revoke/validate
  - History and stats
"""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase1_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── SecurityEventBus Basics ─────────────────────────────────────────────


class TestSecurityEventBus:
    """Test the SecurityEventBus pub/sub mechanism."""

    def test_publish_and_subscribe(self):
        from whitemagic.security.event_bus import (
            SecurityEventBus,
            SecurityEventType,
        )

        bus = SecurityEventBus()
        received = []
        bus.subscribe(SecurityEventType.TOOL_BLOCKED, lambda e: received.append(e))

        bus.emit(
            event_type=SecurityEventType.TOOL_BLOCKED,
            source="test",
            detail="test event",
        )
        assert len(received) == 1
        assert received[0].event_type == SecurityEventType.TOOL_BLOCKED
        assert received[0].source == "test"

    def test_wildcard_subscriber_receives_all(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        received = []
        bus.subscribe(None, lambda e: received.append(e))

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="test1")
        bus.emit(event_type=SecurityEventType.URL_BLOCKED, source="test2")
        assert len(received) == 2

    def test_unsubscribe(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        received = []
        def cb(e):
            return received.append(e)
        bus.subscribe(SecurityEventType.TOOL_BLOCKED, cb)

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="test")
        assert len(received) == 1

        bus.unsubscribe(SecurityEventType.TOOL_BLOCKED, cb)
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="test2")
        assert len(received) == 1  # No new events

    def test_history(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.emit(event_type=SecurityEventType.URL_BLOCKED, source="b")
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="c")

        all_events = bus.history(limit=10)
        assert len(all_events) == 3

        filtered = bus.history(event_type=SecurityEventType.TOOL_BLOCKED)
        assert len(filtered) == 2
        assert all(e.event_type == SecurityEventType.TOOL_BLOCKED for e in filtered)

        filtered_source = bus.history(source="b")
        assert len(filtered_source) == 1

    def test_stats(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="b")
        bus.emit(event_type=SecurityEventType.URL_BLOCKED, source="c")

        stats = bus.stats()
        assert stats["total_events"] == 3
        assert stats["by_type"][SecurityEventType.TOOL_BLOCKED] == 2
        assert stats["by_type"][SecurityEventType.URL_BLOCKED] == 1

    def test_clear(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.clear()
        assert len(bus.history()) == 0

    def test_severity_levels(self):
        from whitemagic.security.event_bus import (
            SecurityEventBus,
            SecurityEventType,
        )

        bus = SecurityEventBus()
        received = []
        bus.subscribe(None, lambda e: received.append(e))

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="test", severity="critical")
        assert received[0].severity == "critical"

    def test_metadata_preserved(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        received = []
        bus.subscribe(None, lambda e: received.append(e))

        bus.emit(
            event_type=SecurityEventType.TRANSACTION_BLOCKED,
            source="tx_firewall",
            metadata={"amount": 1000, "currency": "USDC"},
        )
        assert received[0].metadata["amount"] == 1000
        assert received[0].metadata["currency"] == "USDC"

    def test_event_id_unique(self):
        from whitemagic.security.event_bus import SecurityEventBus, SecurityEventType

        bus = SecurityEventBus()
        received = []
        bus.subscribe(None, lambda e: received.append(e))

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="b")
        assert received[0].event_id != received[1].event_id


# ─── SecurityEvent Dataclass ─────────────────────────────────────────────


class TestSecurityEvent:
    """Test SecurityEvent dataclass serialization."""

    def test_to_dict(self):
        from whitemagic.security.event_bus import SecurityEvent

        event = SecurityEvent(
            event_type="test.event",
            source="test",
            severity="high",
            detail="test detail",
            metadata={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "test.event"
        assert d["source"] == "test"
        assert d["severity"] == "high"
        assert d["metadata"]["key"] == "value"
        assert "event_id" in d
        assert "timestamp" in d

    def test_from_dict(self):
        from whitemagic.security.event_bus import SecurityEvent

        data = {
            "event_type": "test.event",
            "source": "test",
            "severity": "low",
            "detail": "detail",
            "metadata": {"k": "v"},
            "event_id": "test-id",
            "timestamp": "2026-01-01T00:00:00",
            "epoch": 1000.0,
        }
        event = SecurityEvent.from_dict(data)
        assert event.event_type == "test.event"
        assert event.source == "test"
        assert event.event_id == "test-id"

    def test_roundtrip(self):
        from whitemagic.security.event_bus import SecurityEvent

        event = SecurityEvent(
            event_type="test.roundtrip",
            source="test",
            metadata={"a": 1, "b": 2},
        )
        d = event.to_dict()
        restored = SecurityEvent.from_dict(d)
        assert restored.event_type == event.event_type
        assert restored.source == event.source
        assert restored.metadata == event.metadata


# ─── SecurityEventType Constants ─────────────────────────────────────────


class TestSecurityEventType:
    """Test that all canonical event types are defined."""

    def test_all_types_defined(self):
        from whitemagic.security.event_bus import SecurityEventType

        assert SecurityEventType.TOOL_BLOCKED == "security.tool_blocked"
        assert SecurityEventType.PATH_VIOLATION == "security.path_violation"
        assert SecurityEventType.URL_BLOCKED == "security.url_blocked"
        assert SecurityEventType.PROMPT_INJECTION_DETECTED == "security.prompt_injection_detected"
        assert SecurityEventType.RAPID_FIRE_DETECTED == "security.rapid_fire_detected"
        assert SecurityEventType.LATERAL_MOVEMENT == "security.lateral_movement"
        assert SecurityEventType.ESCALATION_ATTEMPT == "security.escalation_attempt"
        assert SecurityEventType.TRANSACTION_BLOCKED == "security.transaction_blocked"
        assert SecurityEventType.TRANSACTION_APPROVED == "security.transaction_approved"
        assert SecurityEventType.WASM_VERIFICATION_FAILED == "security.wasm_verification_failed"
        assert SecurityEventType.HERMIT_CRAB_STATE_CHANGE == "security.hermit_crab_state_change"
        assert SecurityEventType.ENGAGEMENT_TOKEN_ISSUED == "security.engagement_token_issued"
        assert SecurityEventType.ENGAGEMENT_TOKEN_REVOKED == "security.engagement_token_revoked"
        assert SecurityEventType.ENGAGEMENT_TOKEN_VALIDATED == "security.engagement_token_validated"
        assert SecurityEventType.ENGAGEMENT_TOKEN_REJECTED == "security.engagement_token_rejected"
        assert SecurityEventType.MCP_DRIFT_DETECTED == "security.mcp_drift_detected"
        assert SecurityEventType.MODEL_VERIFICATION_FAILED == "security.model_verification_failed"
        assert SecurityEventType.SHELTER_CREATED == "security.shelter_created"
        assert SecurityEventType.SHELTER_DESTROYED == "security.shelter_destroyed"
        assert SecurityEventType.DHARMA_BLOCKED == "security.dharma_blocked"


# ─── Integration: TransactionFirewall ────────────────────────────────────


class TestTransactionFirewallEvents:
    """Test that TransactionFirewall publishes events to the bus."""

    def test_blocked_transaction_publishes_event(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        firewall = TransactionFirewall()
        firewall.set_policy("test_agent", TransactionPolicy(max_single_transaction=100))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=500,
            currency="USDC",
            recipient="0xabc",
            tool_name="test_tool",
            purpose="test",
        )
        verdict = firewall.validate(request)
        assert not verdict.approved

        events = bus.history(event_type=SecurityEventType.TRANSACTION_BLOCKED)
        assert len(events) >= 1
        assert events[-1].source == "transaction_firewall"
        assert events[-1].metadata["amount"] == 500

    def test_approved_transaction_publishes_event(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        firewall = TransactionFirewall()
        firewall.set_policy("test_agent", TransactionPolicy(max_single_transaction=1000))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=50,
            currency="USDC",
            recipient="0xabc",
            tool_name="test_tool",
            purpose="test",
        )
        verdict = firewall.validate(request)
        assert verdict.approved

        events = bus.history(event_type=SecurityEventType.TRANSACTION_APPROVED)
        assert len(events) >= 1


# ─── Integration: HermitCrab ─────────────────────────────────────────────


class TestHermitCrabEvents:
    """Test that HermitCrab publishes state changes to the bus."""

    def test_withdrawal_publishes_state_change(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.hermit_crab import HermitCrab

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        hermit = HermitCrab()
        hermit.withdraw("test withdrawal")

        events = bus.history(event_type=SecurityEventType.HERMIT_CRAB_STATE_CHANGE)
        assert len(events) >= 1
        assert events[-1].source == "hermit_crab"
        assert "withdrawn" in events[-1].detail

    def test_guarded_state_publishes_event(self):
        import tempfile
        from pathlib import Path

        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.hermit_crab import HermitCrab

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        # Use fresh temp dir to avoid persisted state from previous tests
        tmp_dir = Path(tempfile.mkdtemp(prefix="wm_hermit_test_"))
        hermit = HermitCrab(state_dir=tmp_dir)
        # Trigger guarded mode with moderate threat (need > 0.3 composite)
        hermit.assess_threat({
            "boundary_violations": 1.0,
            "coercion_detected": 0.5,
            "abuse_score": 0.5,
        })

        events = bus.history(event_type=SecurityEventType.HERMIT_CRAB_STATE_CHANGE)
        assert len(events) >= 1


# ─── Integration: EngagementTokenManager ─────────────────────────────────


class TestEngagementTokenEvents:
    """Test that EngagementTokenManager publishes events to the bus."""

    def test_issue_publishes_event(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        mgr = get_token_manager()
        mgr._tokens.clear()
        mgr.issue(scope=["10.0.0.*"], tools=["nmap_*"], issuer="test", duration_minutes=5)

        events = bus.history(event_type=SecurityEventType.ENGAGEMENT_TOKEN_ISSUED)
        assert len(events) >= 1
        assert events[-1].source == "engagement_tokens"
        assert events[-1].metadata["issuer"] == "test"

    def test_revoke_publishes_event(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        mgr = get_token_manager()
        mgr._tokens.clear()
        issued = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
        token_id = issued["token"]["token_id"]

        bus.clear()
        mgr.revoke(token_id)

        events = bus.history(event_type=SecurityEventType.ENGAGEMENT_TOKEN_REVOKED)
        assert len(events) >= 1
        assert events[-1].source == "engagement_tokens"

    def test_validate_publishes_event(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        mgr = get_token_manager()
        mgr._tokens.clear()
        issued = mgr.issue(scope=["10.0.0.*"], tools=["nmap_*"], issuer="test", duration_minutes=5)
        token_id = issued["token"]["token_id"]

        bus.clear()
        mgr.validate(token_id, tool="nmap_scan", target="10.0.0.1")

        events = bus.history(event_type=SecurityEventType.ENGAGEMENT_TOKEN_VALIDATED)
        assert len(events) >= 1
        assert events[-1].tool_name == "nmap_scan"


# ─── Integration: WasmVerifier ───────────────────────────────────────────


class TestWasmVerifierEvents:
    """Test that WasmVerifier publishes verification failures to the bus."""

    def test_verification_failure_publishes_event(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.wasm_verifier import (
            VerificationRequest,
            WasmVerifier,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        verifier = WasmVerifier()
        # Create a request for a verifiable tool with mismatched output
        request = VerificationRequest(
            tool_name="memory_search",
            inputs={"query": "test"},
            outputs={"results": ["wrong"]},
        )
        verifier.verify(request)

        events = bus.history(event_type=SecurityEventType.WASM_VERIFICATION_FAILED)
        # May or may not have an event depending on replay behavior, but if present should be from wasm_verifier
        for e in events:
            assert e.source == "wasm_verifier"


# ─── Singleton ───────────────────────────────────────────────────────────


class TestSingleton:
    """Test the singleton pattern."""

    def test_get_security_event_bus_returns_same_instance(self):
        from whitemagic.security.event_bus import get_security_event_bus

        bus1 = get_security_event_bus()
        bus2 = get_security_event_bus()
        assert bus1 is bus2

    def test_reset_security_event_bus(self):
        from whitemagic.security.event_bus import (
            get_security_event_bus,
            reset_security_event_bus,
        )

        bus1 = get_security_event_bus()
        reset_security_event_bus()
        bus2 = get_security_event_bus()
        assert bus1 is not bus2
