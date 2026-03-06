import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.models import Asset
from app.domain.schemas import (
    AssetResponse,
    AssetStatus,
    AssetType,
    BatchCreateRequest,
    BatchCreateResponse,
)
from app.infrastructure.database import get_db

router = APIRouter(prefix="/assets", tags=["Assets"])


# ── GET /assets/search  ──────────────────────────────────────────────────────
# ⚠️  Must be declared BEFORE /assets (index) and any dynamic /{id} routes
#     so FastAPI does not accidentally treat "search" as a path parameter.

_SEARCH_LIMIT = 100

@router.get(
    "/search",
    response_model=List[AssetResponse],
    summary="Search assets by name",
    description=(
        "Case-insensitive partial-match search on the `name` field. "
        f"Returns at most {_SEARCH_LIMIT} results."
    ),
    responses={
        200: {"description": "List of matching assets (may be empty)"},
        400: {"description": "`q` is missing or empty"},
        500: {"description": "Unexpected server error"},
    },
)
def search_assets(
    q:  str     = Query(..., min_length=1, description="Search term (partial, case-insensitive)"),
    db: Session = Depends(get_db),
) -> List[Asset]:
    try:
        results: List[Asset] = (
            db.query(Asset)
            .filter(Asset.name.ilike(f"%{q}%"))
            .order_by(Asset.created_at.desc())
            .limit(_SEARCH_LIMIT)
            .all()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc

    return results


# ── GET /assets  (paginated list + filters) ───────────────────────────────────

_PAGE_MAX_LIMIT = 100

@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List assets with pagination and optional filters",
    description=(
        "Returns a paginated list of assets. "
        "Filter by `type` and/or `status`. Results are sorted by `created_at` descending."
    ),
    responses={
        200: {"description": "Paginated asset list"},
        422: {"description": "Invalid query parameter value"},
        500: {"description": "Unexpected server error"},
    },
)
def list_assets(
    page:   int                    = Query(1,    ge=1,                 description="Page number (1-based)"),
    limit:  int                    = Query(20,   ge=1, le=_PAGE_MAX_LIMIT, description=f"Items per page (max {_PAGE_MAX_LIMIT})"),
    type:   Optional[AssetType]   = Query(None,                        description="Filter by asset type"),
    status: Optional[AssetStatus] = Query(None,                        description="Filter by asset status"),
    db:     Session                = Depends(get_db),
) -> Dict[str, Any]:
    try:
        # ── Base query (shared between COUNT and SELECT) ──────────────────────
        base_q = db.query(Asset)
        if type is not None:
            base_q = base_q.filter(Asset.type == type.value)
        if status is not None:
            base_q = base_q.filter(Asset.status == status.value)

        # ── Total count (runs a single COUNT query, no data fetched) ──────────
        total: int = base_q.with_entities(func.count(Asset.id)).scalar() or 0

        # ── Paginated data ────────────────────────────────────────────────────
        offset      = (page - 1) * limit
        total_pages = math.ceil(total / limit) if total > 0 else 1

        assets: List[Asset] = (
            base_q
            .order_by(Asset.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assets: {exc}",
        ) from exc

    return {
        "data": [AssetResponse.model_validate(a) for a in assets],
        "pagination": {
            "page":        page,
            "limit":       limit,
            "total":       total,
            "total_pages": total_pages,
        },
    }


# ── GET /assets/stats ────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Asset statistics",
    description="Returns total count plus breakdowns by type and status.",
)
def get_asset_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        # ── Total ────────────────────────────────────────────────────────────
        total: int = db.query(func.count(Asset.id)).scalar() or 0

        # ── By type ──────────────────────────────────────────────────────────
        type_rows = (
            db.query(Asset.type, func.count(Asset.id))
            .group_by(Asset.type)
            .all()
        )
        by_type: Dict[str, int] = {t.value: 0 for t in AssetType}
        for asset_type, count in type_rows:
            if asset_type in by_type:
                by_type[asset_type] = count

        # ── By status ────────────────────────────────────────────────────────
        status_rows = (
            db.query(Asset.status, func.count(Asset.id))
            .group_by(Asset.status)
            .all()
        )
        by_status: Dict[str, int] = {s.value: 0 for s in AssetStatus}
        for asset_status, count in status_rows:
            if asset_status in by_status:
                by_status[asset_status] = count

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve asset statistics: {exc}",
        ) from exc

    return {
        "total":     total,
        "by_type":   by_type,
        "by_status": by_status,
    }


# ── GET /assets/count ────────────────────────────────────────────────────────

@router.get(
    "/count",
    summary="Count assets with optional filters",
    description=(
        "Returns the number of assets matching the optional `type` "
        "and/or `status` query parameters. Omit either param to skip that filter."
    ),
)
def get_asset_count(
    type:   Optional[AssetType]   = Query(None, description="Filter by asset type: domain | ip | service"),
    status: Optional[AssetStatus] = Query(None, description="Filter by asset status: active | inactive"),
    db:     Session               = Depends(get_db),
) -> Dict[str, Any]:
    try:
        query = db.query(func.count(Asset.id))

        if type is not None:
            query = query.filter(Asset.type == type.value)
        if status is not None:
            query = query.filter(Asset.status == status.value)

        count: int = query.scalar() or 0

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count assets: {exc}",
        ) from exc

    return {
        "count":   count,
        "filters": {
            "type":   type.value   if type   else None,
            "status": status.value if status else None,
        },
    }


