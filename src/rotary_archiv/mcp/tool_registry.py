"""MCP Tool Registry for managing and dispatching tools."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolRegistry:
    """Registry for storing and calling MCP tools."""

    def __init__(self):
        self._tools: dict[str, tuple[ToolDefinition, Callable]] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        """Register a tool with its handler."""
        self._tools[definition.name] = (definition, handler)

    def list_tools(self) -> list[dict]:
        """List all registered tools as dicts."""
        return [t.model_dump() for t, _ in self._tools.values()]

    def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a registered tool by name."""
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        _, handler = self._tools[name]
        return handler(**arguments)


# Global registry instance
registry = ToolRegistry()
