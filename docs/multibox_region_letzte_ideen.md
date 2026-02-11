# Multibox-Region (+X Boxen): Letzte Ideen vor Deaktivierung

Kurze Übersicht der umgesetzten und der möglichen weiteren Maßnahmen.

## Umgesetzt (Stand heute)

### 1. Fallback: Immer mindestens eine Box
- **Problem:** Wenn das OCR-LLM 0 Boxen liefert (oder alle rausgefiltert werden), verschwindet die Region und der Nutzer hat nichts.
- **Lösung:** In beiden Fällen geben wir **eine Box für die ganze Region** zurück, mit Text  
  `[Bitte manuell prüfen – keine Unterboxen erkannt]`.  
  Der Nutzer kann diese Box behalten oder manuell aufteilen.
- **Code:** `job_processor.py` – `_multibox_fallback_region_box()`, Aufruf wenn `detected_bboxes` leer ist oder nach dem Filter `new_bboxes` leer ist.

### 2. Crop-Pfad stabil: Projektordner statt Temp
- **Problem:** Die Crop-Datei wurde mit `tempfile.NamedTemporaryFile` abgelegt. Wenn API und Worker in unterschiedlichen Umgebungen/CWDs laufen oder die Temp-Datei zwischenzeitlich gelöscht wird, findet der Worker die Datei nicht.
- **Lösung:** Crop wird in **`data/multibox_crops/`** gespeichert (z.B. `page_<id>_<uuid>.png`). Beide Prozesse nutzen dasselbe Projektverzeichnis; der Worker löscht die Datei nach erfolgreicher Verarbeitung weiterhin.
- **Code:** `review.py` – Speicherung in `data/multibox_crops`, absoluter Pfad wird in `multibox_crop_path` gespeichert.

### 3. Koordinaten-Transformation (bereits zuvor korrigiert)
- Rückrechnung von Crop-Pixel auf Seitenkoordinaten:  
  `x_original = x1_region + (crop_pixel_x / 0.7)` (analog für x2, y unverändert).  
  Damit liegt die rechte Kante bei „volle Crop-Breite“ korrekt am Region-Ende.

---

## Weitere Ideen (falls es noch nicht reicht)

### A. Tesseract statt (oder zusätzlich zu) Ollama für Multibox
- **Idee:** Auf dem Crop `pytesseract.image_to_data()` ausführen; pro Zeile/Block eine Box aus `left, top, width, height` bauen und in dasselbe Format wie die LLM-Boxen bringen. Dann dieselbe Rücktransformation (Crop → Seite) anwenden.
- **Vorteil:** Kein Halluzinieren, stabile Boxen, oft gute Zeilen-Erkennung.
- **Aufwand:** In `process_multibox_region` einen zweiten Pfad (Tesseract) einbauen; entweder als Ersatz bei 0 Ollama-Boxen oder parallel und Ergebnis mergen.

### B. Vollbild + Region im Prompt (ohne Crop)
- **Idee:** Statt zu croppen: Volles Seitenbild an das LLM senden und im Prompt die Region als Rechteck angeben (z.B. „Return all text boxes that lie inside the rectangle [x1,y1,x2,y2]. Image dimensions: WxH.“). Koordinaten sind dann direkt in Seitenpixel.
- **Risiko:** Große Bilder, Context-Limits, Modell könnte trotzdem falsch antworten. Eher experimentell.

### C. Debug-Ausgabe bei 0 Boxen
- **Idee:** Wenn 0 Boxen zurückkommen: Crop-Bild und Rohantwort des LLMs in einen Debug-Ordner schreiben (z.B. `data/debug/multibox_failures/`). Hilft beim nächsten Debugging, ändert das Verhalten nicht.
- **Code:** In `process_multibox_region` im Fall „keine Boxen“ (vor dem Fallback) Crop kopieren und LLM-Response speichern.

### D. Multibox nur mit Tesseract (Option „ohne LLM“)
- **Idee:** In den Einstellungen oder pro Aufruf wählbar: „Multibox mit Tesseract“ (nur Tesseract-Boxen, wie in A) oder „Multibox mit Ollama“ (wie bisher). Nutzer können auf Tesseract ausweichen, wenn Ollama unzuverlässig ist.

---

## Wenn die Funktion deaktiviert wird

- **Frontend:** Button „+X Boxen“ / Multibox-Region ausblenden oder deaktivieren.
- **Backend:** Endpoint `POST .../bboxes/add-multiple` kann bestehen bleiben (z.B. 410 Gone oder Hinweis „vorübergehend deaktiviert“), oder du entfernst den Aufruf aus dem Frontend und lässt den Endpoint für spätere Reaktivierung drin.
- **Worker:** Verarbeitung von `multibox_region`-Boxen kann unverändert bleiben (Fallback liefert dann immer die eine Region-Box); oder du überspringst im Worker Multibox-Regionen und setzt die temporäre Box auf „failed“, damit sie nicht als normale Box bleibt.

---

## Dateien (Referenz)

| Änderung | Datei |
|----------|--------|
| Fallback-Box, Hilfsfunktion | `src/rotary_archiv/ocr/job_processor.py` |
| Crop in data/multibox_crops | `src/rotary_archiv/api/review.py` |
| Tests | `tests/test_ocr/test_multibox_region.py` |
