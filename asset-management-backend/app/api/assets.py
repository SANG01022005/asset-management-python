"""
app/api/assets.py
CRUD endpoints for assets with pagination, search, stats.
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models import Asset, ScanJob
from app.domain.schemas import (
    AssetCreate, AssetResponse, AssetStatus, AssetType,
    BatchCreateRequest, BatchCreateResponse,
)
from app.infrastructure.database import get_db

router = APIRouter(tags=["Assets"])


# ── POST /assets/batch ────────────────────────────────────────────────────────

@router.post("/assets/batch", status_code=status.HTTP_201_CREATED,
             response_model=BatchCreateResponse, summary="Batch create assets")
def batch_create(payload: BatchCreateRequest, db: Session = Depends(get_db)):
    created = []
    for a in payload.assets:
        asset = Asset(id=uuid.uuid4(), name=a.name, type=a.type.value, status=a.status.value)
        db.add(asset)
        created.append(asset)
    db.commit()
    return BatchCreateResponse(created_count=len(created), ids=[a.id for a in created])


# ── DELETE /assets/batch ──────────────────────────────────────────────────────

@router.delete("/assets/batch", summary="Batch delete assets")
def batch_delete(
    ids: str = Query(..., description="Comma-separated UUIDs"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    id_list = [i.strip() for i in ids.split(",")]
    parsed = []
    for i in id_list:
        try:
            parsed.append(uuid.UUID(i))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"message": f"'{i}' is not valid UUID.", "invalid_id": i},
            )

    deleted_ids, not_found_ids = [], []
    for uid in parsed:
        asset = db.query(Asset).filter(Asset.id == uid).first()
        if asset:
            db.delete(asset)
            deleted_ids.append(str(uid))
        else:
            not_found_ids.append(str(uid))
    db.commit()
    return {
        "deleted":      len(deleted_ids),
        "not_found":    len(not_found_ids),
        "deleted_ids":  deleted_ids,
        "not_found_ids": not_found_ids,
    }


# ── GET /assets/search ────────────────────────────────────────────────────────

@router.get("/assets/search", response_model=List[AssetResponse], summary="Search assets")
def search_assets(
    q:  str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db),
):
    return (
        db.query(Asset)
        .filter(Asset.name.ilike(f"%{q}%"))
        .order_by(Asset.created_at.desc())
        .all()
    )


# ── GET /assets/stats ─────────────────────────────────────────────────────────

@router.get("/assets/stats", summary="Asset statistics")
def asset_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    assets = db.query(Asset).all()
    by_type   = {"domain": 0, "ip": 0, "service": 0}
    by_status = {"active": 0, "inactive": 0}
    for a in assets:
        by_type[a.type]     = by_type.get(a.type, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1
    return {"total": len(assets), "by_type": by_type, "by_status": by_status}


# ── GET /assets/count ─────────────────────────────────────────────────────────

@router.get("/assets/count", summary="Count assets")
def count_assets(
    type:   Optional[AssetType]   = Query(None),
    status: Optional[AssetStatus] = Query(None),
    db:     Session                = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(Asset)
    if type:
        q = q.filter(Asset.type == type.value)
    if status:
        q = q.filter(Asset.status == status.value)
    return {
        "count":   q.count(),
        "filters": {"type": type.value if type else None,
                    "status": status.value if status else None},
    }


# ── GET /assets ───────────────────────────────────────────────────────────────

@router.get("/assets", summary="List assets (paginated)")
def list_assets(
    type:   Optional[AssetType]   = Query(None),
    status: Optional[AssetStatus] = Query(None),
    page:   int = Query(1, ge=1),
    limit:  int = Query(20, ge=1, le=200),
    db:     Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(Asset)
    if type:
        q = q.filter(Asset.type == type.value)
    if status:
        q = q.filter(Asset.status == status.value)

    total       = q.count()
    total_pages = max(1, (total + limit - 1) // limit)
    assets      = q.order_by(Asset.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [AssetResponse.model_validate(a).model_dump() for a in assets],
        "pagination": {
            "page":        page,
            "limit":       limit,
            "total":       total,
            "total_pages": total_pages,
        },
    }