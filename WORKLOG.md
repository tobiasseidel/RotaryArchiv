# Worklog - Entwicklungs-Logbuch

Dieses Logbuch dokumentiert die Entwicklung des RotaryArchiv-Projekts.

## Format

Jeder Eintrag sollte folgende Informationen enthalten:
- **Datum**: YYYY-MM-DD
- **Feature/Bugfix**: Kurze Beschreibung
- **Änderungen**: Was wurde geändert/hinzugefügt
- **Commits**: Relevante Commit-Hashes
- **Notizen**: Besondere Herausforderungen, Learnings, etc.

---

## 2026-01-15

### Feature: Navigationsmenü und Dokument-Gruppierung

**Änderungen:**
- Navigationsmenü oben mit getrennten Bereichen für "Imports" und "Dokumente"
- Gruppierung von Seiten zu Composite-Dokumenten ohne Titel-Prompt
- Automatisches Zurücksetzen der Seiten-Auswahl nach Gruppierung
- Neue Dokumente werden hinten sortiert und mit "NEU"-Badge markiert
- Schema-Erweiterungen: `is_composite`, `parent_document_id`, `page_number` in `DocumentResponse`

**Commits:**
- `91951ba`: UI: Navigationsmenue, Gruppierung ohne Titel und Schema-Erweiterungen

**Notizen:**
- FastAPI lädt Schema-Änderungen nicht immer automatisch neu - Server-Neustart erforderlich
- SQLite-spezifische Migration-Probleme mit ALTER TABLE gelöst
- Poppler-Pfad-Konfiguration für PDF-zu-Bild-Konvertierung hinzugefügt

---

## 2026-01-15

### Setup: Entwicklungssetup vervollständigen

**Änderungen:**
- Ruff-Konfiguration für Linting und Formatting
- Pre-commit Hooks eingerichtet
- pytest.ini und Coverage-Konfiguration
- Development-Dependencies in requirements-dev.txt
- Makefile für häufige Tasks
- Projekt-Management: TODO.md, BACKLOG.md, WORKLOG.md
- Dokumentation: CHANGELOG.md, CONTRIBUTING.md, LICENSE

**Notizen:**
- Ruff als moderner, schneller Linter gewählt (ersetzt Flake8 + Black + isort)
- Pre-commit Hooks für automatische Code-Qualitäts-Checks
- Makefile für plattformübergreifende Entwicklung (mit PowerShell-Fallback)

---

## Template für neue Einträge

```markdown
## YYYY-MM-DD

### Feature/Bugfix: [Kurze Beschreibung]

**Änderungen:**
- Änderung 1
- Änderung 2

**Commits:**
- `commit-hash`: Commit-Nachricht

**Notizen:**
- Besondere Herausforderungen oder Learnings
```

---

**Hinweis**: Dieses Logbuch sollte regelmäßig aktualisiert werden, um die Projekt-Historie nachvollziehbar zu machen.
