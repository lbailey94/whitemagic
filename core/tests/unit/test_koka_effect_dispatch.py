"""Tests for Koka effect dispatch wrappers.

Tests verify the high-level wrapper methods correctly format line-protocol
commands and parse responses. Uses mock dispatch_line to avoid needing
compiled Koka binaries.
"""

from unittest.mock import patch

from whitemagic.core.acceleration.koka_native_bridge import KokaNativeBridge


class TestBackpressureWrappers:
    def test_admit_true(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true"):
            assert bridge.backpressure_admit(1) is True

    def test_admit_false(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:false"):
            assert bridge.backpressure_admit(0) is False

    def test_admit_none_on_error(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value=None):
            assert bridge.backpressure_admit() is None

    def test_should_shed_true(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true"):
            assert bridge.backpressure_should_shed() is True

    def test_current_load(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:0.75"):
            assert bridge.backpressure_current_load() == 0.75

    def test_set_threshold(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:set"):
            assert bridge.backpressure_set_threshold(0.8) is True


class TestTimeoutWrappers:
    def test_set_timeout(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:set"):
            assert bridge.timeout_set(5000) is True

    def test_get_timeout(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:5000"):
            assert bridge.timeout_get() == 5000

    def test_is_timed_out(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:false"):
            assert bridge.timeout_is_timed_out() is False

    def test_time_remaining(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:3000"):
            assert bridge.timeout_time_remaining() == 3000


class TestRetryWrappers:
    def test_attempt(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:2"):
            assert bridge.retry_attempt("test_op") == 2

    def test_should_retry(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true"):
            assert bridge.retry_should_retry() is True

    def test_backoff_delay(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:400"):
            assert bridge.retry_backoff_delay() == 400

    def test_set_strategy(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:set"):
            assert bridge.retry_set_strategy("exponential", 100, 30000) is True


class TestTransactionWrappers:
    def test_begin(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:tx_0"):
            assert bridge.transaction_begin() == "tx_0"

    def test_commit(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true"):
            assert bridge.transaction_commit("tx_0") is True

    def test_rollback(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true"):
            assert bridge.transaction_rollback("tx_0") is True

    def test_status(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:active"):
            assert bridge.transaction_status("tx_0") == "active"

    def test_status_unknown(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:unknown"):
            assert bridge.transaction_status("tx_nonexistent") == "unknown"


class TestCommandFormatting:
    """Verify that dispatch_line is called with correct line-protocol commands."""

    def test_admit_command_format(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true") as mock:
            bridge.backpressure_admit(3)
            mock.assert_called_once_with("backpressure", "admit:3")

    def test_timeout_set_command(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:set") as mock:
            bridge.timeout_set(10000)
            mock.assert_called_once_with("timeout", "set:10000")

    def test_retry_set_strategy_command(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:set") as mock:
            bridge.retry_set_strategy("linear", 200, 5000)
            mock.assert_called_once_with("retry", "set-strategy:linear:200:5000")

    def test_transaction_commit_command(self):
        bridge = KokaNativeBridge()
        with patch.object(bridge, "dispatch_line", return_value="ok:true") as mock:
            bridge.transaction_commit("tx_42")
            mock.assert_called_once_with("transactions", "commit:tx_42")
