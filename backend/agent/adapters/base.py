from abc import ABC, abstractmethod
from typing import Any

class ToolAdapter(ABC):
    @abstractmethod
    async def execute(self, tool: str, mcp_server: str, parameters: dict[str, Any]) -> Any:
       ... 
       
    @abstractmethod
    def supports(self, mcp_server: str) -> bool:
        ...