# litellm-Setup für RotaryArchiv

## Überblick

LiteLLM dient als Agent-Plattform für RotaryArchiv. Es stellt:
- MCP-Gateway für Tool-Aufrufe bereit
- LLM-Integration (Ollama, OpenAI, etc.)
- Agent-Loop (Chat Completions + Tool Calls)
- Admin-UI für Monitoring

## Installation

```bash
# litellm installieren
pip install litellm

# Oder mit Docker
docker pull ghcr.io/berriai/litellm:main-latest
```

## Konfiguration

Die Konfiguration liegt in `litellm_config.yaml`:

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
```

## Starten

### Lokal

```bash
# MCP-Server testen
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m src.rotary_archiv.mcp.server

# litellm starten
litellm --config litellm_config.yaml

# litellm mit Admin-UI
litellm --config litellm_config.yaml --port 4000
```

### Docker

```bash
docker run -p 4000:4000 \
  -v ./litellm_config.yaml:/app/config.yaml \
  -v ./src:/app/src \
  ghcr.io/berriai/litellm:main-latest \
  --config /app/config.yaml
```

## Tools nutzen

### Über REST API

```bash
# Tools aufrufen (mit Tool-Auto-Execution)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Zeige mir alle Dokumente"}],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}],
    "tool_choice": "required"
  }'

# Nur Tools aufrufen (ohne LLM)
curl -X POST http://localhost:4000/mcp-rest/tools/list \
  -H "Content-Type: application/json"
```

### Über Python SDK

```python
import litellm

# Tools konfigurieren
tools = [
    {
        "type": "mcp",
        "server_url": "litellm_proxy",
        "server_label": "archiv"
    }
]

# Chat mit Tools
response = litellm.completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Finde alle Dokumente von 1930"}],
    tools=tools
)
```

## Agenten

### Recherche-Agent

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "system", "content": "Du bist ein Archiv-Rechercheur. Durchsuche das Archiv und synthetisiere Ergebnisse mit Quellenangaben."},
      {"role": "user", "content": "Finde alle Clubvorstände der 1930er"}
    ],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

### OCR-Agent

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-local",
    "messages": [
      {"role": "system", "content": "Du steuerst OCR-Workflows. Starte OCR für Dokumente und überwache den Fortschritt."},
      {"role": "user", "content": "Starte OCR für Dokument 5"}
    ],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

## Troubleshooting

### MCP-Server startet nicht

```bash
# Manuell testen
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m src.rotary_archiv.mcp.server

# Fehler prüfen
python -c "from src.rotary_archiv.mcp.server import main; main()"
```

### Tools werden nicht gefunden

1. MCP-Server in litellm_config.yaml prüfen
2. litellm-Logs prüfen
3. `mcp_aliases` konfigurieren

### LLM-Modell nicht erreichbar

1. Ollama läuft: `curl http://localhost:11434/api/tags`
2. API-Key gesetzt: `echo $OPENAI_API_KEY`
