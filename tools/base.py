"""
Pluggable Tool Connector Abstractions for LedgerGuard.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from runtime.models import RiskTier

class BaseTool(ABC):
    """
    Standard interface for all LedgerGuard tools and connectors.
    Provides schema definition, permission tiers, and audit logging hooks.
    """
    name: str
    description: str
    risk_tier: RiskTier

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Executes the tool action and returns a structured dictionary result."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema metadata for agent planner and LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "risk_tier": self.risk_tier.value,
        }

class ToolRegistry:
    """Registry managing available tools in the AI Employee runtime."""
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {name: tool.get_schema() for name, tool in self._tools.items()}