# ── POST /assets/batch ───────────────────────────────────────────────────────

_BATCH_LIMIT = 100


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=BatchCreateResponse,
    summary="Batch create assets",
    description=(
        f"Create up to {_BATCH_LIMIT} assets in a single atomic transaction. "
        "If **any** asset fails, the entire batch is rolled back."
    ),
    responses={
        201: {"description": "All assets created successfully"},
        400: {"description": "Validation error or duplicate entry"},
        422: {"description": "Request body failed schema validation"},
        500: {"description": "Unexpected server error — batch rolled back"},
    },
)
def batch_create_assets(
    payload: BatchCreateRequest,
    db: Session = Depends(get_db),
) -> BatchCreateResponse:

    # ── Guard: enforce hard limit ────────────────────────────────────────────
    if len(payload.assets) > _BATCH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size {len(payload.assets)} exceeds the limit of {_BATCH_LIMIT}.",
        )

    created_ids: List[uuid.UUID] = []

    try:
        # ── Atomic transaction ───────────────────────────────────────────────
        # SQLAlchemy Session opened by get_db() is in autocommit=False mode,
        # so every statement is already inside a transaction.  We call
        # db.begin() only when the session has no active transaction yet
        # (i.e. when it was freshly obtained).  Using begin_nested() would
        # work too, but a top-level transaction is cleaner here.
        with db.begin():
            for idx, asset_data in enumerate(payload.assets, start=1):
                new_asset = Asset(
                    id=uuid.uuid4(),
                    name=asset_data.name,
                    type=asset_data.type.value,
                    status=asset_data.status.value,
                )
                db.add(new_asset)
                # Flush after each insert so DB constraint violations surface
                # immediately with a meaningful index, before the full commit.
                try:
                    db.flush()
                except IntegrityError as ie:
                    # Rollback is handled automatically when `with db.begin()`
                    # block exits via exception.
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": f"Asset #{idx} caused an integrity error — batch rolled back.",
                            "asset":   asset_data.model_dump(),
                            "error":   str(ie.orig),
                        },
                    ) from ie

                created_ids.append(new_asset.id)
        # `with db.begin()` commits here only if no exception was raised.

    except HTTPException:
        raise  # Already formatted — let FastAPI handle it

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Database error — batch rolled back.",
                "error":   str(exc),
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unexpected error — batch rolled back.",
                "error":   str(exc),
            },
        ) from exc

    return BatchCreateResponse(
        created_count=len(created_ids),
        ids=created_ids,
    )


# ── DELETE /assets/batch ─────────────────────────────────────────────────────

@router.delete(
    "/batch",
    summary="Batch delete assets",
    description=(
        "Delete multiple assets by a comma-separated list of UUIDs supplied as "
        "the `ids` query parameter. IDs that do not exist are silently ignored."
    ),
    responses={
        200: {"description": "Operation completed (partial success is possible)"},
        400: {"description": "One or more IDs are not valid UUIDs"},
        500: {"description": "Unexpected server error"},
    },
)
def batch_delete_assets(
    ids: str = Query(
        ...,
        description="Comma-separated UUIDs, e.g. `?ids=uuid1,uuid2,uuid3`",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6,7cf1b2a3-1234-4abc-def0-9876543210ab"],
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:

    # ── Parse & validate UUIDs ───────────────────────────────────────────────
    raw_ids = [raw.strip() for raw in ids.split(",") if raw.strip()]

    parsed_ids: List[uuid.UUID] = []
    invalid: List[str] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(uuid.UUID(raw))
        except ValueError:
            invalid.append(raw)

    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "One or more IDs are not valid UUIDs.",
                "invalid_ids": invalid,
            },
        )

    if not parsed_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid IDs provided.",
        )

    # ── Delete inside a transaction ──────────────────────────────────────────
    try:
        with db.begin():
            # Fetch only the rows that actually exist so we can report
            # deleted vs not_found accurately without a separate COUNT query.
            existing: List[Asset] = (
                db.query(Asset)
                .filter(Asset.id.in_(parsed_ids))
                .all()
            )

            for asset in existing:
                db.delete(asset)
            # Commit happens automatically at end of `with db.begin()` block.

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Database error during batch delete.",
                "error":   str(exc),
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unexpected error during batch delete.",
                "error":   str(exc),
            },
        ) from exc

    deleted   = len(existing)
    not_found = len(parsed_ids) - deleted

    return {
        "deleted":   deleted,
        "not_found": not_found,
        "deleted_ids":   [str(a.id) for a in existing],
        "not_found_ids": [
            str(pid) for pid in parsed_ids
            if pid not in {a.id for a in existing}
        ],
    }