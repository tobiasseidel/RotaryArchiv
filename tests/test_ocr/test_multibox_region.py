"""
Tests für Multibox-Region Transformation (process_multibox_region).

Die OCR-LLM-Antwort wird gemockt; die Transformation von Crop-Koordinaten
zurück auf die Original-Seite wird getestet.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.ocr.job_processor import process_multibox_region


# --- Fixtures (minimales Mock-Setup) ---


@pytest.fixture
def mock_db():
    """Minimales DB-Mock."""
    db = MagicMock()
    db.commit = MagicMock()
    return db


@pytest.fixture
def mock_page():
    """Mock DocumentPage."""
    page = MagicMock()
    page.bbox_data = []
    return page


@pytest.fixture
def mock_ocr_result():
    """Mock OCRResult mit Bild-Dimensionen (vollständige Seite)."""
    ocr_result = MagicMock()
    ocr_result.image_width = 1000
    ocr_result.image_height = 1500
    return ocr_result


# --- Helper-Funktionen ---


def make_bbox_item(region_bbox, crop_path="/tmp/test_crop.png"):
    """Erstelle bbox_item-Dict für Multibox-Region."""
    return {
        "bbox_pixel": region_bbox,
        "multibox_crop_path": crop_path,
    }


def make_ocr_response(bboxes_list, image_width, image_height):
    """
    Erstelle Mock OCR-Response.
    bboxes_list: Liste von dicts mit "bbox" (4 floats, normalisiert) und "text".
    """
    return {
        "bbox_list": bboxes_list,
        "image_width": image_width,
        "image_height": image_height,
    }


@pytest.mark.ocr
@pytest.mark.unit
class TestMultiboxRegionTransformation:
    """Tests für Multibox-Region Transformation."""

    @pytest.mark.asyncio
    async def test_simple_transformation(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 1: Einfache Transformation - eine Box innerhalb Region."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.1, 0.2, 0.8, 0.9], "text": "Test Text"}],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        # x1=100+28/0.7=140, x2=100+224/0.7=420, y1=200+40=240, y2=200+180=380
        assert result[0]["bbox_pixel"] == [140, 240, 420, 380]
        assert result[0]["text"] == "Test Text"

    @pytest.mark.asyncio
    async def test_coordinates_greater_than_one(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 2: Koordinaten > 1.0 werden auf Crop-Bild-Größe begrenzt."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.1, 0.2, 1.5, 2.0], "text": "Text"}],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        # x2_crop auf 280, y2_crop auf 200 begrenzt
        # x1_original = 100 + 28/0.7 ≈ 140, x2_original = 100 + 280/0.7 = 500
        # y1_original = 200 + 40 = 240, y2_original = 200 + 200 = 400
        assert result[0]["bbox_pixel"][0] == 140
        assert result[0]["bbox_pixel"][1] == 240
        assert result[0]["bbox_pixel"][2] == 500
        assert result[0]["bbox_pixel"][3] == 400

    @pytest.mark.asyncio
    async def test_box_clipped_to_region(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 3: Box über Region-Rand wird auf Region-Grenzen begrenzt."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.0, 0.0, 1.0, 1.0], "text": "Full"}],
            image_width=280,
            image_height=200,
        )
        mock_ocr_result.image_width = 600
        mock_ocr_result.image_height = 800
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        # Crop 280px breit -> x2_original = 100 + 280/0.7 = 500 (Region-Ende), Ergebnis [100, 200, 500, 400]
        assert result[0]["bbox_pixel"] == [100, 200, 500, 400]

    @pytest.mark.asyncio
    async def test_box_clipped_to_image_bounds(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 4: Box wird auf Bildgrenzen beschnitten wenn nötig."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.0, 0.0, 1.0, 1.0], "text": "Full"}],
            image_width=280,
            image_height=200,
        )
        mock_ocr_result.image_width = 400
        mock_ocr_result.image_height = 500
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        x1, y1, x2, y2 = result[0]["bbox_pixel"]
        assert x1 >= 0 and x2 <= 400 and y1 >= 0 and y2 <= 500

    @pytest.mark.asyncio
    async def test_multiple_boxes(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 5: Mehrere Boxen werden alle transformiert."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [
                {"bbox": [0.1, 0.1, 0.4, 0.3], "text": "First"},
                {"bbox": [0.1, 0.4, 0.4, 0.6], "text": "Second"},
                {"bbox": [0.1, 0.65, 0.4, 0.9], "text": "Third"},
            ],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 3
        assert result[0]["text"] == "First"
        assert result[1]["text"] == "Second"
        assert result[2]["text"] == "Third"

    @pytest.mark.asyncio
    async def test_small_region(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 6: Sehr kleine Region."""
        bbox_item = make_bbox_item([100, 200, 150, 250])
        ocr_response = make_ocr_response(
            [{"bbox": [0.1, 0.1, 0.9, 0.9], "text": "Small"}],
            image_width=35,
            image_height=50,
        )
        mock_img = MagicMock()
        mock_img.size = (35, 50)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        x1, y1, x2, y2 = result[0]["bbox_pixel"]
        assert 100 <= x1 < x2 <= 150 and 200 <= y1 < y2 <= 250

    @pytest.mark.asyncio
    async def test_box_at_region_edge(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 7: Box exakt an Region-Rand."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.0, 0.0, 1.0, 1.0], "text": "Edge"}],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        assert len(result) == 1
        # Volles Crop 280x200 -> x2_original = 100 + 280/0.7 = 500, y2 = 200+200 = 400
        assert result[0]["bbox_pixel"] == [100, 200, 500, 400]

    @pytest.mark.asyncio
    async def test_invalid_box_x1_gte_x2_skipped(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 8: Ungültige Box (x1 >= x2) wird übersprungen."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.5, 0.2, 0.3, 0.8], "text": "Invalid"}],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        # Fallback: Wenn alle Boxen ungültig sind, wird eine Box für die ganze Region geliefert
        assert len(result) == 1
        assert result[0]["bbox_pixel"] == [100, 200, 500, 400]
        assert "[Bitte manuell prüfen" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_empty_text_skipped(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 9: Box mit leerem Text wird übersprungen."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        ocr_response = make_ocr_response(
            [{"bbox": [0.1, 0.2, 0.8, 0.9], "text": "   "}],
            image_width=280,
            image_height=200,
        )
        mock_img = MagicMock()
        mock_img.size = (280, 200)
        with patch(
            "src.rotary_archiv.ocr.job_processor.OllamaVisionOCR"
        ) as mock_ollama_class:
            mock_ollama_class.return_value.extract_text_with_bbox.return_value = (
                ocr_response
            )
            with patch("PIL.Image.open", return_value=mock_img):
                with patch.object(Path, "exists", return_value=True):
                    result = await process_multibox_region(
                        db=mock_db,
                        document_page_id=1,
                        bbox_item=bbox_item,
                        ocr_result=mock_ocr_result,
                        page=mock_page,
                    )
        # Fallback: Wenn alle Boxen leeren Text haben, wird eine Box für die ganze Region geliefert
        assert len(result) == 1
        assert result[0]["bbox_pixel"] == [100, 200, 500, 400]
        assert "[Bitte manuell prüfen" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_crop_path_missing_returns_empty(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Test 10: Fehlender multibox_crop_path liefert leere Liste."""
        bbox_item = {"bbox_pixel": [100, 200, 500, 400]}
        result = await process_multibox_region(
            db=mock_db,
            document_page_id=1,
            bbox_item=bbox_item,
            ocr_result=mock_ocr_result,
            page=mock_page,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_crop_file_not_exists_returns_empty(
        self, mock_db, mock_page, mock_ocr_result
    ):
        """Crop-Pfad existiert nicht -> leere Liste."""
        bbox_item = make_bbox_item([100, 200, 500, 400])
        with patch.object(Path, "exists", return_value=False):
            result = await process_multibox_region(
                db=mock_db,
                document_page_id=1,
                bbox_item=bbox_item,
                ocr_result=mock_ocr_result,
                page=mock_page,
            )
        assert result == []
