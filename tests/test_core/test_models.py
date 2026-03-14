"""
Tests für Core Models
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.rotary_archiv.core.database import Base
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
)


@pytest.fixture
def db_session():
    """Erstelle Test-Datenbank-Session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.mark.unit
class TestDocumentModel:
    """Tests für Document Model"""

    def test_create_document(self, db_session):
        """Test: Dokument wird erstellt"""
        document = Document(
            filename="test.pdf",
            file_path="test/path/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(document)
        db_session.commit()

        assert document.id is not None
        assert document.filename == "test.pdf"
        assert document.status == DocumentStatus.UPLOADED

    def test_document_with_pages(self, db_session):
        """Test: Dokument mit Seiten"""
        document = Document(
            filename="test.pdf",
            file_path="test/path/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(document)
        db_session.flush()

        page1 = DocumentPage(
            document_id=document.id,
            page_number=1,
            file_path="test/path/page1.png",
            file_type="image/png",
        )
        page2 = DocumentPage(
            document_id=document.id,
            page_number=2,
            file_path="test/path/page2.png",
            file_type="image/png",
        )

        db_session.add_all([page1, page2])
        db_session.commit()

        assert len(document.pages) == 2
        assert document.pages[0].page_number == 1

    def test_composite_document(self, db_session):
        """Test: Composite-Dokument mit Child-Dokumenten"""
        parent = Document(
            filename="composite.pdf",
            file_path="test/path/composite.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=1,
        )
        db_session.add(parent)
        db_session.flush()

        child1 = Document(
            filename="page1.pdf",
            file_path="test/path/page1.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            parent_document_id=parent.id,
            page_number=1,
            is_composite=0,
        )
        child2 = Document(
            filename="page2.pdf",
            file_path="test/path/page2.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            parent_document_id=parent.id,
            page_number=2,
            is_composite=0,
        )

        db_session.add_all([child1, child2])
        db_session.commit()

        assert len(parent.child_documents) == 2
        assert parent.is_composite == 1
