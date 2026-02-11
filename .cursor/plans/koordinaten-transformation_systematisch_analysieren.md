# Koordinaten-Transformation systematisch analysieren und korrigieren

## Problem-Analyse aus den Logs

### Beobachtungen aus den letzten Logs:
1. **OCR-LLM gibt normalisierte Koordinaten > 1.0 zurück**:
   - Box 0: `bbox=[0.1154, 0.0, 1.5164, 0.44]` → `x2=1.5164` bedeutet 151.64% der Crop-Bild-Breite
   - Box 1: `y2=2.4667` bedeutet 246.67% der Crop-Bild-Höhe
   - Box 2: `y2=2.96` bedeutet 296% der Crop-Bild-Höhe

2. **Transformation führt zu Werten außerhalb der Region**:
   - Box 0: `x2_original=1457` aber Region endet bei `x2_region=985`
   - Box 1: `y2_original=1298` aber Region endet bei `y2_region=968`

3. **Alle Boxen werden gefiltert** wegen "außerhalb Region"

## Root Cause Hypothesis

**Hypothese 1**: Die normalisierten Koordinaten vom OCR-LLM sind relativ zum **Crop-Bild**, aber das Crop-Bild wurde mit `* 0.7` erstellt. Die Transformation muss das berücksichtigen.

**Hypothese 2**: Die normalisierten Koordinaten > 1.0 bedeuten, dass das OCR-LLM Pixel-Koordinaten zurückgibt, die größer sind als das Crop-Bild. Das könnte ein Problem mit der Bildgröße oder dem OCR-Prompt sein.

**Hypothese 3**: Die Transformation selbst ist falsch - wir müssen verstehen, was die normalisierten Koordinaten wirklich bedeuten.

## Plan: Systematische Analyse mit Feedback-Schleifen

### Phase 1: Verstehen der Datenquelle (OCR-LLM)

#### Schritt 1.1: Analysiere OCR-LLM Output-Format
**Datei**: `src/rotary_archiv/ocr/ollama_vision.py`

**Fragen zu klären**:
- Gibt das OCR-LLM Pixel-Koordinaten oder normalisierte Koordinaten zurück?
- Was bedeuten Werte > 1.0 in den normalisierten Koordinaten?
- Wie werden die Koordinaten normalisiert?

**Test 1.1.1**: Erstelle ein Test-Crop-Bild mit bekannter Größe (z.B. 100x100 Pixel)
- Führe OCR durch
- Prüfe die zurückgegebenen Koordinaten
- Dokumentiere: Sind es Pixel oder normalisiert? Was bedeuten Werte > 1.0?

**Erwartetes Ergebnis**: Klarheit darüber, was das OCR-LLM zurückgibt

**Feedback-Schleife**: Wenn unklar, füge Debug-Logging hinzu, um die rohen OCR-Antworten zu sehen

#### Schritt 1.2: Prüfe Normalisierungs-Logik
**Datei**: `src/rotary_archiv/ocr/ollama_vision.py` (Zeile 273-280)

**Aktuelle Logik**:
```python
bbox_normalized = [
    x1 / image_width,  # x_min (relativ)
    y1 / image_height,  # y_min (relativ)
    x2 / image_width,  # x_max (relativ)
    y2 / image_height,  # y_max (relativ)
]
```

**Frage**: Wenn `x2 > image_width`, dann `x2_normalized > 1.0`. Ist das korrekt?

**Test 1.2.1**: Erstelle ein Test-Crop-Bild und prüfe:
- Was gibt das OCR-LLM zurück? (Pixel oder bereits normalisiert?)
- Werden die Pixel-Koordinaten korrekt normalisiert?
- Was passiert, wenn Pixel-Koordinaten > Bildgröße sind?

**Erwartetes Ergebnis**: Verständnis der Normalisierungs-Logik

### Phase 2: Verstehen der Transformationskette

#### Schritt 2.1: Dokumentiere die komplette Transformationskette

**Transformationskette (aktuell)**:

1. **Leaflet → OCR-Koordinaten** (Frontend):
   - `scaleX_display = (mapImageWidth/ocrImageWidth) * 0.7`
   - `x_ocr = x_map / scaleX_display`
   - `y_ocr = ocrImageHeight - (y_map / scaleY_display)`

