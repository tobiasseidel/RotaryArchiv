"""
Tesseract OCR Implementation
"""
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from typing import Optional, Dict, Any
from pathlib import Path

from src.rotary_archiv.config import settings


class TesseractOCR:
    """Tesseract OCR Wrapper"""
    
    def __init__(self):
        """Initialisiere Tesseract OCR"""
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    
    def extract_text(
        self,
        file_path: str,
        language: str = "deu+eng"
    ) -> Dict[str, Any]:
        """
        Extrahiere Text aus Datei mit Tesseract
        
        Args:
            file_path: Pfad zur Datei
            language: Sprache (z.B. "deu+eng" für Deutsch+Englisch)
            
        Returns:
            Dict mit 'text' und 'confidence'
        """
        file_path_obj = Path(file_path)
        
        try:
            if file_path_obj.suffix.lower() == ".pdf":
                # PDF zu Bilder konvertieren
                images = convert_from_path(str(file_path_obj))
                texts = []
                confidences = []
                
                for image in images:
                    text = pytesseract.image_to_string(image, lang=language)
                    data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
                    
                    # Berechne durchschnittliche Confidence
                    confs = [int(conf) for conf in data["conf"] if conf != "-1"]
                    avg_conf = sum(confs) / len(confs) if confs else 0
                    
                    texts.append(text)
                    confidences.append(avg_conf)
                
                full_text = "\n\n".join(texts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
            else:
                # Bild-Datei direkt verarbeiten
                image = Image.open(file_path_obj)
                full_text = pytesseract.image_to_string(image, lang=language)
                data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
                
                # Berechne durchschnittliche Confidence
                confs = [int(conf) for conf in data["conf"] if conf != "-1"]
                avg_confidence = sum(confs) / len(confs) if confs else 0
            
            return {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "engine": "tesseract",
                "language": language
            }
            
        except Exception as e:
            return {
                "text": "",
                "confidence": 0,
                "engine": "tesseract",
                "error": str(e)
            }
