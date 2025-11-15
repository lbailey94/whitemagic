"""Setup wizard for WhiteMagic first-run configuration."""

from .wizard import SetupWizard
from .tier_configs import TIER_CONFIGS, TIER_INFO

__all__ = ["SetupWizard", "TIER_CONFIGS", "TIER_INFO"]
