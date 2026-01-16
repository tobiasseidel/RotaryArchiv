"""
Tests für File Handler Utilities
"""

from pathlib import Path

import pytest

from src.rotary_archiv.utils.file_handler import (
    delete_file,
    ensure_documents_dir,
    get_file_path,
    get_file_size,
    save_uploaded_file,
)


@pytest.mark.unit
class TestFileHandler:
    """Tests für File Handler Funktionen"""

    def test_ensure_documents_dir(self, tmp_path, monkeypatch):
        """Test: Dokumente-Verzeichnis wird erstellt"""
        # Temporäres Verzeichnis verwenden
        monkeypatch.setattr(
            "src.rotary_archiv.utils.file_handler.settings.documents_path",
            str(tmp_path / "test_docs"),
        )

        docs_dir = ensure_documents_dir()
        assert docs_dir.exists()
        assert docs_dir.is_dir()

    def test_save_uploaded_file(self, tmp_path, monkeypatch):
        """Test: Datei wird korrekt gespeichert"""
        monkeypatch.setattr(
            "src.rotary_archiv.utils.file_handler.settings.documents_path",
            str(tmp_path / "test_docs"),
        )

        file_content = b"Test file content"
        filename = "test.txt"

        relative_path = save_uploaded_file(file_content, filename)

        # Prüfe dass Datei existiert
        file_path = get_file_path(relative_path)
        assert file_path.exists()
        assert file_path.read_bytes() == file_content
        assert relative_path.endswith(".txt")

    def test_get_file_path(self):
        """Test: Relativer Pfad wird zu absolutem Pfad konvertiert"""
        relative_path = "test/file.txt"
        absolute_path = get_file_path(relative_path)

        assert isinstance(absolute_path, Path)
        # Windows-kompatibel: Prüfe auf beide Pfad-Separatoren
        path_str = str(absolute_path).replace("\\", "/")
        assert path_str.endswith("test/file.txt")

    def test_delete_file(self, tmp_path, monkeypatch):
        """Test: Datei wird gelöscht"""
        monkeypatch.setattr(
            "src.rotary_archiv.utils.file_handler.settings.documents_path",
            str(tmp_path / "test_docs"),
        )

        # Erstelle Test-Datei
        test_file = tmp_path / "test_docs" / "test_delete.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")

        # Relativer Pfad (versuche relativ zu cwd, sonst absolut)
        try:
            relative_path = str(test_file.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(test_file)

        # Lösche Datei
        result = delete_file(relative_path)
        assert result is True
        assert not test_file.exists()

    def test_delete_nonexistent_file(self):
        """Test: Löschen nicht-existenter Datei gibt False zurück"""
        result = delete_file("nonexistent/file.txt")
        assert result is False

    def test_get_file_size(self, tmp_path, monkeypatch):
        """Test: Dateigröße wird korrekt ermittelt"""
        monkeypatch.setattr(
            "src.rotary_archiv.utils.file_handler.settings.documents_path",
            str(tmp_path / "test_docs"),
        )

        # Erstelle Test-Datei
        test_file = tmp_path / "test_docs" / "test_size.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_content = "test content"
        test_file.write_text(test_content)

        # Relativer Pfad (versuche relativ zu cwd, sonst absolut)
        try:
            relative_path = str(test_file.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(test_file)

        size = get_file_size(relative_path)

        assert size == len(test_content.encode("utf-8"))

    def test_get_file_size_nonexistent(self):
        """Test: Dateigröße für nicht-existente Datei ist 0"""
        size = get_file_size("nonexistent/file.txt")
        assert size == 0
