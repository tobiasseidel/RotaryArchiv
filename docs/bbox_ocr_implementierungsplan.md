# BBox OCR Implementierungsplan mit DeepSeek-OCR

## Übersicht

Dieser Plan beschreibt die Implementierung von Bounding-Box-OCR (BBox OCR) mit DeepSeek-OCR, um OCR-Ergebnisse mit Positionsinformationen zu speichern.

## DeepSeek-OCR Eigenschaften

Basierend auf der [DeepSeek-OCR Dokumentation](https://ollama.com/library/deepseek-ocr):

- **Modell**: `deepseek-ocr:latest` oder `deepseek-ocr:3b`
- **Größe**: ~6.7GB
- **Context**: 8K Token
- **Input**: Text + Image
- **Besonderheiten**:
  - Token-effizient für OCR
  - Sehr empfindlich auf Input-Formatierung (Punktuation, Newlines wichtig!)
  - Unterstützt spezielle Prompts mit `<|grounding|>` für Layout-Erkennung
  - Kann strukturierte Ausgaben generieren (Markdown, JSON)

## Anforderungen

1. **Datenmodell-Erweiterung**: Bounding Boxes in `OCRResult` speichern
2. **Prompt-Engineering**: Spezielle Prompts für strukturierte BBox-Ausgabe
3. **Parsing**: BBox-Informationen aus DeepSeek-OCR-Antwort extrahieren
4. **API-Erweiterung**: BBox-Daten in API-Endpoints verfügbar machen

## Implementierungsschritte

### Phase 1: Datenmodell-Erweiterung

#### 1.1 OCRResult-Modell erweitern

**Neue Felder in `OCRResult`**:
```python
# Bounding Boxes (JSON-Format)
bbox_data = Column(JSON, nullable=True)  # Liste von BBox-Objekten
# Format: [
#   {
#     "text": "erkanntes Wort",
#     "bbox": [x1, y1, x2, y2],  # Koordinaten relativ zur Bildgröße (0-1) oder Pixel
#     "confidence": 0.95,  # Optional: Confidence für dieses Wort
#     "line": 1,  # Optional: Zeilennummer
#     "word_index": 0  # Optional: Index innerhalb der Zeile
#   },
#   ...
# ]

# Bild-Dimensionen für BBox-Kontext
image_width = Column(Integer, nullable=True)  # Breite des verarbeiteten Bildes
image_height = Column(Integer, nullable=True)  # Höhe des verarbeiteten Bildes
```

**Migration erstellen**:
```bash
alembic revision --autogenerate -m "add_bbox_fields_to_ocr_result"
```

### Phase 2: DeepSeek-OCR Integration

#### 2.1 Prompt-Strategien für BBox-OCR

DeepSeek-OCR unterstützt verschiedene Prompt-Formate. Für BBox-OCR verwenden wir:

**Option A: JSON-Format (empfohlen)**
```
Extract all text from this image with bounding boxes. Return a JSON array where each object has:
- "text": the recognized text
- "bbox": [x1, y1, x2, y2] coordinates (normalized 0-1)
- "confidence": confidence score (0-1)

Format: [{"text": "...", "bbox": [0.1, 0.2, 0.3, 0.25], "confidence": 0.95}, ...]
```

**Option B: Markdown mit Grounding**
```
<|grounding|>Given the layout of the image, extract all text with bounding box coordinates.
Return in format:
- Text: [text]
- BBox: [x1, y1, x2, y2]
- Confidence: [0-1]
```

**Option C: Strukturierter Text**
```
Extract the text in the image. For each word, provide:
WORD: [text] | BBOX: [x1,y1,x2,y2] | CONF: [0-1]
```

**Empfehlung**: Option A (JSON) ist am einfachsten zu parsen, aber DeepSeek-OCR könnte auch Markdown oder strukturierten Text zurückgeben. Wir implementieren einen flexiblen Parser.

#### 2.2 OllamaVisionOCR erweitern

**Neue Methode in `OllamaVisionOCR`**:
```python
def extract_text_with_bbox(
    self,
    file_path: str,
    prompt: str | None = None,
    return_format: str = "json",  # "json", "markdown", "structured"
) -> dict[str, Any]:
    """
    Extrahiere Text mit Bounding Boxes aus Datei

    Args:
        file_path: Pfad zur Datei
        prompt: Optionaler Prompt (Standard-Prompt wird verwendet wenn None)
        return_format: Gewünschtes Format ("json", "markdown", "structured")

    Returns:
        Dict mit 'text', 'bbox_data', 'image_width', 'image_height', etc.
    """
```

**Standard-Prompt für JSON**:
```python
DEFAULT_BBOX_PROMPT = """Extract all text from this image with bounding boxes.
Return a JSON array where each object has:
- "text": the recognized text
- "bbox": [x1, y1, x2, y2] coordinates (normalized 0-1, where 0,0 is top-left)
- "confidence": confidence score (0-1, optional)

Return ONLY valid JSON, no explanations. Format: [{"text": "...", "bbox": [0.1, 0.2, 0.3, 0.25], "confidence": 0.95}, ...]"""
```

**Bild-Dimensionen erfassen**:
```python
# In extract_text_with_bbox:
from PIL import Image
image = Image.open(file_path)
image_width, image_height = image.size
```

#### 2.3 BBox-Parser implementieren

**Neue Datei**: `src/rotary_archiv/ocr/bbox_parser.py`

```python
"""
Parser für Bounding Box Daten aus DeepSeek-OCR Antworten
"""

import json
import re
from typing import Any

def parse_bbox_response(response_text: str, image_width: int, image_height: int) -> list[dict[str, Any]]:
    """
    Parse BBox-Daten aus DeepSeek-OCR Antwort

    Unterstützt:
    - JSON-Format
    - Markdown-Format
    - Strukturierter Text

    Args:
        response_text: Rohe Antwort von DeepSeek-OCR
        image_width: Breite des Bildes in Pixeln
        image_height: Höhe des Bildes in Pixeln

    Returns:
        Liste von BBox-Objekten
    """
    # Versuche JSON zu parsen
    bbox_data = _try_parse_json(response_text)
    if bbox_data:
        return _normalize_bboxes(bbox_data, image_width, image_height)

    # Versuche Markdown zu parsen
    bbox_data = _try_parse_markdown(response_text)
    if bbox_data:
        return _normalize_bboxes(bbox_data, image_width, image_height)

    # Versuche strukturierten Text zu parsen
    bbox_data = _try_parse_structured(response_text)
    if bbox_data:
        return _normalize_bboxes(bbox_data, image_width, image_height)

    # Fallback: Keine BBox-Daten, nur Text
    return []

def _normalize_bboxes(bbox_data: list[dict], image_width: int, image_height: int) -> list[dict]:
    """
    Normalisiere BBox-Koordinaten (konvertiere Pixel zu 0-1 oder umgekehrt)
    """
    # Annahme: DeepSeek-OCR gibt normalisierte Koordinaten (0-1) zurück
    # Wir speichern beide: normalisiert UND Pixel
    normalized = []
    for item in bbox_data:
        bbox = item.get("bbox", [])
        if len(bbox) == 4:
            # Wenn bereits normalisiert (0-1), behalte es
            if all(0 <= coord <= 1 for coord in bbox):
                normalized.append({
                    "text": item.get("text", ""),
                    "bbox_normalized": bbox,
                    "bbox_pixels": [
                        int(bbox[0] * image_width),
                        int(bbox[1] * image_height),
                        int(bbox[2] * image_width),
                        int(bbox[3] * image_height),
                    ],
                    "confidence": item.get("confidence"),
                })
            # Wenn Pixel-Koordinaten, normalisiere
            else:
                normalized.append({
                    "text": item.get("text", ""),
                    "bbox_normalized": [
                        bbox[0] / image_width,
                        bbox[1] / image_height,
                        bbox[2] / image_width,
                        bbox[3] / image_height,
                    ],
                    "bbox_pixels": bbox,
                    "confidence": item.get("confidence"),
                })
    return normalized
```

### Phase 3: Pipeline-Integration

#### 3.1 OCRPipeline erweitern

**Neue Parameter in `process_page_from_pdf_with_db`**:
```python
async def process_page_from_pdf_with_db(
    self,
    db: Session,
    document_id: int,
    document_page_id: int,
    pdf_path: str,
    page_number: int,
    language: str = "deu+eng",
    use_correction: bool = True,
    extract_bbox: bool = True,  # NEU: BBox-Extraktion aktivieren
) -> list[OCRResult]:
```

**Anpassung der OCR-Verarbeitung**:
```python
if extract_bbox:
    # OCR mit BBox
    ollama_result = await asyncio.to_thread(
        self.ollama_vision.extract_text_with_bbox, temp_path
    )

    # Parse BBox-Daten
    from src.rotary_archiv.ocr.bbox_parser import parse_bbox_response
    bbox_data = parse_bbox_response(
        ollama_result.get("text", ""),
        ollama_result.get("image_width", 0),
        ollama_result.get("image_height", 0),
    )

    ollama_ocr_result.bbox_data = bbox_data
    ollama_ocr_result.image_width = ollama_result.get("image_width")
    ollama_ocr_result.image_height = ollama_result.get("image_height")
else:
    # Standard OCR ohne BBox
    ollama_result = await asyncio.to_thread(
        self.ollama_vision.extract_text, temp_path
    )
```

### Phase 4: API-Erweiterung

#### 4.1 Schemas erweitern

**In `src/rotary_archiv/api/schemas.py`**:
```python
class BBoxItem(BaseModel):
    """Einzelne Bounding Box"""
    text: str
    bbox_normalized: list[float]  # [x1, y1, x2, y2] 0-1
    bbox_pixels: list[int]  # [x1, y1, x2, y2] Pixel
    confidence: float | None = None

class OCRResultResponse(BaseModel):
    """OCR-Ergebnis mit BBox-Daten"""
    id: int
    document_id: int
    document_page_id: int | None
    source: str
    text: str
    bbox_data: list[BBoxItem] | None = None  # NEU
    image_width: int | None = None  # NEU
    image_height: int | None = None  # NEU
    confidence: float | None
    # ... weitere Felder
```

#### 4.2 OCR-Endpoints erweitern

**In `src/rotary_archiv/api/ocr.py`**:
- `GET /api/ocr/results/{id}` - BBox-Daten inkludieren
- `GET /api/ocr/documents/{id}/results` - BBox-Daten inkludieren
- Optional: `GET /api/ocr/results/{id}/bbox` - Nur BBox-Daten

### Phase 5: Testing & Validierung

#### 5.1 Test-Dokumente
- Einfaches Dokument (eine Zeile)
- Mehrspaltiges Dokument
- Tabelle
- Handschrift (falls unterstützt)

#### 5.2 Validierung
- BBox-Koordinaten innerhalb Bildgrenzen?
- Text-Länge stimmt mit Anzahl BBoxes überein?
- Confidence-Werte im erwarteten Bereich?

## Konfiguration

### Environment-Variablen

```bash
# .env
OLLAMA_VISION_MODEL=deepseek-ocr:latest
# oder
OLLAMA_VISION_MODEL=deepseek-ocr:3b

# Optional: BBox-Extraktion standardmäßig aktivieren
OCR_EXTRACT_BBOX=true
```

## Wichtige Hinweise

1. **DeepSeek-OCR Empfindlichkeit**:
   - Prompt-Formatierung ist kritisch
   - Punktuation und Newlines müssen exakt sein
   - Teste verschiedene Prompt-Varianten

2. **Koordinatensystem**:
   - DeepSeek-OCR könnte normalisierte (0-1) oder Pixel-Koordinaten zurückgeben
   - Wir speichern beide Formate für Flexibilität

3. **Performance**:
   - BBox-Extraktion ist langsamer als reine Text-Extraktion
   - Optional machen (Parameter `extract_bbox`)

4. **Fallback**:
   - Wenn BBox-Parsing fehlschlägt, speichere trotzdem den Text
   - Logge Warnung, aber breche nicht ab

5. **Ollama-Version**:
   - DeepSeek-OCR erfordert Ollama v0.13.0 oder später
   - Prüfe Version: `ollama --version`

## Migration-Strategie

1. **Schritt 1**: Datenmodell erweitern (Migration)
2. **Schritt 2**: BBox-Parser implementieren
3. **Schritt 3**: OllamaVisionOCR erweitern
4. **Schritt 4**: Pipeline-Integration (optional, standardmäßig aus)
5. **Schritt 5**: API-Erweiterung
6. **Schritt 6**: Testing mit echten Dokumenten
7. **Schritt 7**: Optional: BBox-Extraktion standardmäßig aktivieren

## Offene Fragen

1. **BBox-Granularität**: Wort-weise, Zeile-weise, oder beides?
   - Empfehlung: Wort-weise (flexibler)

2. **Koordinatensystem**: Normalisiert (0-1) oder Pixel?
   - Empfehlung: Beides speichern

3. **Confidence**: Pro Wort oder nur global?
   - Empfehlung: Pro Wort (wenn verfügbar)

4. **Layout-Erkennung**: Sollen auch Layout-Informationen (Spalten, Absätze) erfasst werden?
   - Für später: Erweiterung möglich

## Referenzen

- [DeepSeek-OCR Dokumentation](https://ollama.com/library/deepseek-ocr)
- [DeepSeek-OCR Arxiv Paper](https://arxiv.org/abs/2510.18234)
