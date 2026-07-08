"""MCP SSE Server - HTTP endpoint for litellm integration."""

import asyncio
import json

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

from src.rotary_archiv.mcp.protocol import make_error, make_response
from src.rotary_archiv.mcp.tool_registry import registry

# Import tools to register them
from src.rotary_archiv.mcp.tools import documents, ocr, search  # noqa: F401

app = FastAPI(title="RotaryArchiv MCP Server", version="1.0.0")

SERVER_INFO = {"name": "rotary-archiv", "version": "1.0.0"}
CAPABILITIES = {"tools": {"listChanged": False}}

# Store for SSE connections
sse_connections: dict[str, asyncio.Queue] = {}


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol."""
    connection_id = str(id(request))
    queue: asyncio.Queue = asyncio.Queue()
    sse_connections[connection_id] = queue

    async def event_generator():
        try:
            # Send endpoint URL for message posting
            yield f"event: endpoint\ndata: /messages?session_id={connection_id}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        finally:
            sse_connections.pop(connection_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/messages")
async def messages_endpoint(request: Request, session_id: str | None = None):
    """Handle incoming JSON-RPC messages."""
    body = await request.json()

    # Handle initialize
    if body.get("method") == "initialize":
        response = make_response(
            body.get("id"),
            {
                "serverInfo": SERVER_INFO,
                "capabilities": CAPABILITIES,
            },
        )
        if session_id and session_id in sse_connections:
            await sse_connections[session_id].put(response)
        return {"status": "ok"}

    # Handle tools/list
    if body.get("method") == "tools/list":
        response = make_response(body.get("id"), {"tools": registry.list_tools()})
        if session_id and session_id in sse_connections:
            await sse_connections[session_id].put(response)
        return {"status": "ok"}

    # Handle tools/call
    if body.get("method") == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        try:
            result = registry.call_tool(tool_name, arguments)
            response = make_response(
                body.get("id"),
                {"content": [{"type": "text", "text": json.dumps(result)}]},
            )
        except Exception as e:
            response = make_error(body.get("id"), -32000, str(e))

        if session_id and session_id in sse_connections:
            await sse_connections[session_id].put(response)
        return {"status": "ok"}

    # Unknown method
    response = make_error(
        body.get("id"), -32601, f"Unknown method: {body.get('method')}"
    )
    if session_id and session_id in sse_connections:
        await sse_connections[session_id].put(response)
    return {"status": "ok"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "server": SERVER_INFO}


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "RotaryArchiv MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