2. **OCR-Koordinaten → Crop-Bild** (Backend):
   - Original-Koordinaten: `[x1_original, y1_original, x2_original, y2_original]`
   - Crop-Koordinaten: `[x1_original * 0.7, y1_original, x2_original * 0.7, y2_original]`
   - Crop-Bild-Größe: `(x2_original - x1_original) * 0.7 x (y2_original - y1_original)`

3. **OCR-LLM → Normalisierte Koordinaten**:
   - OCR gibt Pixel-Koordinaten zurück: `[x1_pixel, y1_pixel, x2_pixel, y2_pixel]`
   - Normalisiert: `[x1_pixel/crop_width, y1_pixel/crop_height, x2_pixel/crop_width, y2_pixel/crop_height]`
   - **PROBLEM**: Wenn `x2_pixel > crop_width`, dann `x2_normalized > 1.0`

4. **Normalisierte Koordinaten → OCR-Koordinaten** (Worker):
   - Aktuell: `x1_original = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)`
   - **FRAGE**: Ist das korrekt?

#### Schritt 2.2: Erstelle Testfälle mit bekannten Werten

**Test 2.2.1: Einfacher Fall (normale Box innerhalb Crop-Bild)**
- Region: `[100, 200, 500, 400]` (400x200 Pixel)
- Crop-Bild: `[70, 200, 350, 400]` (280x200 Pixel, da 400 * 0.7 = 280)
- OCR gibt zurück: Pixel `[10, 20, 270, 180]` (Box innerhalb Crop-Bild)
- Normalisiert: `[10/280, 20/200, 270/280, 180/200]` = `[0.036, 0.1, 0.964, 0.9]`
- **Erwartete Transformation**: `x1_original = 100 + (0.036 * 280 / 0.7) = 100 + 14.4 = 114`
- **Erwartete Transformation**: `x2_original = 100 + (0.964 * 280 / 0.7) = 100 + 385.6 = 485`
- **Erwartete Transformation**: `y1_original = 200 + (0.1 * 200) = 200 + 20 = 220`
- **Erwartete Transformation**: `y2_original = 200 + (0.9 * 200) = 200 + 180 = 380`

**Test 2.2.2: Box geht über Crop-Bild hinaus (normalized > 1.0)**
- Region: `[100, 200, 500, 400]` (400x200 Pixel)
- Crop-Bild: `[70, 200, 350, 400]` (280x200 Pixel)
- OCR gibt zurück: Pixel `[10, 20, 300, 180]` (x2=300 > crop_width=280)
- Normalisiert: `[10/280, 20/200, 300/280, 180/200]` = `[0.036, 0.1, 1.071, 0.9]`
- **FRAGE**: Wie sollen wir das transformieren?
  - Option A: Begrenzen auf Crop-Bild-Größe: `x2_normalized = 1.0` → `x2_original = 100 + (1.0 * 280 / 0.7) = 500` (Region-Ende)
  - Option B: Verwende originalen Wert: `x2_original = 100 + (1.071 * 280 / 0.7) = 100 + 428.4 = 528` (über Region hinaus)
  - Option C: Andere Transformation?

**Test 2.2.3: Verifiziere mit tatsächlichen Daten**
- Verwende die Logs vom letzten Test:
  - Region: `[69, 743, 985, 968]` (916x225 Pixel)
  - Crop-Bild: `641x225` Pixel (916 * 0.7 = 641.2 ≈ 641)
  - Box 0: Normalized `[0.1154, 0.0, 1.5164, 0.44]`
  - **Berechnung**: `x2_crop_pixel = 1.5164 * 641 = 972` Pixel
  - **Problem**: Crop-Bild ist nur 641 Pixel breit, aber Box geht bis 972 Pixel!

### Phase 3: Identifiziere das eigentliche Problem

#### Schritt 3.1: Prüfe, ob das OCR-LLM die falsche Bildgröße verwendet

**Hypothese**: Das OCR-LLM verwendet möglicherweise die originale Bildgröße statt der Crop-Bild-Größe für die Normalisierung.

**Test 3.1.1**: Füge Debug-Logging hinzu:
- Logge die Bildgröße, die an das OCR-LLM übergeben wird
- Logge die Pixel-Koordinaten, die das OCR-LLM zurückgibt (vor Normalisierung)
- Prüfe, ob `x2_pixel > crop_image_width` oder `y2_pixel > crop_image_height`

**Datei**: `src/rotary_archiv/ocr/ollama_vision.py` (Zeile 294-450)

