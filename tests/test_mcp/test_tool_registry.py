"""Tests for MCP Tool Registry."""

import pytest

from src.rotary_archiv.mcp.tool_registry import ToolDefinition, ToolRegistry


@pytest.fixture
def registry():
    """Erstellt eine fresh Registry für jeden Test."""
    return ToolRegistry()


class TestToolDefinition:
    """Tests für ToolDefinition Model."""

    def test_tool_definition_minimal(self):
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object", "properties": {}}

    def test_tool_definition_with_properties(self):
        tool = ToolDefinition(
            name="get_document",
            description="Get document details",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "integer", "description": "Document ID"}
                },
                "required": ["document_id"],
            },
        )
        assert tool.name == "get_document"
        assert "document_id" in tool.input_schema["properties"]


class TestToolRegistry:
    """Tests für ToolRegistry."""

    def test_register_tool(self, registry):
        def handler(x: int) -> int:
            return x * 2

        tool_def = ToolDefinition(
            name="double",
            description="Doubles a number",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
        )
        registry.register(tool_def, handler)
        tools = registry.list_tools()
        assert any(t["name"] == "double" for t in tools)

    def test_list_tools_empty(self, registry):
        tools = registry.list_tools()
        assert tools == []

    def test_list_tools_returns_dicts(self, registry):
        def handler():
            return "ok"

        registry.register(
            ToolDefinition(
                name="test",
                description="Test",
                input_schema={"type": "object", "properties": {}},
            ),
            handler,
        )
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test"

    def test_call_tool_success(self, registry):
        def add(a: int, b: int) -> int:
            return a + b

        registry.register(
            ToolDefinition(
                name="add",
                description="Adds two numbers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                },
            ),
            add,
        )
        result = registry.call_tool("add", {"a": 2, "b": 3})
        assert result == 5

    def test_call_tool_unknown(self, registry):
        with pytest.raises(ValueError, match="Unknown tool: unknown"):
            registry.call_tool("unknown", {})

    def test_register_multiple_tools(self, registry):
        def handler1():
            return 1

        def handler2():
            return 2

        registry.register(
            ToolDefinition(
                name="tool1",
                description="Tool 1",
                input_schema={"type": "object", "properties": {}},
            ),
            handler1,
        )
        registry.register(
            ToolDefinition(
                name="tool2",
                description="Tool 2",
                input_schema={"type": "object", "properties": {}},
            ),
            handler2,
        )
        assert len(registry.list_tools()) == 2
        assert registry.call_tool("tool1", {}) == 1
        assert registry.call_tool("tool2", {}) == 2

    def test_register_overwrites_same_name(self, registry):
        def handler_old():
            return "old"

        def handler_new():
            return "new"

        registry.register(
            ToolDefinition(
                name="mytool",
                description="Old",
                input_schema={"type": "object", "properties": {}},
            ),
            handler_old,
        )
        registry.register(
            ToolDefinition(
                name="mytool",
                description="New",
                input_schema={"type": "object", "properties": {}},
            ),
            handler_new,
        )
        assert registry.call_tool("mytool", {}) == "new"
        assert len(registry.list_tools()) == 1
