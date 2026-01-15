"""
Dokumenten-Klassifizierung
"""
from typing import Dict, Any, Optional, List
from src.rotary_archiv.core.models import DocumentType
from src.rotary_archiv.ocr.ollama_gpt import OllamaGPT


class DocumentClassifier:
    """Klassifiziert Dokumente nach Typ"""
    
    def __init__(self):
        """Initialisiere Document Classifier"""
        self.ollama_gpt = OllamaGPT()
    
    def classify_document(
        self,
        text: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Klassifiziere Dokument nach Typ
        
        Args:
            text: OCR-Text des Dokuments
            filename: Optional: Dateiname (kann Hinweise geben)
            
        Returns:
            Dict mit vorgeschlagenem DocumentType und Confidence
        """
        # Einfache Heuristik basierend auf Text-Inhalten
        text_lower = text.lower()
        filename_lower = filename.lower() if filename else ""
        
        # Keywords für verschiedene Dokument-Typen
        keywords = {
            DocumentType.MEETING_PROTOCOL: [
                "protokoll", "sitzung", "meeting", "versammlung",
                "tagesordnung", "anwesend", "abwesend", "beschluss"
            ],
            DocumentType.INVITATION: [
                "einladung", "invitation", "ladung", "einladen",
                "wir laden", "herzlich ein"
            ],
            DocumentType.MEMBER_LIST: [
                "mitglieder", "mitgliederliste", "member list",
                "vorstand", "präsident", "sekretär"
            ],
            DocumentType.FINANCIAL_REPORT: [
                "finanzbericht", "kassenbericht", "rechnung",
                "einnahmen", "ausgaben", "bilanz"
            ],
        }
        
        scores = {}
        for doc_type, kw_list in keywords.items():
            score = sum(1 for kw in kw_list if kw in text_lower or kw in filename_lower)
            scores[doc_type] = score
        
        # Bestimme Typ mit höchstem Score
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                suggested_type = max(scores, key=scores.get)
                return {
                    "document_type": suggested_type,
                    "confidence": min(max_score / 5.0, 1.0),  # Normalisiere zu 0-1
                    "scores": scores
                }
        
        # Fallback: GPT-basierte Klassifizierung
        return self._classify_with_gpt(text, filename)
    
    def _classify_with_gpt(
        self,
        text: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Klassifiziere mit GPT
        
        Args:
            text: OCR-Text
            filename: Optional: Dateiname
            
        Returns:
            Dict mit vorgeschlagenem DocumentType
        """
        prompt = f"""Klassifiziere das folgende Dokument in einen dieser Typen:
- meeting_protocol (Meeting-Protokoll)
- invitation (Einladung)
- photo (Foto)
- member_list (Mitgliederliste)
- financial_report (Finanzbericht)
- other (Sonstiges)

Antworte nur mit dem Typ-Namen, nichts anderes.

{f"Dateiname: {filename}" if filename else ""}

Text (erste 1000 Zeichen):
{text[:1000]}"""
        
        try:
            result = self.ollama_gpt._generate(prompt)
            result_lower = result.strip().lower()
            
            # Parse Ergebnis
            type_mapping = {
                "meeting_protocol": DocumentType.MEETING_PROTOCOL,
                "invitation": DocumentType.INVITATION,
                "photo": DocumentType.PHOTO,
                "member_list": DocumentType.MEMBER_LIST,
                "financial_report": DocumentType.FINANCIAL_REPORT,
                "other": DocumentType.OTHER,
            }
            
            for key, doc_type in type_mapping.items():
                if key in result_lower:
                    return {
                        "document_type": doc_type,
                        "confidence": 0.7,  # GPT-basierte Klassifizierung
                        "method": "gpt"
                    }
            
            return {
                "document_type": DocumentType.OTHER,
                "confidence": 0.5,
                "method": "gpt"
            }
        except Exception as e:
            return {
                "document_type": DocumentType.OTHER,
                "confidence": 0.0,
                "error": str(e)
            }