**Änderung**: Füge Logging hinzu, um zu sehen:
- Welche Bildgröße wird an `extract_text_with_bbox` übergeben?
- Was gibt das OCR-LLM zurück? (Pixel-Koordinaten oder bereits normalisiert?)
- Wie werden die Koordinaten normalisiert?

#### Schritt 3.2: Prüfe die Bildgröße, die an das OCR-LLM übergeben wird

**Frage**: Wird die Crop-Bild-Größe korrekt an das OCR-LLM übergeben?

**Datei**: `src/rotary_archiv/ocr/job_processor.py` (Zeile 655-659)

**Aktueller Code**:
```python
ocr_result_data = await asyncio.to_thread(
    ollama_ocr.extract_text_with_bbox, str(crop_path_obj)
)
```

**Prüfe**: 
- Welche Bildgröße verwendet `extract_text_with_bbox`?
- Wird die Crop-Bild-Größe korrekt ermittelt?

**Test 3.2.1**: Füge Logging hinzu:
```python
from PIL import Image
crop_img = Image.open(crop_path_obj)
logger.info(f"Crop-Bild-Größe (PIL): {crop_img.size}")
ocr_result_data = await asyncio.to_thread(
    ollama_ocr.extract_text_with_bbox, str(crop_path_obj)
)
logger.info(f"OCR-LLM Bild-Größe: {ocr_result_data.get('image_width')}x{ocr_result_data.get('image_height')}")
```

### Phase 4: Korrigiere die Transformation

#### Schritt 4.1: Entscheide über die korrekte Transformation

**Basierend auf den Erkenntnissen aus Phase 1-3**:

**Option A**: Wenn OCR-LLM Pixel-Koordinaten zurückgibt, die relativ zum Crop-Bild sind:
- `x_crop_pixel = x_normalized * crop_image_width`
- `x_original = x1_region + (x_crop_pixel / 0.7)`
- Oder direkt: `x_original = x1_region + ((x_normalized * crop_image_width) / 0.7)`

**Option B**: Wenn OCR-LLM Pixel-Koordinaten zurückgibt, die relativ zur originalen Bildgröße sind:
- Müssen wir anders transformieren

**Option C**: Wenn normalisierte Werte > 1.0 bedeuten, dass die Box über den Rand hinausgeht:
- Sollen wir die Box auf die Region-Größe begrenzen?
- Oder die Box so lassen und nicht filtern?

#### Schritt 4.2: Implementiere die korrekte Transformation

**Nach Klärung der Fragen aus Phase 1-3**

**Test 4.2.1**: Erstelle Unit-Tests für die Transformation:
```python
def test_transform_crop_to_ocr():
    # Test 1: Normale Box innerhalb Crop-Bild
    x1_region, y1_region = 100, 200
    region_width, region_height = 400, 200
    crop_image_width, crop_image_height = 280, 200  # 400 * 0.7 = 280
    x1_norm, y1_norm, x2_norm, y2_norm = 0.036, 0.1, 0.964, 0.9
    
    x1_original = x1_region + int((x1_norm * crop_image_width) / 0.7)
    # Erwartet: 100 + (0.036 * 280 / 0.7) = 100 + 14.4 = 114
    assert x1_original == 114
    
    # Test 2: Box geht über Crop-Bild hinaus (normalized > 1.0)
    x2_norm = 1.071  # Box geht 7.1% über Crop-Bild hinaus
    x2_original = x1_region + int((x2_norm * crop_image_width) / 0.7)
    # Erwartet: 100 + (1.071 * 280 / 0.7) = 100 + 428.4 = 528
    # Aber Region endet bei x2_region = 500
    # Sollte x2_original auf 500 begrenzt werden?
```

#### Schritt 4.3: Entscheide über Filterung vs. Begrenzung

**Aktuell**: Boxen werden gefiltert, wenn sie außerhalb der Region liegen.

**Optionen**:
1. **Begrenzen statt Filtern**: Begrenze Boxen auf die Region-Größe statt sie zu filtern
2. **Toleranz erhöhen**: Erhöhe die Toleranz weiter (z.B. 50% oder 100%)
3. **Keine Filterung**: Entferne die Filterung komplett und begrenze nur auf Bildgrenzen

**Empfehlung**: Option 1 (Begrenzen statt Filtern), da:
- Die Boxen enthalten gültigen Text
- Es besser ist, eine begrenzte Box zu haben als keine Box
- Die Begrenzung kann später korrigiert werden

### Phase 5: Implementierung und Tests

#### Schritt 5.1: Füge Debug-Logging hinzu

