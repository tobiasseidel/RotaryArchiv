# Prompt-Vergleich: Ursprüngliche OCR vs. Multibox-Region

## Aktuelle Prompts

### Ursprüngliche OCR (ganze Seite)
**Datei**: `src/rotary_archiv/ocr/pipeline.py`
- Verwendet: `extract_text_with_bbox(file_path_str)` ohne expliziten Prompt
- Standard-Prompt: `<|grounding|>Extract text with bounding boxes.`
- Bild: Vollständiges Bild (z.B. 694x1000 Pixel)
- Koordinaten: Relativ zum vollständigen Bild

### Multibox-Region ("+X")
**Datei**: `src/rotary_archiv/ocr/job_processor.py`
- Verwendet: `extract_text_with_bbox(crop_path)` ohne expliziten Prompt
- Standard-Prompt: `<|grounding|>Extract text with bounding boxes.`
- Bild: Crop-Bild (z.B. 639x239 Pixel)
- Koordinaten: Sollten relativ zum Crop-Bild sein, aber OCR gibt Werte zurück, die größer sind als das Crop-Bild

## Problem

**Beide verwenden den gleichen Prompt**, aber:
- Ursprüngliche OCR: Koordinaten sind relativ zum vollständigen Bild ✓
- Multibox-Region: Koordinaten sollten relativ zum Crop-Bild sein, aber OCR gibt Werte zurück, die größer sind als das Crop-Bild ❌

**Mögliche Ursache**: Der Prompt ist zu vage und gibt keine klaren Anweisungen über das Koordinatensystem.

## Lösung: Spezifischerer Prompt für Multibox-Region

Der Prompt sollte klar angeben:
1. **Koordinatensystem**: Koordinaten sind relativ zum übergebenen Bild
2. **Format**: Pixel-Koordinaten [x1, y1, x2, y2] mit (0,0) oben links
3. **Bildgröße**: Die Bildgröße sollte im Prompt erwähnt werden

**Vorschlag für Multibox-Region**:
```
<|grounding|>Extract text with bounding boxes. 
The bounding box coordinates must be relative to the provided image.
Coordinates format: [x1, y1, x2, y2] in pixels, where (0,0) is the top-left corner of the image.
The image dimensions are: {image_width}x{image_height} pixels.
```

**ODER noch spezifischer**:
```
<|grounding|>Extract all text from this image with bounding box coordinates.
Important: All bounding box coordinates must be relative to THIS image only.
Format: [x1, y1, x2, y2] in pixels, where:
- (0, 0) is the top-left corner of THIS image
- x increases from left to right
- y increases from top to bottom
- Image size: {image_width}x{image_height} pixels
```

## Vergleich mit ursprünglicher OCR

**Ursprüngliche OCR** könnte auch einen spezifischeren Prompt bekommen:
```
<|grounding|>Extract all text from this full page image with bounding box coordinates.
Coordinates format: [x1, y1, x2, y2] in pixels, relative to this image.
Image dimensions: {image_width}x{image_height} pixels.
```

## Empfehlung

1. **Für Multibox-Region**: Verwende einen spezifischeren Prompt, der klar angibt, dass Koordinaten relativ zum übergebenen Bild sein sollen
2. **Für ursprüngliche OCR**: Kann den gleichen spezifischeren Prompt verwenden
3. **Konsistenz**: Beide sollten den gleichen Prompt-Stil verwenden, nur die Bildgröße ändert sich
