"""Tests for Economic Layer — Wallet, Tips, and Gratitude Settlement.

Uses mocks for XRPL to avoid network dependencies.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWalletManager:
    """Tests for WalletManager receive-only wallet."""

    def test_wallet_disabled_without_env(self):
        """Wallet should be disabled if WM_XRP_ADDRESS is not set."""
        from whitemagic.core.economy.wallet_manager import WalletManager

        # Ensure env is clear
        with patch.dict(os.environ, {}, clear=True):
            wm = WalletManager()
            assert not wm.enabled
            assert wm.public_address == ""

    def test_wallet_enabled_with_env(self):
        """Wallet should activate when WM_XRP_ADDRESS is set."""
        from whitemagic.core.economy.wallet_manager import WalletManager

        test_addr = "rN7n7otQDd6FczFgLdlqtyMVrn3HMfHgFj"
        with patch.dict(os.environ, {"WM_XRP_ADDRESS": test_addr}):
            wm = WalletManager()
            assert wm.enabled
            assert wm.public_address == test_addr

    def test_propose_gratitude_settlement_no_beneficiaries(self):
        """Settlement with no beneficiaries should return 100% to owner."""
        from whitemagic.core.economy.wallet_manager import WalletManager

        test_addr = "rN7n7otQDd6FczFgLdlqtyMVrn3HMfHgFj"
        with patch.dict(os.environ, {"WM_XRP_ADDRESS": test_addr}):
            wm = WalletManager()
            proposal = wm.propose_gratitude_settlement(10.0)
            assert proposal["status"] == "pending_approval"
            assert proposal["currency"] == "XRP"
            assert len(proposal["proposals"]) == 1
            assert proposal["proposals"][0]["target"] == "Local Node Owner"
            assert proposal["proposals"][0]["amount"] == 10.0

    def test_get_gratitude_payload(self):
        """Gratitude payload should have required fields."""
        from whitemagic.core.economy.wallet_manager import WalletManager

        with patch.dict(os.environ, {}, clear=True):
            wm = WalletManager()
            payload = wm.get_gratitude_payload(5.5)
            assert payload["title"] == "Gratitude Resonance"
            assert "5.5 XRP" in payload["content"]
            assert "gratitude" in payload["tags"]
            assert payload["importance"] == 0.9

    @pytest.mark.asyncio
    async def test_check_for_tips_disabled(self):
        """check_for_tips should return None when wallet is disabled."""
        from whitemagic.core.economy.wallet_manager import WalletManager

        with patch.dict(os.environ, {}, clear=True):
            wm = WalletManager()
            tip = await wm.check_for_tips()
            assert tip is None

    @pytest.mark.asyncio
    async def test_check_for_tips_no_httpx(self):
        """check_for_tips should return None when httpx is unavailable."""
        from whitemagic.core.economy import wallet_manager as wm_mod

        test_addr = "rN7n7otQDd6FczFgLdlqtyMVrn3HMfHgFj"
        with patch.dict(os.environ, {"WM_XRP_ADDRESS": test_addr}):
            with patch.object(wm_mod, "_HTTPX_AVAILABLE", False):
                wm = wm_mod.WalletManager()
                tip = await wm.check_for_tips()
                assert tip is None

    @pytest.mark.asyncio
    async def test_check_for_tips_detects_new_tip(self):
        """check_for_tips should detect a balance increase as a tip."""
        from whitemagic.core.economy import wallet_manager as wm_mod

        test_addr = "rN7n7otQDd6FczFgLdlqtyMVrn3HMfHgFj"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "account_data": {
                    "Balance": "2000000",  # 2 XRP in drops
                }
            }
        }

        with patch.dict(os.environ, {"WM_XRP_ADDRESS": test_addr}):
            with patch.object(wm_mod, "_HTTPX_AVAILABLE", True):
                wm = wm_mod.WalletManager()
                wm.last_balance = 1.0  # 1 XRP previously

                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.post = AsyncMock(return_value=mock_response)

                with patch("whitemagic.core.economy.wallet_manager.httpx.AsyncClient", return_value=mock_client):
                    tip = await wm.check_for_tips()
                    assert tip == 1.0  # 2 - 1 = 1 XRP
                    assert wm.last_balance == 2.0


class TestTipRoute:
    """Tests for the /tip FastAPI routes (when available)."""

    def test_tip_module_imports(self):
        """The tip route module should import without error."""
        from whitemagic.interfaces.api.routes import tip

        assert tip is not None

    @pytest.mark.asyncio
    async def test_tip_status_when_disabled(self):
        """tip_status should return enabled=False when wallet is not configured."""
        from whitemagic.interfaces.api.routes.tip import tip_status

        with patch.dict(os.environ, {}, clear=True):
            result = await tip_status()
            assert result["status"] == "success"
            assert result["data"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_tip_status_when_enabled(self):
        """tip_status should return wallet details when configured."""
        from whitemagic.interfaces.api.routes.tip import tip_status
        from whitemagic.core.economy import wallet_manager as wm_mod

        test_addr = "rN7n7otQDd6FczFgLdlqtyMVrn3HMfHgFj"
        with patch.dict(os.environ, {"WM_XRP_ADDRESS": test_addr}):
            # Reset singleton so new env is picked up
            wm_mod._wallet_manager = None
            result = await tip_status()
            assert result["status"] == "success"
            assert result["data"]["enabled"] is True
            assert result["data"]["address"] == test_addr
