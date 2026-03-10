"""
Konfiguration für RotaryArchiv
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rotary_archiv"
    postgres_user: str = "rotary_user"
    postgres_password: str = "change_me"

    # Triple Store (Fuseki)
    fuseki_host: str = "localhost"
    fuseki_port: int = 3030
    fuseki_dataset: str = "rotary_archiv"

    # File Storage
    documents_path: str = "./data/documents"

    # OCR
    tesseract_cmd: str = "tesseract"
    poppler_path: str | None = (
        None  # Pfad zu Poppler (z.B. "./poppler/bin" oder "C:/poppler/bin")
    )
    pdf_extraction_dpi: int = 200  # DPI für PDF-zu-Bild-Konvertierung (niedriger = schneller, weniger Speicher)
    pdf_extraction_batch_size: int = 50  # Anzahl Seiten pro Batch für große PDFs
    debug_save_bbox_crops: bool = True  # Speichere ausgeschnittene BBoxes für Debugging
    debug_bbox_crops_path: str = "./data/debug/bbox_crops"  # Pfad für Debug-BBox-Bilder
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("ollama_base_url", "ollama_api_base"),
    )
    ollama_vision_model: str = "deepseek-ocr:latest"  # Standard: deepseek-ocr:latest, kann über .env überschrieben werden
    ollama_gpt_model: str = (
        "gpt-oss:20b"  # Standard: gpt-oss:20b, kann über .env überschrieben werden
    )
    ollama_timeout_seconds: int = 3600  # Timeout für Ollama-Requests in Sekunden (Standard: 60 Minuten, für Background-Jobs)

    # Wikidata
    wikidata_api_url: str = "https://www.wikidata.org/w/api.php"
    wikidata_sparql_url: str = "https://query.wikidata.org/sparql"

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Quality Metrics - Dichte-Schwellenwerte (Zeichen/1000px)
    density_green_min: float = 3.5  # Ab diesem Wert: grün (optimal)
    density_green_max: float = 6.0  # Bis zu diesem Wert: grün (optimal)
    density_orange_min: float = 2.0  # Ab diesem Wert: orange (akzeptabel)
    density_orange_max: float = 10.0  # Bis zu diesem Wert: orange (akzeptabel)
    # < density_orange_min oder > density_orange_max: rot (problematisch)

    # OCR-Sichtung (LLM) - Fallback wenn keine DB-Settings
    auto_sight_black_pc_min: float = 18
    auto_sight_black_pc_max: float = 35
    auto_sight_threshold: float = 0.85

    # Mehrstufige Re-Erkennung persistente Regionen
    re_recognize_coverage_threshold: float = (
        0.85  # Abbruch wenn coverage_ratio >= Schwellwert
    )
    re_recognize_max_stages: int = 4  # Maximale Anzahl Stufen (0..3)
    re_recognize_dpi_stage1: int = 300  # DPI für Stufe 1 (höhere Auflösung)
    # Resize-Limits für Ollama Vision beim Re-Recognize (Stufe 3: größeres Bild ans Modell).
    # Warum Resize: Das Vision-Modell (z. B. DeepSeek-OCR) hat ein begrenztes Context-Window (z. B. 8K).
    # Große Bilder werden als Base64 gesendet; zu viele Pixel führen zu Fehlern oder Timeout.
    # Daher werden Bilder oberhalb bestimmter Dimensionen/Dateigröße verkleinert.
    # Trade-off: Kleineres Bild = weniger Detail, schlechtere Erkennung bei feiner Schrift.
    # Größeres Bild = bessere Erkennung, aber höheres Risiko für Context-Limit-Fehler und mehr Speicher/Latenz.
    # max_size = maximale Kantenlänge in Pixel (Breite und Höhe); max_size_mb = maximale Dateigröße in MB.
    # Überschreitung einer der Grenzen löst Verkleinerung (LANCZOS) aus.
    # Für Re-Recognize können höhere Limits gewählt werden (z. B. 1500 px, 4 MB), um mehr Detail zu senden.
    re_recognize_ollama_max_size: int = 1500  # max. Kantenlänge Pixel für Re-Recognize
    re_recognize_ollama_max_size_mb: float = 4.0  # max. Dateigröße MB für Re-Recognize
    # Korrekturfaktor X-Richtung: Ollama/Vision liefert oft zu schmale Boxen (z. B. 1/0.7 ≈ 1.43).
    re_recognize_bbox_x_stretch: float = 1.0 / 0.7

    @property
    def database_url(self) -> str:
        """Database Connection URL (PostgreSQL oder SQLite)"""
        # Fallback zu SQLite wenn PostgreSQL nicht verfügbar
        use_sqlite = self.postgres_host == "sqlite" or not self.postgres_host
        if use_sqlite:
            return "sqlite:///./rotary_archiv.db"
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def fuseki_url(self) -> str:
        """Fuseki SPARQL Endpoint URL"""
        return f"http://{self.fuseki_host}:{self.fuseki_port}/{self.fuseki_dataset}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
