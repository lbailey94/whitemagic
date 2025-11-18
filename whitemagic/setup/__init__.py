"""Setup wizard for WhiteMagic first-run configuration."""

from .tier_configs import TIER_CONFIGS, TIER_INFO
from .wizard import SetupWizard

__all__ = ["SetupWizard", "TIER_CONFIGS", "TIER_INFO"]
