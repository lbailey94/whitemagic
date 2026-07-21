"""Tests for ABI decoder selector matching (keccak256)."""

from whitemagic.tools.security.abi_decoder import _selector_matches


class TestSelectorMatches:
    def test_erc20_transfer_vector(self):
        # Canonical ERC-20 selector: keccak256("transfer(address,uint256)")[0:4]
        assert _selector_matches("0xa9059cbb", "transfer(address,uint256)") is True

    def test_erc20_balance_of_vector(self):
        # keccak256("balanceOf(address)")[0:4] = 0x70a08231
        assert _selector_matches("0x70a08231", "balanceOf(address)") is True

    def test_without_0x_prefix(self):
        assert _selector_matches("a9059cbb", "transfer(address,uint256)") is True

    def test_case_insensitive(self):
        assert _selector_matches("0xA9059CBB", "transfer(address,uint256)") is True

    def test_non_matching_signature(self):
        assert _selector_matches("0xa9059cbb", "approve(address,uint256)") is False

    def test_wrong_signature_format_changes_digest(self):
        # Whitespace/ordering matters in canonical signatures
        assert _selector_matches("0xa9059cbb", "transfer(address, uint256)") is False
