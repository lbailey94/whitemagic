"""Tests for whitemagic.api.websocket"""

import pytest
from whitemagic.api.websocket import (
    ConnectionManager,
    disconnect
)


class TestConnectionManager:
    """Tests for ConnectionManager"""
    
    def test_initialization(self):
        """Test ConnectionManager can be initialized"""
        instance = ConnectionManager()
        assert instance is not None
    
    @pytest.mark.skip(reason="Not implemented")
    def test_basic_functionality(self):
        """Test ConnectionManager basic functionality"""
        raise NotImplementedError("Add tests here")


def test_disconnect():
    """Test disconnect function"""
    # TODO: Implement test
    pytest.skip("Not implemented")

