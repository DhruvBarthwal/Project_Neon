from contextlib import AsyncExitStack
from mcp import ClientSession , StdioServerParameters
from mcp.client.stdio import stdio_client
from agent.adapters.base  import ToolAdapter
from typing import Any

class MCPAdapter(ToolAdapter):
    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._stack = AsyncExitStack()
        
    async def connect(self, mcp_server: str, command: str, args: list[str]) -> None:
        params = StdioServerParameters(command=command, args=args)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        self._sessions[mcp_server] = session
        print(f"Connected to {mcp_server}")
        
    async def close(self) -> None:
        await self._stack.aclose()
        
    def supports(self, mcp_server: str) -> bool:
        return mcp_server in self._sessions
    
    async def execute(self, tool: str, mcp_server: str, parameters: dict[str, Any]) -> Any:
        session = self._sessions[mcp_server]
        result = await session.call_tool(tool, parameters)
        return result.content