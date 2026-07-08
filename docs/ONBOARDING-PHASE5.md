# Start-Prompt: Phase 5 MCP Server + Agenten (litellm)

Du arbeitest am **RotaryArchiv** Projekt – einem digitalen Archiv-System für Rotary Club Dokumente mit OCR-Verarbeitung.

## Voraussetzung

Phase 4 ist komplett abgeschlossen:
- ✅ 3 Services mit 63 Tests (OCR, Document, Search)
- ✅ API-Routen refactored (nutzen Services, -38% bis -52% Code-Reduktion)
- ✅ 68/68 Tests grün

Services:
- `src/rotary_archiv/services/ocr_service.py` – OCR-Job-Management
- `src/rotary_archiv/services/document_service.py` – Document-CRUD
- `src/rotary_archiv/services/search_service.py` – Volltextsuche

## Architektur

```
Nutzer → litellm (Agent-Plattform, LLM-Aufrufe, Tool-Handling)
               ↓ MCP (stdio)
         MCP Server (Tools)
               ↓
         Services (Business Logic)
               ↓
         Data Layer (DB, Triple Store, Ollama, Wikidata)
```

**litellm übernimmt:**
- Agent-Loop (Chat Completions + Tool Calls)
- LLM-Integration (Ollama, OpenAI, Anthropic, etc.)
- Auth & Security
- Monitoring & UI

## Deine Aufgabe

Implementiere einen MCP-Server (stdio) der von litellm als Tool-Provider genutzt wird.

**Reihenfolge:**
1. MCP Server (Protocol + Server + Registry)
2. Tools die Services aufrufen
3. litellm-Integration (Config)
4. Agenten-Prompts

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `TODO.md` | Detaillierter Plan mit allen Tests |
| `src/rotary_archiv/services/ocr_service.py` | OCR-Service |
| `src/rotary_archiv/services/document_service.py` | Document-Service |
| `src/rotary_archiv/services/search_service.py` | Search-Service |
| `src/rotary_archiv/core/database.py` | SessionLocal für DB-Zugriff |

## MCP Protocol (Kurz-Zusammenfassung)

Der MCP Server kommuniziert über **stdio** mit newline-delimited JSON:

```json
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
← {"jsonrpc":"2.0","id":1,"result":{"serverInfo":{"name":"rotary-archiv"}}}

→ {"jsonrpc":"2.0","id":2,"method":"tools/list"}
← {"jsonrpc":"2.0","id":2,"result":{"tools":[...]}}

→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_document_detail","arguments":{"document_id":1}}}
← {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"..."}]}}
```

## Vorgehen (pro Schritt)

### 1. MCP Server (Schritt 1)

```bash
# Neue Dateien erstellen:
src/rotary_archiv/mcp/__init__.py
src/rotary_archiv/mcp/protocol.py      # read_message, write_message, make_response, make_error
src/rotary_archiv/mcp/server.py        # MCP Server mit initialize, tools/list, tools/call
src/rotary_archiv/mcp/tool_registry.py # Tool-Definitionen sammeln und dispatchen
tests/test_mcp/__init__.py
tests/test_mcp/test_protocol.py
tests/test_mcp/test_server.py
tests/test_mcp/test_tool_registry.py
```

### 2. TDD-Zyklus (pro Schritt)
1. **Red**: Alle Tests schreiben → Tests schlagen fehl
2. **Green**: Code implementieren → Tests werden grün
3. **Refactor**: Code refactorn → Tests bleiben grün

### 3. Quality Checks
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_mcp/ -v
.\venv\Scripts\python.exe -m ruff check src/rotary_archiv/mcp/
.\venv\Scripts\python.exe -m ruff format --check src/rotary_archiv/mcp/
```

## MCP Server Design

### Protocol (protocol.py)

```python
import json
import sys
from typing import Any

def read_message() -> dict[str, Any]:
    """Liest eine JSON-RPC Nachricht von stdin."""
    line = sys.stdin.readline()
    if not line:
        raise EOFError()
    return json.loads(line)

