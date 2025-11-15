"""
Tests for WhiteMagic configuration system.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Ensure local package is used
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from whitemagic.config import (
    ConfigManager,
    WhiteMagicConfig,
    EmbeddingsConfig,
    SearchConfig,
    TerminalConfig,
    APIConfig,
)


@pytest.fixture
def temp_config_path():
    """Create temporary config file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_config.yaml"


@pytest.fixture
def config_manager(temp_config_path):
    """Create config manager with temp path."""
    return ConfigManager(config_path=temp_config_path)


def test_default_config_creation(config_manager, temp_config_path):
    """Test that default config is created if file doesn't exist."""
    assert not temp_config_path.exists()
    
    config = config_manager.load()
    
    assert temp_config_path.exists()
    assert isinstance(config, WhiteMagicConfig)
    assert config.embeddings.provider == "local"
    assert config.search.default_mode == "hybrid"
    assert config.terminal.enabled is True


def test_config_schemas():
    """Test that config schemas have correct defaults."""
    # EmbeddingsConfig
    embeddings = EmbeddingsConfig()
    assert embeddings.provider == "local"
    assert embeddings.model == "all-MiniLM-L6-v2"
    assert embeddings.cache_enabled is True
    
    # SearchConfig
    search = SearchConfig()
    assert search.default_mode == "hybrid"
    assert search.semantic_threshold == 0.7
    assert search.max_results == 10
    
    # TerminalConfig
    terminal = TerminalConfig()
    assert terminal.enabled is True
    assert terminal.default_profile == "PROD"
    assert terminal.audit_enabled is True
    
    # APIConfig
    api = APIConfig()
    assert api.host == "0.0.0.0"
    assert api.port == 8000
    assert api.workers == 1


def test_config_save_and_load(config_manager, temp_config_path):
    """Test saving and loading config."""
    # Create and save config
    config = WhiteMagicConfig()
    config.embeddings.provider = "openai"
    config.search.max_results = 20
    
    config_manager.save(config)
    assert temp_config_path.exists()
    
    # Create new manager and load
    new_manager = ConfigManager(config_path=temp_config_path)
    loaded_config = new_manager.load()
    
    assert loaded_config.embeddings.provider == "openai"
    assert loaded_config.search.max_results == 20


def test_config_get(config_manager):
    """Test getting config values by dot notation."""
    config_manager.load()
    
    # Test successful gets
    assert config_manager.get("embeddings.provider") == "local"
    assert config_manager.get("search.max_results") == 10
    assert config_manager.get("terminal.enabled") is True
    
    # Test default value
    assert config_manager.get("nonexistent.key", "default") == "default"
    assert config_manager.get("embeddings.nonexistent", None) is None


def test_config_set(config_manager, temp_config_path):
    """Test setting config values by dot notation."""
    config_manager.load()
    
    # Set values
    config_manager.set("embeddings.provider", "openai")
    config_manager.set("search.max_results", 25)
    config_manager.set("terminal.enabled", False)
    
    # Verify in-memory
    assert config_manager.get("embeddings.provider") == "openai"
    assert config_manager.get("search.max_results") == 25
    assert config_manager.get("terminal.enabled") is False
    
    # Verify persisted to file
    new_manager = ConfigManager(config_path=temp_config_path)
    new_config = new_manager.load()
    assert new_config.embeddings.provider == "openai"
    assert new_config.search.max_results == 25
    assert new_config.terminal.enabled is False


def test_config_set_invalid_key(config_manager):
    """Test setting invalid key raises error."""
    config_manager.load()
    
    with pytest.raises(AttributeError):
        config_manager.set("nonexistent.key", "value")


def test_config_validation():
    """Test that config validation works."""
    from pydantic import ValidationError
    
    # Valid configs
    config = WhiteMagicConfig()
    config.embeddings.provider = "local"  # OK
    config.embeddings.provider = "openai"  # OK
    
    # Invalid provider should raise validation error (on model validation, not assignment)
    with pytest.raises(ValidationError):
        EmbeddingsConfig(provider="invalid_provider")
    
    # Invalid search mode should raise validation error
    with pytest.raises(ValidationError):
        SearchConfig(default_mode="invalid_mode")


def test_config_reset(config_manager, temp_config_path):
    """Test resetting config to defaults."""
    config_manager.load()
    
    # Modify config
    config_manager.set("embeddings.provider", "openai")
    config_manager.set("search.max_results", 50)
    
    # Reset
    config = config_manager.reset()
    
    # Verify defaults restored
    assert config.embeddings.provider == "local"
    assert config.search.max_results == 10


def test_config_exists(config_manager, temp_config_path):
    """Test checking if config file exists."""
    assert not config_manager.exists()
    
    config_manager.load()
    assert config_manager.exists()


def test_config_get_path(config_manager, temp_config_path):
    """Test getting config file path."""
    assert config_manager.get_path() == temp_config_path


def test_corrupted_config_file(config_manager, temp_config_path):
    """Test handling of corrupted config file."""
    # Create corrupted file
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_config_path, 'w') as f:
        f.write("invalid: yaml: content: [[[")
    
    # Should create fresh defaults and not crash
    config = config_manager.load()
    assert isinstance(config, WhiteMagicConfig)
    assert config.embeddings.provider == "local"


def test_nested_config_structure():
    """Test that config has correct nested structure."""
    config = WhiteMagicConfig()
    
    # Test embeddings section
    assert hasattr(config, 'embeddings')
    assert isinstance(config.embeddings, EmbeddingsConfig)
    
    # Test search section
    assert hasattr(config, 'search')
    assert isinstance(config.search, SearchConfig)
    
    # Test terminal section
    assert hasattr(config, 'terminal')
    assert isinstance(config.terminal, TerminalConfig)
    
    # Test api section
    assert hasattr(config, 'api')
    assert isinstance(config.api, APIConfig)


def test_config_field_constraints():
    """Test that config field constraints are enforced."""
    from pydantic import ValidationError
    
    # Valid configs
    SearchConfig(semantic_threshold=0.5)  # OK (0.0 <= x <= 1.0)
    APIConfig(port=8080)  # OK
    
    # Test numeric constraints (validated on model creation)
    with pytest.raises(ValidationError):
        SearchConfig(semantic_threshold=1.5)  # > 1.0
    
    with pytest.raises(ValidationError):
        SearchConfig(semantic_threshold=-0.1)  # < 0.0
    
    # Test positive integer constraint
    with pytest.raises(ValidationError):
        APIConfig(port=0)  # < 1
    
    with pytest.raises(ValidationError):
        APIConfig(port=70000)  # > 65535
