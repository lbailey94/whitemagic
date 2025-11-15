"""Interactive setup wizard for WhiteMagic."""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..config.manager import ConfigManager
from ..config.schema import WhiteMagicConfig

# Tier configurations
TIER_CONFIGS = {
    "personal": {"tier": "personal", "working_days": 30, "auto_archive": False, "spaces": ["personal"]},
    "power": {"tier": "power", "working_days": 90, "auto_archive": True, "spaces": []},
    "team": {"tier": "team", "working_days": 180, "auto_archive": True, "spaces": ["shared"]},
    "regulated": {"tier": "regulated", "working_days": None, "auto_archive": False, "spaces": []},
}

class SetupWizard:
    """Interactive setup wizard."""
    
    def __init__(self):
        self.console = Console()
        self.config_mgr = ConfigManager()
    
    def run(self) -> WhiteMagicConfig:
        """Run setup wizard."""
        self.console.print(Panel.fit("Welcome to WhiteMagic! 🧠✨", border_style="cyan"))
        
        # Step 1: Tier
        tier = self._ask_tier()
        
        # Step 2: Embeddings
        embeddings = self._ask_embeddings()
        
        # Step 3: Build config
        config = self._build_config(tier, embeddings)
        self.config_mgr.save(config)
        
        self.console.print("\n[green]✓ Setup complete![/green]")
        return config
    
    def _ask_tier(self) -> str:
        """Ask user tier."""
        self.console.print("\n[bold]Select tier:[/bold]")
        self.console.print("1. Personal  2. Power  3. Team  4. Regulated")
        choice = Prompt.ask("Choice", choices=["1","2","3","4"], default="2")
        return ["personal","power","team","regulated"][int(choice)-1]
    
    def _ask_embeddings(self) -> str:
        """Ask embeddings choice."""
        self.console.print("\n[bold]Embeddings:[/bold]")
        self.console.print("1. Local (privacy)  2. OpenAI  3. Skip")
        choice = Prompt.ask("Choice", choices=["1","2","3"], default="1")
        return ["local","openai","skip"][int(choice)-1]
    
    def _build_config(self, tier: str, embeddings: str) -> WhiteMagicConfig:
        """Build config from choices."""
        tier_cfg = TIER_CONFIGS[tier]
        config = WhiteMagicConfig()
        config.tier.tier = tier_cfg["tier"]
        config.lifecycle.working_retention_days = tier_cfg["working_days"]
        config.lifecycle.auto_archive_enabled = tier_cfg["auto_archive"]
        if embeddings != "skip":
            config.embeddings.provider = embeddings
        return config
