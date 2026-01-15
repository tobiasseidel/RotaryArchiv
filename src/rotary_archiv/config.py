"""
Konfiguration für RotaryArchiv
"""
from pydantic_settings import BaseSettings
from typing import Optional


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
    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llava"
    ollama_gpt_model: str = "llama3"
    
    # Wikidata
    wikidata_api_url: str = "https://www.wikidata.org/w/api.php"
    wikidata_sparql_url: str = "https://query.wikidata.org/sparql"
    
    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    @property
    def database_url(self) -> str:
        """PostgreSQL Connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def fuseki_url(self) -> str:
        """Fuseki SPARQL Endpoint URL"""
        return f"http://{self.fuseki_host}:{self.fuseki_port}/{self.fuseki_dataset}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