**Datei**: `src/rotary_archiv/ocr/job_processor.py`

**Änderungen**:
1. Logge die Crop-Bild-Größe (PIL)
2. Logge die Bildgröße, die das OCR-LLM zurückgibt
3. Logge die Pixel-Koordinaten vom OCR-LLM (vor Normalisierung)
4. Logge die normalisierten Koordinaten
5. Logge jeden Schritt der Transformation

#### Schritt 5.2: Implementiere die korrekte Transformation

**Basierend auf den Erkenntnissen aus Phase 1-4**

#### Schritt 5.3: Implementiere Begrenzung statt Filterung

**Datei**: `src/rotary_archiv/ocr/job_processor.py` (Zeile 811-829)

**Änderung**: Statt Boxen zu filtern, begrenze sie auf die Region-Größe:

```python
# Statt Filterung:
# Begrenze Boxen auf Region-Größe (mit kleiner Toleranz)
x1_original = max(x1_region, min(x1_original, x2_region))
y1_original = max(y1_region, min(y1_original, y2_region))
x2_original = max(x1_original + 1, min(x2_original, x2_region))
y2_original = max(y1_original + 1, min(y2_original, y2_region))

logger.info(
    f"Box {idx}: Begrenzt auf Region: "
    f"Vorher=[{x1_before}, {y1_before}, {x2_before}, {y2_before}], "
    f"Nachher=[{x1_original}, {y1_original}, {x2_original}, {y2_original}]"
)
```

#### Schritt 5.4: Teste mit echten Daten

**Test 5.4.1**: Erstelle eine "+X" Box mit bekannter Region
- Dokumentiere: Region-Koordinaten, Crop-Bild-Größe, OCR-Output
- Prüfe: Werden Boxen erstellt? Sind sie korrekt positioniert?

**Test 5.4.2**: Prüfe die Logs
- Sind alle Transformations-Schritte korrekt?
- Werden Boxen begrenzt statt gefiltert?
- Stimmen die finalen Koordinaten?

**Feedback-Schleife**: Wenn Probleme auftreten, gehe zurück zu Phase 3 und analysiere die Logs

### Phase 6: Verifikation und Abschluss

#### Schritt 6.1: Verifiziere die komplette Transformationskette

**Test 6.1.1**: Roundtrip-Test
1. Erstelle eine Box in Leaflet
2. Verfolge die Koordinaten durch die gesamte Kette
3. Prüfe, ob die finale Box in Leaflet korrekt angezeigt wird

#### Schritt 6.2: Vergleich mit "+1" Box

**Test 6.2.1**: Erstelle eine "+1" Box und eine "+X" Box im gleichen Bereich
- Prüfe: Haben beide Boxen die gleiche Position?
- Prüfe: Stimmen die Koordinaten überein?

#### Schritt 6.3: Edge Cases testen

**Test 6.3.1**: Boxen am Rand der Region
**Test 6.3.2**: Boxen, die über die Region hinausgehen
**Test 6.3.3**: Sehr kleine Boxen
**Test 6.3.4**: Sehr große Boxen

## Feedback-Mechanismen

### Nach jedem Schritt:
1. **Logs prüfen**: Analysiere die Logs, um zu verstehen, was passiert
2. **Ergebnisse dokumentieren**: Dokumentiere die Erkenntnisse
3. **Anpassungen vornehmen**: Passe den Plan basierend auf den Erkenntnissen an

### Nach jeder Phase:
1. **Zusammenfassung**: Fasse die Erkenntnisse zusammen
2. **Nächste Schritte**: Definiere die nächsten Schritte basierend auf den Erkenntnissen
3. **Rückfragen**: Stelle Fragen, wenn etwas unklar ist

## Erwartete Ergebnisse

Nach Abschluss des Plans sollten wir:
1. **Verstehen**, was die normalisierten Koordinaten > 1.0 bedeuten
2. **Verstehen**, wie die Transformation korrekt funktionieren sollte
3. **Haben** eine korrekte Implementierung der Transformation
4. **Haben** Boxen, die korrekt positioniert sind und nicht gefiltert werden

## Nächste Schritte

**Sofort**: Beginne mit Phase 1, Schritt 1.1 - Analysiere das OCR-LLM Output-Format
- Füge Debug-Logging hinzu, um die rohen OCR-Antworten zu sehen
- Dokumentiere, was das OCR-LLM zurückgibt
- Prüfe, ob die Normalisierung korrekt ist
