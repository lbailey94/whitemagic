"""
Configuration manager for WhiteMagic.

Handles loading, saving, and accessing configuration from ~/.whitemagic/config.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional
from .schema import WhiteMagicConfig


class ConfigManager:
    """Manage WhiteMagic configuration.
    
    Configuration is stored in ~/.whitemagic/config.yaml by default.
    Environment variables can override config file settings.
    
    Examples:
        >>> config_mgr = ConfigManager()
        >>> config = config_mgr.load()
        >>> print(config.embeddings.provider)
        'local'
        
        >>> config_mgr.set("embeddings.provider", "openai")
        >>> provider = config_mgr.get("embeddings.provider")
        'openai'
    """
    
    DEFAULT_CONFIG_PATH = Path.home() / ".whitemagic" / "config.yaml"
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager.
        
        Args:
            config_path: Custom config file path. Defaults to ~/.whitemagic/config.yaml
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[WhiteMagicConfig] = None
    
    def load(self, force_reload: bool = False) -> WhiteMagicConfig:
        """Load config from file, creating defaults if missing.
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            WhiteMagicConfig instance
        """
        if self._config is not None and not force_reload:
            return self._config
        
        if not self.config_path.exists():
            self._config = self._create_default_config()
            return self._config
        
        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f) or {}
            
            self._config = WhiteMagicConfig(**data)
            return self._config
            
        except Exception as e:
            # If config file is corrupted, create fresh defaults
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            print("Creating fresh default configuration...")
            self._config = self._create_default_config()
            return self._config
    
    def save(self, config: Optional[WhiteMagicConfig] = None) -> None:
        """Save config to file.
        
        Args:
            config: Config to save. If None, saves current loaded config.
            
        Raises:
            ValueError: If no config provided and none loaded
        """
        if config is None:
            if self._config is None:
                raise ValueError("No config to save. Load or provide config first.")
            config = self._config
        else:
            self._config = config
        
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save as YAML
        config_dict = config.model_dump()
        
        with open(self.config_path, 'w') as f:
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2
            )
    
    def _create_default_config(self) -> WhiteMagicConfig:
        """Create default config and save to file.
        
        Returns:
            Default WhiteMagicConfig instance
        """
        config = WhiteMagicConfig()
        self.save(config)
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation.
        
        Examples:
            >>> config_mgr.get("embeddings.provider")
            'local'
            >>> config_mgr.get("search.max_results")
            10
            >>> config_mgr.get("nonexistent.key", "fallback")
            'fallback'
        
        Args:
            key: Config key in dot notation (e.g., 'embeddings.provider')
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        if self._config is None:
            self.load()
        
        parts = key.split('.')
        value = self._config
        
        for part in parts:
            try:
                value = getattr(value, part)
            except AttributeError:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set config value by dot notation and save.
        
        Examples:
            >>> config_mgr.set("embeddings.provider", "openai")
            >>> config_mgr.set("search.max_results", 20)
        
        Args:
            key: Config key in dot notation (e.g., 'embeddings.provider')
            value: Value to set
            
        Raises:
            AttributeError: If key path is invalid
            ValueError: If value is invalid for the field
        """
        if self._config is None:
            self.load()
        
        parts = key.split('.')
        target = self._config
        
        # Navigate to parent object
        for part in parts[:-1]:
            target = getattr(target, part)
        
        # Set the final attribute
        setattr(target, parts[-1], value)
        
        # Save updated config
        self.save()
    
    def reset(self) -> WhiteMagicConfig:
        """Reset config to defaults.
        
        Returns:
            Fresh default config
        """
        self._config = self._create_default_config()
        return self._config
    
    def exists(self) -> bool:
        """Check if config file exists.
        
        Returns:
            True if config file exists
        """
        return self.config_path.exists()
    
    def get_path(self) -> Path:
        """Get config file path.
        
        Returns:
            Path to config file
        """
        return self.config_path


# Global config manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance.
    
    Returns:
        Global ConfigManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager
