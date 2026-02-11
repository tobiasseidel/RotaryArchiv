# Aktueller Stand und nächste Schritte

## Was funktioniert NICHT

1. **Prompt-Problem**: Lange Prompts führen dazu, dass OCR-LLM nur den Prompt wiederholt
   - ✅ **GELÖST**: Zurück zum ursprünglichen einfachen Prompt

2. **Transformation-Problem**: Boxen sind nach links/unten verschoben
   - ⏳ **IN ARBEIT**: Transformation korrigiert (Crop beginnt bei x1_region * 0.7)

3. **OCR gibt keine Boxen zurück**: OCR-LLM wiederholt nur den Prompt
   - ✅ **GELÖST**: Prompt zurückgesetzt

## Was ich geändert habe

### 1. Prompt zurückgesetzt
- **Vorher**: Langer Prompt mit Bildgröße → OCR wiederholt nur Prompt
- **Jetzt**: Ursprünglicher einfacher Prompt: `<|grounding|>Extract text with bounding boxes.`

### 2. Transformation korrigiert
- **Vorher**: `x1_original = x1_region + (x1_crop_pixel / 0.7)`
- **Jetzt**: `x1_original = (x1_region * 0.7) + (x1_crop_pixel / 0.7)`
- **Begründung**: Crop-Bild beginnt bei `x1_region * 0.7`, nicht bei `x1_region`

## Systematisches Vorgehen

### Schritt 1: Prompt funktioniert wieder ✅
- Zurück zum ursprünglichen einfachen Prompt
- OCR sollte jetzt wieder Grounding-Format zurückgeben

### Schritt 2: Transformation testen ⏳
- Teste mit korrigierter Transformation
- Prüfe, ob Boxen korrekt positioniert sind

### Schritt 3: Wenn immer noch Probleme
- Analysiere die Logs systematisch
- Vergleiche mit ursprünglicher OCR
- Dokumentiere die Transformationskette

## Nächste Schritte

1. **Sofort**: Teste mit zurückgesetztem Prompt
2. **Dann**: Prüfe Logs - gibt OCR wieder Grounding-Format zurück?
3. **Wenn ja**: Prüfe Transformation - sind Boxen korrekt positioniert?
4. **Wenn nein**: Analysiere warum OCR kein Grounding-Format zurückgibt

## Wichtig: Nicht im Kreis drehen!

- ✅ Prompt-Problem gelöst (zurück zum ursprünglichen)
- ⏳ Transformation korrigiert (muss getestet werden)
- ⏳ Systematisch testen und analysieren
