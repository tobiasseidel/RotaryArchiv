"""
Hilfsskript zum Prüfen der Poppler-Konfiguration
"""
import os
from pathlib import Path
import platform

print("=== Poppler-Konfigurations-Check ===\n")

# Prüfe .env
env_file = Path(".env")
if env_file.exists():
    print("[OK] .env Datei gefunden")
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
        if "POPPLER_PATH" in content:
            for line in content.split("\n"):
                if line.startswith("POPPLER_PATH"):
                    print(f"  {line}")
                    path_value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    poppler_path = Path(path_value)
                    print(f"\n  Konfigurierter Pfad: {poppler_path}")
                    print(f"  Absoluter Pfad: {poppler_path.resolve()}")
                    print(f"  Existiert: {poppler_path.exists()}")
                    
                    if poppler_path.exists():
                        # Prüfe ob es ein Verzeichnis ist
                        if poppler_path.is_dir():
                            print(f"  [OK] Ist ein Verzeichnis")
                            # Prüfe nach pdftoppm
                            if platform.system() == "Windows":
                                pdftoppm = poppler_path / "pdftoppm.exe"
                            else:
                                pdftoppm = poppler_path / "pdftoppm"
                            
                            print(f"  Prüfe nach: {pdftoppm.name}")
                            if pdftoppm.exists():
                                print(f"  [OK] {pdftoppm.name} gefunden!")
                            else:
                                print(f"  ✗ {pdftoppm.name} NICHT gefunden")
                                print(f"  Verfügbare Dateien im Verzeichnis:")
                                for item in poppler_path.iterdir():
                                    print(f"    - {item.name}")
                        else:
                            print(f"  [FEHLER] Ist kein Verzeichnis")
                    else:
                        print(f"  [FEHLER] Pfad existiert nicht!")
        else:
            print("  [FEHLER] POPPLER_PATH nicht in .env gefunden")
            print("  Füge hinzu: POPPLER_PATH=./poppler/bin")
else:
    print("[FEHLER] .env Datei nicht gefunden")
    print("  Erstelle .env und füge hinzu: POPPLER_PATH=./poppler/bin")

# Prüfe ob poppler/ Verzeichnis existiert
poppler_dirs = [
    Path("./poppler/bin"),
    Path("./poppler"),
    Path("poppler/bin"),
    Path("poppler"),
]

print("\n=== Suche nach Poppler-Verzeichnissen ===")
for poppler_dir in poppler_dirs:
    if poppler_dir.exists():
        print(f"[OK] Gefunden: {poppler_dir.resolve()}")
        if poppler_dir.is_dir():
            if platform.system() == "Windows":
                pdftoppm = poppler_dir / "pdftoppm.exe"
            else:
                pdftoppm = poppler_dir / "pdftoppm"
            
            if pdftoppm.exists():
                print(f"  [OK] {pdftoppm.name} gefunden!")
            else:
                print(f"  [FEHLER] {pdftoppm.name} nicht gefunden")
                print(f"  Dateien im Verzeichnis:")
                for item in poppler_dir.iterdir():
                    if item.is_file():
                        print(f"    - {item.name}")

print("\n=== Empfehlung ===")
print("1. Stelle sicher, dass Poppler im Projekt-Verzeichnis liegt:")
print("   RotaryArchiv/")
print("   +-- poppler/")
print("       +-- bin/")
print("           +-- pdftoppm.exe")
print("           +-- ...")
print("\n2. Füge in .env hinzu:")
print("   POPPLER_PATH=./poppler/bin")
print("\n3. Oder absoluter Pfad:")
print(f"   POPPLER_PATH={Path.cwd() / 'poppler' / 'bin'}")
