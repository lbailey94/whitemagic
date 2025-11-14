"""
Shared test fixtures for WhiteMagic tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from whitemagic.api import rate_limit


@pytest.fixture(autouse=True)
def mock_rate_limiter(monkeypatch):
    """
    Mock the rate limiter for all API tests.
    
    This prevents the "Rate limiter not initialized" error
    in tests that don't go through the full app lifespan.
    """
    # Create a mock rate limiter
    mock_limiter = Mock()
    mock_limiter.check_rate_limit = AsyncMock(return_value={
        "allowed": True,
        "limit": 1000,
        "remaining": 999,
        "reset": 3600,
    })
    
    # Patch the global rate limiter
    monkeypatch.setattr(rate_limit, "_rate_limiter", mock_limiter)
    
    # Patch the getter to return our mock
    monkeypatch.setattr(
        rate_limit,
        "get_rate_limiter",
        lambda: mock_limiter
    )
    
    return mock_limiter
