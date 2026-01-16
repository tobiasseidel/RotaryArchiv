# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- Navigationsmenü mit getrennten Bereichen für "Imports" und "Dokumente"
- Dokument-Gruppierung: Seiten können zu Composite-Dokumenten zusammengefasst werden
- "NEU"-Badge für neu erstellte Dokumente
- Automatisches Zurücksetzen der Seiten-Auswahl nach Gruppierung
- Schema-Erweiterungen: `is_composite`, `parent_document_id`, `page_number` für Composite-Dokumente
- Ruff-Konfiguration für Linting und Formatting
- Pre-commit Hooks für automatische Code-Qualitäts-Checks
- pytest.ini und Coverage-Konfiguration
- Development-Dependencies in requirements-dev.txt
- Makefile für häufige Development-Tasks
- Projekt-Management: TODO.md, BACKLOG.md, WORKLOG.md
- Dokumentation: CHANGELOG.md, CONTRIBUTING.md, LICENSE

### Geändert
- Gruppierung erfordert keinen Titel mehr (wird später beim OCR vergeben)
- Neue Dokumente werden hinten sortiert
- Verbesserte Filterlogik für Composite-Dokumente

### Behoben
- SQLite-spezifische Migration-Probleme mit ALTER TABLE
- Schema-Serialisierung für Composite-Dokumente
- Poppler-Pfad-Konfiguration für PDF-zu-Bild-Konvertierung

## [0.1.0] - 2026-01-15

### Hinzugefügt
- Initiale Projekt-Struktur
- FastAPI Backend mit REST API
- SQLAlchemy Models für Dokumente, Seiten, Entitäten, Triples
- Alembic für Datenbank-Migrationen
- OCR-Pipeline (Tesseract + Ollama Vision)
- Wikidata-Integration
- Frontend für Dokument-Upload und Seiten-Verwaltung
- PDF-Seiten-Extraktion mit Poppler-Unterstützung
- Dokument-Status-Workflow (uploaded → ocr_pending → ocr_done → classified → annotated)

---

## Kategorien

- **Hinzugefügt** für neue Features
- **Geändert** für Änderungen an bestehenden Features
- **Veraltet** für Features, die bald entfernt werden
- **Entfernt** für entfernte Features
- **Behoben** für Bugfixes
- **Sicherheit** für Sicherheits-Updates
