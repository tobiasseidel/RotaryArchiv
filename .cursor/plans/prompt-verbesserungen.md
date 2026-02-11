# Prompt-Verbesserungen: Konsistente und klare Anweisungen

## Änderungen

### 1. Standard-Prompt verbessert (`ollama_vision.py`)

**Vorher**:
```
<|grounding|>Extract text with bounding boxes.
```

**Jetzt**:
```
<|grounding|>Extract all text from this image with bounding box coordinates. 
IMPORTANT: All bounding box coordinates must be relative to THIS image only. 
Coordinates format: [x1, y1, x2, y2] in pixels, where (0,0) is the top-left corner of THIS image. 
Return coordinates relative to the provided image dimensions.
This image is {image_width}x{image_height} pixels. 
Return coordinates relative to this {image_width}x{image_height} pixel image.
```

### 2. Spezifischer Prompt für Multibox-Region (`job_processor.py`)

**Für Crop-Bilder**:
```
<|grounding|>Extract all text from this image with bounding box coordinates. 
IMPORTANT: All bounding box coordinates must be relative to THIS image only. 
Coordinates format: [x1, y1, x2, y2] in pixels, where (0,0) is the top-left corner of THIS image. 
This image is {crop_image_width}x{crop_image_height} pixels. 
Return coordinates relative to this {crop_image_width}x{crop_image_height} pixel image.
```

## Vorteile

1. **Klarheit**: Prompt gibt explizit an, dass Koordinaten relativ zum übergebenen Bild sein sollen
2. **Konsistenz**: Beide Prompts verwenden den gleichen Stil
3. **Bildgröße**: Bildgröße wird explizit im Prompt erwähnt
4. **Koordinatensystem**: Klare Angabe, dass (0,0) oben links ist

## Erwartete Verbesserungen

- OCR-LLM sollte jetzt klar verstehen, dass Koordinaten relativ zum übergebenen Bild sein sollen
- Weniger Verwirrung über das Koordinatensystem
- Konsistentere Ergebnisse zwischen ursprünglicher OCR und Multibox-Region

## Nächste Schritte

1. Teste mit verbessertem Prompt
2. Prüfe Logs, ob OCR jetzt korrekte Koordinaten zurückgibt
3. Falls immer noch Probleme: Weitere Prompt-Verbesserungen
