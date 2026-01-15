"""
API Endpoints für Entitäten
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Entity, EntityType
from src.rotary_archiv.api.schemas import (
    EntityCreate, EntityUpdate, EntityResponse
)
from src.rotary_archiv.wikidata.matcher import WikidataMatcher

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.post("/", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(
    entity: EntityCreate,
    db: Session = Depends(get_db)
):
    """
    Erstelle neue Entität
    """
    # Prüfe ob Entität bereits existiert
    existing = db.query(Entity).filter(
        Entity.name == entity.name,
        Entity.entity_type == entity.entity_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entität existiert bereits"
        )
    
    # Hole Wikidata-Daten falls ID angegeben
    wikidata_data = None
    if entity.wikidata_id:
        matcher = WikidataMatcher()
        wikidata_data = matcher.get_entity_details(entity.wikidata_id)
    
    # Erstelle Entität
    db_entity = Entity(
        name=entity.name,
        entity_type=entity.entity_type,
        description=entity.description,
        wikidata_id=entity.wikidata_id,
        wikidata_label=wikidata_data.get("label") if wikidata_data else None,
        wikidata_description=wikidata_data.get("description") if wikidata_data else None,
        wikidata_data=wikidata_data if wikidata_data else None
    )
    
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    
    return db_entity


@router.get("/", response_model=List[EntityResponse])
def list_entities(
    skip: int = 0,
    limit: int = 100,
    entity_type: Optional[EntityType] = None,
    db: Session = Depends(get_db)
):
    """
    Liste alle Entitäten
    """
    query = db.query(Entity)
    
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    
    entities = query.offset(skip).limit(limit).all()
    return entities


@router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: int,
    db: Session = Depends(get_db)
):
    """
    Hole einzelne Entität
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entität nicht gefunden"
        )
    return entity


@router.put("/{entity_id}", response_model=EntityResponse)
def update_entity(
    entity_id: int,
    entity_update: EntityUpdate,
    db: Session = Depends(get_db)
):
    """
    Aktualisiere Entität
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entität nicht gefunden"
        )
    
    # Update Felder
    update_data = entity_update.model_dump(exclude_unset=True)
    
    # Wenn Wikidata-ID geändert, hole neue Daten
    if "wikidata_id" in update_data and update_data["wikidata_id"]:
        matcher = WikidataMatcher()
        wikidata_data = matcher.get_entity_details(update_data["wikidata_id"])
        if wikidata_data:
            update_data["wikidata_label"] = wikidata_data.get("label")
            update_data["wikidata_description"] = wikidata_data.get("description")
            update_data["wikidata_data"] = wikidata_data
    
    for field, value in update_data.items():
        setattr(entity, field, value)
    
    db.commit()
    db.refresh(entity)
    
    return entity


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db)
):
    """
    Lösche Entität
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entität nicht gefunden"
        )
    
    db.delete(entity)
    db.commit()
    
    return None
