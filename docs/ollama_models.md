# Ollama Modelle für OCR

## Empfohlene Modelle

### Vision-Modelle (für OCR)

1. **deepseek-ocr** (Empfohlen für OCR)
   - Modell: `deepseek-ocr:3b` oder `deepseek-ocr:latest`
   - Größe: ~3B Parameter
   - Spezialisiert auf OCR und Text-Extraktion
   - Installation: `ollama pull deepseek-ocr:3b`

2. **llava** (Allgemeines Vision-Modell)
   - Modell: `llava:latest`, `llava:13b`, `llava:34b`
   - Größe: 7B, 13B, 34B Parameter
   - Gut für allgemeine Vision-Aufgaben, auch OCR
   - Installation: `ollama pull llava:13b` (empfohlen)

3. **olmocr2** (Spezialisiert auf OCR)
   - Modell: `richardyoung/olmocr2:7b-q8`
   - Größe: ~7B Parameter (Q8 quantisiert)
   - Sehr gut für Tabellen, Handschrift, komplexe Dokumente
   - Installation: `ollama pull richardyoung/olmocr2:7b-q8`

4. **bakllava** (Alternative zu llava)
   - Modell: `bakllava:latest`
   - Größe: ~7B Parameter
   - Installation: `ollama pull bakllava`

### GPT-Modelle (für Text-Korrektur und Vergleich)

1. **llama3** (Empfohlen)
   - Modell: `llama3:8b` oder `llama3:70b`
   - Größe: 8B oder 70B Parameter
   - Gut für Text-Korrektur und Vergleich
   - Installation: `llama3:8b` (für schnelle Ergebnisse) oder `llama3:70b` (für bessere Qualität)

2. **mistral** (Alternative)
   - Modell: `mistral:7b` oder `mistral:latest`
   - Größe: 7B Parameter
   - Installation: `ollama pull mistral:7b`

3. **mixtral** (Für komplexere Aufgaben)
   - Modell: `mixtral:8x7b`
   - Größe: 8x7B Parameter (MoE)
   - Installation: `ollama pull mixtral:8x7b`

## Konfiguration

Die Modelle können in `.env` oder über Umgebungsvariablen konfiguriert werden:

```bash
# Vision-Modell für OCR
OLLAMA_VISION_MODEL=deepseek-ocr:3b
# oder
OLLAMA_VISION_MODEL=llava:13b

# GPT-Modell für Korrektur
OLLAMA_GPT_MODEL=llama3:8b
# oder
OLLAMA_GPT_MODEL=llama3:70b
```

## Empfehlung für Start

Für den Start empfehle ich:
- **Vision**: `deepseek-ocr:3b` (schnell, spezialisiert) oder `llava:13b` (allgemeiner)
- **GPT**: `llama3:8b` (schnell) oder `llama3:70b` (besser)

## Installation

```bash
# Vision-Modell
ollama pull deepseek-ocr:3b
# oder
ollama pull llava:13b

# GPT-Modell
ollama pull llama3:8b
# oder
ollama pull llama3:70b
```

## API-Endpunkt

Die Ollama-API läuft standardmäßig auf `http://localhost:11434`.

Die aktuelle Implementierung verwendet:
- `/api/generate` für Vision-Modelle (mit `images` Parameter)
- `/api/generate` für GPT-Modelle (ohne `images` Parameter)

Dies ist korrekt für die meisten Ollama-Modelle.
