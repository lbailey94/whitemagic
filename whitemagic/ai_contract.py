"""AI Contract - Machine-readable behavior specification."""

import yaml
from pathlib import Path
from typing import Dict, List

class AIContract:
    """Load and query the AI contract."""
    
    def __init__(self):
        contract_file = Path(__file__).parent / "ai_contract.yaml"
        with open(contract_file) as f:
            self.contract = yaml.safe_load(f)
    
    def get_mandatory_tools(self) -> List[Dict]:
        """Get list of tools AI must use."""
        return self.contract.get("mandatory_tools", [])
    
    def get_phase_actions(self, phase: str) -> List[str]:
        """Get actions for a Wu Xing phase."""
        phases = self.contract.get("phases", {})
        return phases.get(phase, {}).get("actions", [])
    
    def get_token_threshold(self, level: str) -> float:
        """Get token usage threshold."""
        mgmt = self.contract.get("token_management", {})
        return mgmt.get("thresholds", {}).get(level, 0.7)
    
    def should_pause(self, tokens_used: int, tokens_total: int = 200000) -> bool:
        """Check if should pause due to token usage."""
        usage = tokens_used / tokens_total
        danger = self.get_token_threshold("danger")
        return usage >= danger
    
    def get_error_strategy(self, error_type: str) -> List[str]:
        """Get strategy for handling an error."""
        handling = self.contract.get("error_handling", {})
        return handling.get(error_type, [])


def load_contract() -> AIContract:
    """Load the AI contract."""
    return AIContract()
