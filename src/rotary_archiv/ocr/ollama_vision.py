"""
Ollama Vision OCR Implementation
"""
import httpx
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import io

from src.rotary_archiv.config import settings


class OllamaVisionOCR:
    """Ollama Vision OCR Wrapper"""
    
    def __init__(self):
        """Initialisiere Ollama Vision OCR"""
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_vision_model
    
    def _image_to_base64(self, image_path: Path) -> Optional[str]:
        """
        Konvertiere Bild zu Base64
        
        Args:
            image_path: Pfad zum Bild
            
        Returns:
            Base64-String oder None
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode("utf-8")
        except Exception:
            return None
    
    def _pdf_to_images(self, pdf_path: Path) -> list[Image.Image]:
        """
        Konvertiere PDF zu Bilder
        
        Args:
            pdf_path: Pfad zur PDF
            
        Returns:
            Liste von PIL Images
        """
        try:
            from pdf2image import convert_from_path
            return convert_from_path(str(pdf_path))
        except Exception:
            return []
    
    def extract_text(
        self,
        file_path: str,
        prompt: str = "Extract all text from this image. Return only the text, no explanations."
    ) -> Dict[str, Any]:
        """
        Extrahiere Text aus Datei mit Ollama Vision
        
        Args:
            file_path: Pfad zur Datei
            prompt: Prompt für Vision Model
            
        Returns:
            Dict mit 'text' und Metadaten
        """
        file_path_obj = Path(file_path)
        
        try:
            if file_path_obj.suffix.lower() == ".pdf":
                # PDF zu Bilder konvertieren
                images = self._pdf_to_images(file_path_obj)
                texts = []
                
                for image in images:
                    # Konvertiere PIL Image zu Base64
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    text = self._process_image(image_b64, prompt)
                    texts.append(text)
                
                full_text = "\n\n".join(texts)
                
            else:
                # Bild-Datei direkt verarbeiten
                image_b64 = self._image_to_base64(file_path_obj)
                if not image_b64:
                    raise Exception("Konnte Bild nicht laden")
                
                full_text = self._process_image(image_b64, prompt)
            
            return {
                "text": full_text.strip(),
                "confidence": None,  # Ollama Vision gibt keine Confidence
                "engine": "ollama_vision",
                "model": self.model
            }
            
        except Exception as e:
            return {
                "text": "",
                "confidence": None,
                "engine": "ollama_vision",
                "error": str(e)
            }
    
    def _process_image(self, image_b64: str, prompt: str) -> str:
        """
        Verarbeite einzelnes Bild mit Ollama Vision
        
        Args:
            image_b64: Base64-kodiertes Bild
            prompt: Prompt für Vision Model
            
        Returns:
            Extrahierter Text
        """
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            raise Exception(f"Ollama Vision Fehler: {e}")
