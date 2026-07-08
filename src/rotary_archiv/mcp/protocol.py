"""MCP JSON-RPC 2.0 Protocol for stdio communication."""

import json
import sys
from typing import Any


def read_message() -> dict[str, Any]:
    """Reads a JSON-RPC message from stdin."""
    line = sys.stdin.readline()
    if not line:
        raise EOFError()
    return json.loads(line)


def write_message(msg: dict[str, Any]) -> None:
    """Writes a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def make_response(request_id: int | str | None, result: Any) -> dict:
    """Creates a successful JSON-RPC response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id: int | str | None, code: int, message: str) -> dict:
    """Creates a JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
