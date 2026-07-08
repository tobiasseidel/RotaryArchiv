"""Tests for MCP Server."""

import json
from unittest.mock import MagicMock

import pytest

from src.rotary_archiv.mcp.server import CAPABILITIES, SERVER_INFO, handle_request, main
from src.rotary_archiv.mcp.tool_registry import ToolDefinition, ToolRegistry


@pytest.fixture
def registry(monkeypatch):
    """Erstellt eine fresh Registry und patched das globale registry."""
    fresh_registry = ToolRegistry()
    monkeypatch.setattr("src.rotary_archiv.mcp.server.registry", fresh_registry)
    return fresh_registry


class TestHandleInitialize:
    """Tests für initialize Methode."""

    def test_initialize_returns_server_info(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = handle_request(request)
        assert response["result"]["serverInfo"] == SERVER_INFO

    def test_initialize_returns_capabilities(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = handle_request(request)
        assert response["result"]["capabilities"] == CAPABILITIES

    def test_initialize_preserves_id(self):
        request = {"jsonrpc": "2.0", "id": "abc", "method": "initialize", "params": {}}
        response = handle_request(request)
        assert response["id"] == "abc"


class TestHandleToolsList:
    """Tests für tools/list Methode."""

    def test_tools_list_empty(self, registry):
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = handle_request(request)
        assert response["result"]["tools"] == []

    def test_tools_list_with_tools(self, registry):
        def handler():
            return "ok"

        registry.register(
            ToolDefinition(
                name="test_tool",
                description="Test",
                input_schema={"type": "object", "properties": {}},
            ),
            handler,
        )
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = handle_request(request)
        assert len(response["result"]["tools"]) == 1
        assert response["result"]["tools"][0]["name"] == "test_tool"


class TestHandleToolsCall:
    """Tests für tools/call Methode."""

    def test_tools_call_success(self, registry):
        def add(a: int, b: int) -> int:
            return a + b

        registry.register(
            ToolDefinition(
                name="add",
                description="Add numbers",
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
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 2, "b": 3}},
        }
        response = handle_request(request)
        content = json.loads(response["result"]["content"][0]["text"])
        assert content == 5

    def test_tools_call_unknown_tool(self):
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "unknown", "arguments": {}},
        }
        response = handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32000

    def test_tools_call_handler_exception(self, registry):
        def failing_handler():
            raise RuntimeError("Something went wrong")

        registry.register(
            ToolDefinition(
                name="failing",
                description="Fails",
                input_schema={"type": "object", "properties": {}},
            ),
            failing_handler,
        )
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "failing", "arguments": {}},
        }
        response = handle_request(request)
        assert "error" in response
        assert "Something went wrong" in response["error"]["message"]


class TestHandleUnknownMethod:
    """Tests für unbekannte Methoden."""

    def test_unknown_method(self):
        request = {"jsonrpc": "2.0", "id": 4, "method": "unknown/method"}
        response = handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "unknown/method" in response["error"]["message"]


class TestMain:
    """Tests für main Schleife."""

    def test_main_reads_until_eof(self, registry, monkeypatch):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ]
        input_text = "\n".join(json.dumps(m) for m in messages) + "\n"
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(input_text))

        written = []

        def original_write(msg):
            written.append(msg)

        monkeypatch.setattr("sys.stdout", MagicMock(write=original_write))

        main()
        assert len(written) > 0
        response = json.loads(written[0])
        assert "result" in response
