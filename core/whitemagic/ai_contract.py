"""AI Contract compatibility layer (Group A — resurfaced from archive)."""

from datetime import datetime
from typing import Any


class AIContract:
    """AI Contract for agent capabilities and constraints."""

    def __init__(
        self,
        agent_id: str = "",
        capabilities: list[str] | None = None,
        constraints: list[str] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self.constraints = constraints or []

    def validate_action(self, action: str) -> bool:
        """Validate if action is within contract."""
        if action.startswith("memory_") and "memory" in self.capabilities:
            return True
        if action.startswith("reasoning_") and "reasoning" in self.capabilities:
            return True
        if action.startswith("system_") and "system" in self.capabilities:
            return True
        if action in self.capabilities:
            return True
        return False


class ContractEnforcer:
    """Enforces AI contracts."""

    def __init__(self) -> None:
        self.contracts: dict[str, AIContract] = {}
        self.violations: list[dict[str, Any]] = []

    def create_contract(
        self,
        agent_id: str,
        allowed_actions: list[str] | None = None,
        forbidden_actions: list[str] | None = None,
    ) -> AIContract:
        """Create a new contract."""
        contract = AIContract(
            agent_id=agent_id,
            capabilities=allowed_actions or [],
            constraints=forbidden_actions or [],
        )
        self.contracts[agent_id] = contract
        return contract

    def enforce(self, agent_id: str, action: str) -> bool:
        """Enforce contract for agent action."""
        contract = self.contracts.get(agent_id)
        if not contract:
            return False
        return contract.validate_action(action)

    def check_permission(self, contract: AIContract, action: str) -> bool:
        """Check if action is permitted by contract."""
        return contract.validate_action(action)

    def log_violation(self, agent_id: str, action: str, reason: str) -> None:
        """Log a contract violation."""
        self.violations.append({
            "agent_id": agent_id,
            "action": action,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    def get_violations(self, agent_id: str) -> list[dict[str, Any]]:
        """Get violations for an agent."""
        return [v for v in self.violations if v["agent_id"] == agent_id]


__all__ = ["AIContract", "ContractEnforcer"]
