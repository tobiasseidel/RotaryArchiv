# Bestandsaufnahme RotaryArchiv-Projekt
## Analyse zum Stand 2026-05-01

## Sinn und Zweck
RotaryArchiv ist ein digitales Archiv-System für Rotary Club Dokumente mit OCR-Verarbeitung. Es ermöglicht:
- PDF-Upload und automatische Texterkennung mit Ollama Vision
- Seitenweise Job-Verarbeitung in einer Warteschlange
- Speicherung von OCR-Ergebnissen mit dokument-, seiten- und positionsbezogenen Referenzen (BBox)

## Strukturanalyse

### Backend (API-Server)
- **FastAPI-Anwendung** in `src/rotary_archiv/main.py`
- **Modulare API-Endpoints** unter `src/rotary_archiv/api/` für:
  - Dokumente (`documents.py`)
  - OCR-Verarbeitung (`ocr.py`)
  - Seitenverwaltung (`pages.py`)
  - Review-System (`review.py`)
  - Qualitätsmetriken (`quality.py`)
  - Erschließung (`erschliessung.py`, `erschliessung_overview.py`)
  - Einstellungen (`settings.py`)
- **Triple Store** (aktiv): `core/triplestore.py` mit RDFLib für Erschließungs-Daten, persistiert in `data/triplestore.ttl`
- **Authentication/Authorization** noch nicht implementiert (aktuell offen)

### Worker (OCR-Verarbeitung)
- **Separater Hintergrund-Prozess** in `src/rotary_archiv/ocr/worker.py`
- **Job-Verarbeitung** über `src/rotary_archiv/ocr/job_processor.py`
- **OCR-Pipeline** in `src/rotary_archiv/ocr/pipeline.py` (aktuell nur Ollama Vision)
- **Verschiedene Job-Typen**: OCR, BBox-Review, Content-Analysis, etc.

### Frontend (Benutzeroberfläche)
- **Einseitige Webanwendung** in `static/index.html`
- **Vanilla JavaScript** ohne Framework
- **Tab-basierte Navigation** für verschiedene Views (Import, Review, Qualität, etc.)
- **Interaktive Karten-Komponente** mit Leaflet für Erschließungs-Daten
- **Modal-Dialogs** für komplexe Interaktionen (Einheit bearbeiten, etc.)

## Datenmodell und Datenbankstruktur
- **SQLAlchemy ORM** mit SQLite/PostgreSQL-Unterstützung
- **Kern-Modelle** in `src/rotary_archiv/core/models.py`:
  - `Document`: Hauptdokument mit Metadaten
  - `DocumentPage`: Einzelne Seiten
  - `OCRJob`: Asynchrone Verarbeitungsaufträge
  - `OCRResult`: OCR-Ergebnisse verschiedener Quellen
  - `BBox`: Einzelne Bounding Boxes mit Review-Status
  - `DocumentUnit`: Inhaltseinheiten aus mehreren Seiten
  - `ErschliessungsBox`: Für Triple-Store-Integration
- **Migrationen** über Alembic in `alembic/`

## Abhängigkeiten und Schnittstellen
- **Backend ↔ Worker**: Kommunikation ausschließlich über Datenbank (OCRJob-Tabelle)
- **Backend ↔ Frontend**: RESTful API über FastAPI
- **Worker ↔ Externe Dienste**: Ollama Vision (lokal), optional Tesseract
- **Backend ↔ Triple Store**: RDFLib mit Turtle-Persistenz in `data/triplestore.ttl`
- **Konfiguration**: Über `.env`-Datei und `src/rotary_archiv/config.py`

## Identifizierte Unklarheiten und Verbesserungspotentiale

### Architektur
1. **Starke Kopplung zwischen Komponenten** durch direkte Datenbankzugriffe
2. **Fehlende Schichten** zwischen API, Business Logic und Datenzugriff
3. **Inkonsistente Fehlerbehandlung** in verschiedenen Modulen
4. **Komplexe job_processor.py** (3069 Zeilen) mit vielen unterschiedlichen Job-Typen

### Code-Qualität
1. **Lange Funktionen** mit mehreren Verantwortlichkeiten
2. **Wiederholende Code-Muster** (z.B. DB-Session-Handling in job_processor)
3. **Fehlende Typ-Hints** in vielen Bereichen
4. **Inkommentierter Code** erschwert Wartbarkeit

### Frontend
1. **Große einzelne HTML-Datei** (12050 Zeilen) mit eingebettetem CSS/JS
2. **Fehlende Modularisierung** des Frontend-Codes
3. **Direkte DOM-Manipulation** ohne Framework-Abstraktion
4. **Komplexe Zustandsverwaltung** im JavaScript-Code

### Datenmodell
1. **Legacy-Felder** in Dokument-Modell (ocr_text, ocr_text_tesseract, etc.) die entfernt werden sollten
2. **Komplexe JSON-Felder** die teilweise in normale Beziehungen umgewandelt werden könnten
3. **Fehlende Indizes** auf häufig abgefragten Spalten

### Testing
1. **Begrenzte Testabdeckung** erkennbar durch Teststruktur
2. **Fehlende Integrationstests** zwischen Backend und Worker
3. **Unit-Tests** hauptsächlich auf API-Ebene

### Konfiguration und Deployment
1. **Mehrere Startskripte** (PowerShell) die konsolidiert werden könnten
2. **Komplexe Umgebungskonfiguration** über .env-Datei
3. **Docker-Integration** vorhanden, aber nur optional (PostgreSQL, Fuseki)

## Empfehlungen für Refactoring und Feature-Planung

### Kurzfristig (1-2 Monate)
1. **Modularisierung des Frontend-Codes** in separate JavaScript-Dateien nach Funktionalität
2. **Einführung eines CSS-Frameworks** (wie Bootstrap) für konsistentes Styling
3. **Aufteilung der job_processor.py** in kleinere, fokussierte Module nach Job-Typ
4. **Einheitliche Fehlerbehandlung** über das gesamte System hinweg
5. **Entfernung legacy OCR-Felder** aus dem Document-Modell nach entsprechender Migration

### Mittelfristig (3-6 Monate)
1. **Einführung einer Service-Schicht** zwischen API und Datenzugriff für bessere Trennung von Zuständigkeiten
2. **Implementierung von Authentication und Authorization** für sicheren Zugriff
3. **Einführung eines Frontend-Frameworks** (React/Vue) für bessere Wartbarkeit und Skalierbarkeit
4. **Optimierung des Datenmodells** durch Normalisierung komplexer JSON-Felder
5. **Erweiterung der Testabdeckung** mit Integrationstests zwischen allen Komponenten

### Langfristig (6+ Monate)
1. **Migration zu einer Microservices-Architektur** für bessere Skalierbarkeit und Technologiefreiheit
2. **Einbindung zusätzlicher OCR-Engines** für erhöhte Robustheit und Qualität
3. **Implementierung eines Caching-Systems** für häufig genutzte OCR-Ergebnisse
4. **Einführung von WebSockets** für Echtzeit-Updates der Job-Queue im Frontend
5. **Vollständige API-Dokumentation** mit OpenAPI/Swagger für externe Entwickler

Diese Analyse bildet die Basis für die weitere Planung von Refactoring-Maßnahmen und Feature-Erweiterungen. Die nächsten Schritte sollten die Priorisierung dieser Punkte und die Erstellung eines konkreten Aktionsplans umfassen.
