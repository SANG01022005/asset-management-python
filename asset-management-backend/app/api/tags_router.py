"""
app/api/tags_router.py
Bài 6.2 — Asset Tags CRUD.
"""
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.domain.models import Asset, Tag
from app.infrastructure.database import get_db

router = APIRouter(tags=["Tags"])


class TagCreate(BaseModel):
    name:  str = Field(..., min_length=1, max_length=64)
    color: str = Field("#6b7280", pattern=r"^#[0-9a-fA-F]{6}$")


class AssignTagsRequest(BaseModel):
    tag_ids: List[uuid.UUID] = Field(..., min_length=1)


def _tag_to_resp(tag: Tag) -> Dict[str, Any]:
    return {"id": tag.id, "name": tag.name, "color": tag.color, "asset_count": len(tag.assets)}


def _get_asset_or_404(asset_id: uuid.UUID, db: Session) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")
    return asset


def _get_tag_or_404(tag_id: uuid.UUID, db: Session) -> Tag:
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail=f"Tag '{tag_id}' not found.")
    return tag


@router.get("/tags", summary="List all tags")
def list_tags(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return [_tag_to_resp(t) for t in db.query(Tag).order_by(Tag.name).all()]


@router.post("/tags", status_code=201, summary="Create tag")
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if db.query(Tag).filter(Tag.name == payload.name).first():
        raise HTTPException(409, detail=f"Tag '{payload.name}' already exists.")
    tag = Tag(id=uuid.uuid4(), name=payload.name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_to_resp(tag)


@router.delete("/tags/{tag_id}", status_code=204, summary="Delete tag")
def delete_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    tag = _get_tag_or_404(tag_id, db)
    db.delete(tag)
    db.commit()


@router.get("/assets/{asset_id}/tags", summary="List asset tags")
def list_asset_tags(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    asset = _get_asset_or_404(asset_id, db)
    return [_tag_to_resp(t) for t in asset.tags]


@router.post("/assets/{asset_id}/tags", summary="Assign tags to asset")
def assign_tags(asset_id: uuid.UUID, payload: AssignTagsRequest, db: Session = Depends(get_db)):
    asset = _get_asset_or_404(asset_id, db)
    added, not_found = [], []
    for tag_id in payload.tag_ids:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            not_found.append(str(tag_id))
        elif tag not in asset.tags:
            asset.tags.append(tag)
            added.append(tag.name)
    db.commit()
    return {"asset_id": str(asset_id), "added": added, "not_found": not_found,
            "current_tags": [_tag_to_resp(t) for t in asset.tags]}


@router.delete("/assets/{asset_id}/tags/{tag_id}", status_code=204, summary="Remove tag from asset")
def remove_tag_from_asset(asset_id: uuid.UUID, tag_id: uuid.UUID, db: Session = Depends(get_db)):
    asset = _get_asset_or_404(asset_id, db)
    tag   = _get_tag_or_404(tag_id, db)
    if tag in asset.tags:
        asset.tags.remove(tag)
        db.commit()