def write_message(msg: dict[str, Any]) -> None:
    """Schreibt eine JSON-RPC Nachricht nach stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def make_response(request_id: int | str, result: Any) -> dict:
    """Erstellt eine erfolgreiche Response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def make_error(request_id: int | str, code: int, message: str) -> dict:
    """Erstellt eine Fehler-Response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
```

### Server (server.py)

```python
import json
from src.rotary_archiv.mcp.protocol import read_message, write_message, make_response, make_error
from src.rotary_archiv.mcp.tool_registry import registry

SERVER_INFO = {"name": "rotary-archiv", "version": "1.0.0"}
CAPABILITIES = {"tools": {"listChanged": False}}

def handle_request(request: dict) -> dict:
    """Verarbeitet eine JSON-RPC Anfrage."""
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return make_response(request_id, {"serverInfo": SERVER_INFO, "capabilities": CAPABILITIES})
    elif method == "tools/list":
        return make_response(request_id, {"tools": registry.list_tools()})
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            result = registry.call_tool(tool_name, arguments)
            return make_response(request_id, {"content": [{"type": "text", "text": json.dumps(result)}]})
        except Exception as e:
            return make_error(request_id, -32000, str(e))
    else:
        return make_error(request_id, -32601, f"Unknown method: {method}")

def main():
    """Hauptschleife des MCP Servers."""
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
```

### Tool Registry (tool_registry.py)

```python
from typing import Any, Callable
from pydantic import BaseModel

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[ToolDefinition, Callable]] = {}

    def register(self, definition: ToolDefinition, handler: Callable):
        self._tools[definition.name] = (definition, handler)

    def list_tools(self) -> list[dict]:
        return [t.model_dump() for t, _ in self._tools.values()]

    def call_tool(self, name: str, arguments: dict) -> Any:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        _, handler = self._tools[name]
        return handler(**arguments)

registry = ToolRegistry()
```

## DB-Zugriff in Tools

```python
from src.rotary_archiv.core.database import SessionLocal

def get_document_tool(document_id: int) -> dict:
    db = SessionLocal()
    try:
        return document_service.get_document(db, document_id)
    finally:
        db.close()
```

## Tool-Beispiel

```python
# mcp/tools/documents.py
from src.rotary_archiv.mcp.tool_registry import registry, ToolDefinition
from src.rotary_archiv.services import document_service
from src.rotary_archiv.core.database import SessionLocal

def get_document_detail(document_id: int) -> dict:
    db = SessionLocal()
    try:
        doc = document_service.get_document(db, document_id)
        return {"id": doc.id, "filename": doc.filename, "status": doc.status}
    finally:
        db.close()

registry.register(
    ToolDefinition(
        name="get_document_detail",
        description="Hole Detailinformationen zu einem Dokument",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "ID des Dokuments"}
            },
            "required": ["document_id"]
        }
    ),
    get_document_detail
)
```

## litellm-Integration (Schritt 3)

### litellm_config.yaml

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
  - model_name: ollama-local
    litellm_params:
      model: ollama/deepseek-ocr
      api_base: http://localhost:11434

mcp_servers:
  rotary_archiv:
    transport: "stdio"
    command: "python"
    args: ["-m", "src.rotary_archiv.mcp.server"]
    description: "RotaryArchiv - Dokumente, OCR, Suche"

litellm_settings:
  mcp_aliases:
    "archiv": "rotary_archiv"
```

### Starten

```bash
# litellm starten
litellm --config litellm_config.yaml

# Oder mit Docker
docker run -v ./litellm_config.yaml:/app/config.yaml ghcr.io/berriai/litellm:main-latest --config /app/config.yaml
```

### Tool-Aufruf über litellm

```bash
# Tools aufrufen
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Zeige mir alle Dokumente"}],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

## Test-Beispiel

```python
# tests/test_mcp/test_server.py
import json
from src.rotary_archiv.mcp.server import handle_request

def test_initialize():
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    response = handle_request(request)
    assert response["result"]["serverInfo"]["name"] == "rotary-archiv"

def test_tools_list():
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    response = handle_request(request)
    assert "tools" in response["result"]
    assert isinstance(response["result"]["tools"], list)

def test_tools_call_unknown():
    request = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "unknown_tool", "arguments": {}}}
    response = handle_request(request)
    assert "error" in response
    assert response["error"]["code"] == -32601
```

## Commits

Nach jedem abgeschlossenen Schritt:
```bash
git add -A
git commit -m "feat(mcp): add MCP server with tools for ocr/document/search"
```
