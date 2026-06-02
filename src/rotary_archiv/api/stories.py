"""
Admin CRUD API für Stories
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    NoteRef,
    StoryCreate,
    StoryDetail,
    StoryResponse,
    StoryUpdate,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import BBox, DocumentPage, OCRResult, Story

router = APIRouter(prefix="/api/stories", tags=["stories"])


def _story_to_detail(story: Story, db: Session) -> StoryDetail:
    """Hilfsfunktion: Story + Notes → StoryDetail"""
    notes: list[NoteRef] = []
    for bbox in story.notes or []:
        page_id = None
        doc_id = None
        if bbox.ocr_result_id:
            ocr_result = (
                db.query(OCRResult).filter(OCRResult.id == bbox.ocr_result_id).first()
            )
            if ocr_result and ocr_result.document_page_id:
                page = (
                    db.query(DocumentPage)
                    .filter(DocumentPage.id == ocr_result.document_page_id)
                    .first()
                )
                if page:
                    page_id = page.id
                    doc_id = page.document_id
        notes.append(
            NoteRef(
                id=bbox.id,
                note_text=bbox.note_text,
                note_author=bbox.note_author,
                page_id=page_id,
                document_id=doc_id,
            )
        )
    return StoryDetail(
        id=story.id,
        slug=story.slug,
        title=story.title,
        teaser=story.teaser,
        body=story.body,
        epoch=story.epoch,
        image_url=story.image_url,
        is_published=story.is_published,
        is_featured=story.is_featured,
        created_by=story.created_by,
        created_at=story.created_at,
        updated_at=story.updated_at,
        notes=notes,
    )


def _update_note_assignment(
    story_id: int | None, note_ids: list[int], db: Session
) -> None:
    """Setzt story_id auf den angegebenen Notes. Entfernt Zuweisung von allen nicht mehr enthaltenen."""
    if not note_ids:
        return
    # Alte Zuweisungen für diese Story lösen
    if story_id is not None:
        db.query(BBox).filter(
            BBox.story_id == story_id,
            BBox.box_type == "note",
            ~BBox.id.in_(note_ids),
        ).update({"story_id": None}, synchronize_session="fetch")
    # Neue Zuweisungen setzen
    db.query(BBox).filter(
        BBox.id.in_(note_ids),
        BBox.box_type == "note",
    ).update({"story_id": story_id}, synchronize_session="fetch")


@router.get("", response_model=list[StoryResponse])
def list_stories(
    published: bool | None = Query(None, description="Filter: nur publizierte"),
    featured: bool | None = Query(None, description="Filter: nur gefeaturete"),
    db: Session = Depends(get_db),
):
    """Alle Stories, optional gefiltert."""
    q = db.query(Story)
    if published is not None:
        q = q.filter(Story.is_published == published)
    if featured is not None:
        q = q.filter(Story.is_featured == featured)
    return q.order_by(Story.updated_at.desc()).all()


@router.get("/{story_id}", response_model=StoryDetail)
def get_story(story_id: int, db: Session = Depends(get_db)):
    """Story-Detail inkl. verknüpfter Notes."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story nicht gefunden"
        )
    return _story_to_detail(story, db)


@router.post("", response_model=StoryDetail, status_code=status.HTTP_201_CREATED)
def create_story(body: StoryCreate, db: Session = Depends(get_db)):
    """Neue Story anlegen und optional Notes zuweisen."""
    existing = db.query(Story).filter(Story.slug == body.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Story mit slug '{body.slug}' existiert bereits",
        )
    story = Story(
        slug=body.slug,
        title=body.title,
        teaser=body.teaser,
        body=body.body,
        epoch=body.epoch,
        image_url=body.image_url,
        is_published=body.is_published,
        is_featured=body.is_featured,
        created_by=body.created_by,
    )
    db.add(story)
    db.flush()  # story.id generieren
    if body.note_ids:
        _update_note_assignment(story.id, body.note_ids, db)
    db.commit()
    db.refresh(story)
    return _story_to_detail(story, db)


@router.patch("/{story_id}", response_model=StoryDetail)
def update_story(story_id: int, body: StoryUpdate, db: Session = Depends(get_db)):
    """Story aktualisieren (Body, Notes, Featured, Published)."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story nicht gefunden"
        )

    update_data = body.model_dump(exclude_unset=True, exclude={"note_ids"})
    for field, value in update_data.items():
        setattr(story, field, value)
    db.flush()
    if body.note_ids is not None:
        _update_note_assignment(story.id, body.note_ids, db)
    db.commit()
    db.refresh(story)
    return _story_to_detail(story, db)


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(story_id: int, db: Session = Depends(get_db)):
    """Story löschen. Notes werden wieder unassigned (SET NULL durch FK)."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story nicht gefunden"
        )
    db.delete(story)
    db.commit()
