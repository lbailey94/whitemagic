"""Interactive setup wizard for WhiteMagic."""

from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from ..config.manager import ConfigManager
from ..config.schema import WhiteMagicConfig
from .tier_configs import TIER_CONFIGS, get_tier_display_name, get_tier_description, get_tier_highlight
from .installer import check_embeddings_installed, install_embeddings_package, download_model, prompt_openai_key
from . import ui

class SetupWizard:
    """Interactive tier-aware setup wizard."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.config_mgr = ConfigManager()
    
    def run(self) -> WhiteMagicConfig:
        """Run complete setup wizard."""
        ui.show_welcome(self.console)
        
        tier = self._ask_tier()
        tier_config = TIER_CONFIGS[tier]
        ui.show_tier_summary(self.console, tier, get_tier_display_name(tier), 
                            get_tier_description(tier), get_tier_highlight(tier))
        
        has_embeddings = check_embeddings_installed()
        ui.show_installation_status(self.console, has_embeddings)
        
        embeddings_choice, api_key = self._configure_embeddings(tier, tier_config, has_embeddings)
        config = self._build_config(tier, tier_config, embeddings_choice, api_key)
        
        self.config_mgr.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_mgr.save(config)
        
        ui.show_completion(self.console, tier, embeddings_choice, str(self.config_mgr.config_path))
        return config
    
    def _ask_tier(self) -> str:
        """Ask user to select tier."""
        ui.show_tier_options(self.console)
        choice = Prompt.ask("Select tier", choices=["1","2","3","4"], default="2")
        return ["personal","power","team","regulated"][int(choice)-1]
    
    def _configure_embeddings(self, tier: str, tier_config: dict, has_embeddings: bool) -> tuple:
        """Configure embeddings provider."""
        recommended = tier_config["recommendations"]["embeddings"]
        ui.show_embeddings_options(self.console, recommended)
        
        default_choice = "1" if recommended == "local" else "2"
        choice = Prompt.ask("Select provider", choices=["1","2","3"], default=default_choice)
        embeddings_choice = ["local","openai","skip"][int(choice)-1]
        api_key = None
        
        if embeddings_choice == "local" and not has_embeddings:
            if install_embeddings_package(self.console):
                download_model("all-MiniLM-L6-v2", self.console)
            else:
                embeddings_choice = "skip"
        elif embeddings_choice == "openai":
            api_key = prompt_openai_key(self.console)
        
        return embeddings_choice, api_key
    
    def _build_config(self, tier: str, tier_config: dict, embeddings: str, api_key: Optional[str]) -> WhiteMagicConfig:
        """Build configuration from user choices."""
        config = WhiteMagicConfig()
        
        # Tier settings
        config.tier.tier = tier_config["tier"]
        config.tier.draft_review_enabled = tier_config["features"]["draft_review_enabled"]
        config.tier.audit_required = tier_config["features"]["audit_required"]
        config.tier.strict_isolation = tier_config["features"]["strict_isolation"]
        
        # Lifecycle settings
        config.lifecycle.scratch_retention_days = tier_config["lifecycle"]["scratch_retention_days"]
        config.lifecycle.working_retention_days = tier_config["lifecycle"]["working_retention_days"]
        config.lifecycle.auto_archive_enabled = tier_config["lifecycle"]["auto_archive_enabled"]
        config.lifecycle.archive_retention_forever = tier_config["lifecycle"]["archive_retention_forever"]
        
        # Embeddings settings
        if embeddings != "skip":
            config.embeddings.provider = embeddings
            if embeddings == "local":
                config.embeddings.model = "all-MiniLM-L6-v2"
        
        return config
