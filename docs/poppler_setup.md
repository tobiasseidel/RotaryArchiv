# Poppler Setup für PDF-zu-Bild-Konvertierung

Poppler ist eine Bibliothek, die für die Konvertierung von PDFs zu Bildern benötigt wird (z.B. für Seiten-Vorschauen).

## Installation

### Windows

1. **Download Poppler:**
   - Gehe zu: https://github.com/oschwartz10612/poppler-windows/releases
   - Lade die neueste Version herunter (z.B. `Release-XX.XX.X-X.zip`)

2. **Extrahieren:**
   - Entpacke die ZIP-Datei in dein Projekt-Verzeichnis
   - Beispiel-Struktur:
     ```
     RotaryArchiv/
     ├── poppler/
     │   ├── bin/
     │   │   ├── pdftoppm.exe
     │   │   ├── pdftocairo.exe
     │   │   └── ...
     │   └── ...
     ```

3. **Konfiguration:**
   - Öffne `.env` (oder erstelle es von `.env.example`)
   - Füge den Pfad hinzu:
     ```env
     POPPLER_PATH=./poppler/bin
     ```
   - Oder absoluter Pfad:
     ```env
     POPPLER_PATH=C:/Users/DeinName/RotaryArchiv/poppler/bin
     ```

### Linux/Mac

```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS (mit Homebrew)
brew install poppler

# Falls lokal installiert, in .env konfigurieren:
POPPLER_PATH=/usr/local/bin
```

## Verwendung

Nach der Konfiguration wird Poppler automatisch verwendet für:
- PDF-Seiten-Extraktion als Bilder
- PDF-Vorschau-Generierung
- OCR-Verarbeitung von PDFs

## Git-Ignore

Das `poppler/` Verzeichnis wird automatisch von Git ignoriert (siehe `.gitignore`).
