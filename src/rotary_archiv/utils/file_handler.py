"""
File Handling Utilities
"""

from pathlib import Path
import uuid

from src.rotary_archiv.config import settings


def ensure_documents_dir() -> Path:
    """
    Stelle sicher, dass das Dokumente-Verzeichnis existiert

    Returns:
        Path zum Dokumente-Verzeichnis
    """
    docs_path = Path(settings.documents_path)
    docs_path.mkdir(parents=True, exist_ok=True)
    return docs_path


def ensure_exports_dir() -> Path:
    """
    Stelle sicher, dass das Export-Verzeichnis (documents_path/exports) existiert.
    Für PDF-Export-Jobs (Worker).

    Returns:
        Path zum Export-Verzeichnis
    """
    exports_path = Path(settings.documents_path) / "exports"
    exports_path.mkdir(parents=True, exist_ok=True)
    return exports_path


def save_uploaded_file(file_content: bytes, filename: str) -> str:
    """
    Speichere hochgeladene Datei

    Args:
        file_content: Datei-Inhalt als Bytes
        filename: Original-Dateiname

    Returns:
        Relativer Pfad zur gespeicherten Datei
    """
    docs_dir = ensure_documents_dir()

    # Generiere eindeutigen Dateinamen
    file_ext = Path(filename).suffix if filename else ".bin"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = docs_dir / unique_filename

    # Speichere Datei
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise Exception(f"Fehler beim Speichern der Datei: {e}") from e

    # Relativer Pfad für Datenbank - verwende absoluten Pfad relativ zum Projekt-Root
    try:
        # Versuche relativ zu cwd
        relative_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        # Falls nicht möglich, verwende absoluten Pfad
        relative_path = str(file_path)

    return relative_path


def get_file_path(relative_path: str) -> Path:
    """
    Hole absoluten Pfad zur Datei

    Args:
        relative_path: Relativer oder absoluter Pfad (aus Datenbank)

    Returns:
        Absoluter Path
    """
    path = Path(relative_path)
    # Wenn bereits absolut, verwende direkt
    if path.is_absolute():
        return path
    # Sonst relativ zu cwd
    return Path.cwd() / relative_path


def delete_file(relative_path: str) -> bool:
    """
    Lösche Datei

    Args:
        relative_path: Relativer Pfad zur Datei

    Returns:
        True wenn erfolgreich
    """
    try:
        file_path = get_file_path(relative_path)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception:
        return False


def get_file_size(relative_path: str) -> int:
    """
    Hole Dateigröße in Bytes

    Args:
        relative_path: Relativer Pfad zur Datei

    Returns:
        Dateigröße in Bytes
    """
    file_path = get_file_path(relative_path)
    if file_path.exists():
        return file_path.stat().st_size
    return 0
