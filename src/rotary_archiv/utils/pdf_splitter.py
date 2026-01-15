"""
PDF-Seiten-Extraktion und -Verwaltung
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
import uuid
from PyPDF2 import PdfReader, PdfWriter

# Optional imports
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.rotary_archiv.config import settings
from src.rotary_archiv.utils.file_handler import ensure_documents_dir


class PDFSplitter:
    """Extrahiert einzelne Seiten aus PDF-Dateien"""
    
    def __init__(self):
        """Initialisiere PDF Splitter"""
        self.pages_dir = ensure_documents_dir() / "pages"
        self.pages_dir.mkdir(exist_ok=True)
    
    def extract_pages(
        self,
        pdf_path: str,
        output_format: str = "pdf"  # "pdf" oder "image"
    ) -> List[Dict[str, Any]]:
        """
        Extrahiere alle Seiten aus einem PDF
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            output_format: "pdf" für einzelne PDFs, "image" für Bilder (PNG)
            
        Returns:
            Liste von Dicts mit page_number und file_path
        """
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
        
        pages_info = []
        
        try:
            if output_format == "pdf":
                # Extrahiere als einzelne PDFs
                try:
                    reader = PdfReader(str(pdf_path_obj), strict=False)  # strict=False für fehlertolerantes Lesen
                except Exception as e:
                    raise Exception(f"Fehler beim Lesen der PDF: {e}")
                
                # Prüfe ob PDF verschlüsselt ist
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")  # Versuche ohne Passwort
                    except Exception:
                        raise Exception("PDF ist verschlüsselt und benötigt ein Passwort")
                
                total_pages = len(reader.pages)
                
                if total_pages == 0:
                    raise Exception("PDF enthält keine Seiten")
                
                for page_num in range(total_pages):
                    try:
                        # Erstelle einzelnes PDF für diese Seite
                        writer = PdfWriter()
                        writer.add_page(reader.pages[page_num])
                        
                        # Generiere eindeutigen Dateinamen
                        page_filename = f"{uuid.uuid4()}_page_{page_num + 1}.pdf"
                        page_path = self.pages_dir / page_filename
                        
                        # Speichere Seite
                        with open(page_path, "wb") as output_file:
                            writer.write(output_file)
                    except Exception as e:
                        raise Exception(f"Fehler beim Extrahieren von Seite {page_num + 1}: {e}")
                    
                    # Relativer Pfad für Datenbank
                    try:
                        relative_path = str(page_path.relative_to(Path.cwd()))
                    except ValueError:
                        # Falls nicht relativ zu cwd, verwende absoluten Pfad
                        relative_path = str(page_path)
                    
                    pages_info.append({
                        "page_number": page_num + 1,
                        "file_path": relative_path,
                        "file_type": "pdf",
                        "total_pages": total_pages
                    })
            
            else:  # output_format == "image"
                if not PDF2IMAGE_AVAILABLE:
                    raise ImportError("pdf2image ist nicht installiert. Bitte installieren: pip install pdf2image")
                
                # Prüfe Dateigröße
                file_size_mb = pdf_path_obj.stat().st_size / (1024 * 1024)
                logging.info(f"PDF-Dateigröße: {file_size_mb:.2f} MB")
                
                # Bestimme DPI basierend auf Dateigröße
                dpi = settings.pdf_extraction_dpi
                if file_size_mb > 50:
                    dpi = 150  # Niedrigeres DPI für sehr große Dateien
                    logging.info(f"Große Datei erkannt ({file_size_mb:.2f} MB), verwende DPI {dpi}")
                elif file_size_mb > 20:
                    dpi = 200
                    logging.info(f"Mittlere Datei erkannt ({file_size_mb:.2f} MB), verwende DPI {dpi}")
                
                # Extrahiere als Bilder
                # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
                convert_kwargs = {"dpi": dpi}
                if settings.poppler_path:
                    poppler_path = Path(settings.poppler_path)
                    # Prüfe ob Verzeichnis existiert
                    if not poppler_path.exists():
                        raise FileNotFoundError(
                            f"Poppler-Pfad nicht gefunden: {poppler_path}\n"
                            f"Bitte prüfe die POPPLER_PATH Einstellung in .env\n"
                            f"Der Pfad sollte auf das 'bin' Verzeichnis von Poppler zeigen (z.B. './poppler/bin')"
                        )
                    # Prüfe ob pdftoppm.exe existiert (Windows) oder pdftoppm (Linux/Mac)
                    import platform
                    if platform.system() == "Windows":
                        pdftoppm = poppler_path / "pdftoppm.exe"
                    else:
                        pdftoppm = poppler_path / "pdftoppm"
                    
                    if not pdftoppm.exists():
                        raise FileNotFoundError(
                            f"Poppler-Tool nicht gefunden: {pdftoppm}\n"
                            f"Bitte stelle sicher, dass Poppler korrekt installiert ist.\n"
                            f"Der POPPLER_PATH sollte auf das 'bin' Verzeichnis zeigen."
                        )
                    
                    convert_kwargs["poppler_path"] = str(poppler_path)
                    logging.info(f"Verwende Poppler von: {poppler_path}")
                else:
                    logging.warning("POPPLER_PATH nicht konfiguriert. Versuche Poppler aus PATH zu verwenden.")
                
                # Für große PDFs: Batch-Verarbeitung
                batch_size = settings.pdf_extraction_batch_size
                
                # Zuerst: Anzahl der Seiten ermitteln
                try:
                    reader = PdfReader(str(pdf_path_obj), strict=False)
                    total_pages = len(reader.pages)
                    logging.info(f"PDF hat {total_pages} Seiten")
                except Exception as e:
                    logging.warning(f"Konnte Seitenzahl nicht ermitteln: {e}, verarbeite alle Seiten auf einmal")
                    total_pages = None
                
                # Wenn viele Seiten: Batch-Verarbeitung
                if total_pages and total_pages > batch_size:
                    logging.info(f"Große PDF ({total_pages} Seiten), verwende Batch-Verarbeitung (Batch-Größe: {batch_size})")
                    pages_info = []
                    
                    for batch_start in range(1, total_pages + 1, batch_size):
                        batch_end = min(batch_start + batch_size - 1, total_pages)
                        logging.info(f"Verarbeite Seiten {batch_start}-{batch_end} von {total_pages}")
                        
                        batch_kwargs = convert_kwargs.copy()
                        batch_kwargs["first_page"] = batch_start
                        batch_kwargs["last_page"] = batch_end
                        
                        try:
                            images = convert_from_path(str(pdf_path_obj), **batch_kwargs)
                            
                            for idx, image in enumerate(images):
                                page_num = batch_start + idx
                                # Generiere eindeutigen Dateinamen
                                page_filename = f"{uuid.uuid4()}_page_{page_num}.png"
                                page_path = self.pages_dir / page_filename
                                
                                # Speichere Bild
                                image.save(page_path, "PNG")
                                
                                # Relativer Pfad für Datenbank
                                try:
                                    relative_path = str(page_path.relative_to(Path.cwd()))
                                except ValueError:
                                    relative_path = str(page_path)
                                
                                pages_info.append({
                                    "page_number": page_num,
                                    "file_path": relative_path,
                                    "file_type": "png",
                                    "total_pages": total_pages
                                })
                                
                                # Speicher freigeben
                                del image
                            
                            # Speicher freigeben
                            del images
                            
                        except Exception as e:
                            logging.error(f"Fehler beim Verarbeiten von Seiten {batch_start}-{batch_end}: {e}")
                            raise
                else:
                    # Normale Verarbeitung für kleinere PDFs
                    logging.info("Verarbeite alle Seiten auf einmal")
                    images = convert_from_path(str(pdf_path_obj), **convert_kwargs)
                    
                    for page_num, image in enumerate(images, start=1):
                        # Generiere eindeutigen Dateinamen
                        page_filename = f"{uuid.uuid4()}_page_{page_num}.png"
                        page_path = self.pages_dir / page_filename
                        
                        # Speichere Bild
                        image.save(page_path, "PNG")
                        
                        # Relativer Pfad für Datenbank
                        try:
                            relative_path = str(page_path.relative_to(Path.cwd()))
                        except ValueError:
                            relative_path = str(page_path)
                        
                        pages_info.append({
                            "page_number": page_num,
                            "file_path": relative_path,
                            "file_type": "png",
                            "total_pages": len(images) if total_pages is None else total_pages
                        })
            
            return pages_info
            
        except Exception as e:
            raise Exception(f"Fehler beim Extrahieren der PDF-Seiten: {e}")
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Hole Anzahl der Seiten in einem PDF
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            
        Returns:
            Anzahl der Seiten
        """
        try:
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception as e:
            raise Exception(f"Fehler beim Lesen der PDF: {e}")
