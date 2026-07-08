"""MCP Server - JSON-RPC 2.0 stdio server for litellm integration."""

import json

from src.rotary_archiv.mcp.protocol import (
    make_error,
    make_response,
    read_message,
    write_message,
)
from src.rotary_archiv.mcp.tool_registry import registry

# Import tools to register them
from src.rotary_archiv.mcp.tools import documents, ocr, search  # noqa: F401

SERVER_INFO = {"name": "rotary-archiv", "version": "1.0.0"}
CAPABILITIES = {"tools": {"listChanged": False}}


def handle_request(request: dict) -> dict:
    """Handles a single JSON-RPC request."""
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return make_response(
            request_id, {"serverInfo": SERVER_INFO, "capabilities": CAPABILITIES}
        )
    elif method == "tools/list":
        return make_response(request_id, {"tools": registry.list_tools()})
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            result = registry.call_tool(tool_name, arguments)
            return make_response(
                request_id, {"content": [{"type": "text", "text": json.dumps(result)}]}
            )
        except Exception as e:
            return make_error(request_id, -32000, str(e))
    else:
        return make_error(request_id, -32601, f"Unknown method: {method}")


def main() -> None:
    """Main loop for the MCP server."""
    while True:
        try:
            request = read_message()
            response = handle_request(request)
            write_message(response)
        except EOFError:
            break
        except Exception as e:
            write_message(make_error(None, -32603, str(e)))


if __name__ == "__main__":
    main()
