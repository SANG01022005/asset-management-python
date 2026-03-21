"""
app/api/scan_router.py
Background scan job endpoints.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.domain.models import Asset, ScanJob
from app.domain.scan_schemas import ScanJobCreate, ScanJobResponse
from app.domain.scan_service import run_scan_job
from app.infrastructure.database import get_db

router = APIRouter(tags=["Scan Jobs"])


@router.post(
    "/assets/{asset_id}/scan",
    status_code=http_status.HTTP_202_ACCEPTED,
    response_model=ScanJobCreate,
    summary="Enqueue background scan",
)
def enqueue_scan(
    asset_id:         uuid.UUID,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
) -> ScanJobCreate:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")

    active = (
        db.query(ScanJob)
        .filter(ScanJob.asset_id == asset_id, ScanJob.status.in_(["pending", "running"]))
        .first()
    )
    if active:
        raise HTTPException(
            status_code=409,
            detail={"message": "A scan is already pending/running.", "job_id": str(active.id)},
        )

    job = ScanJob(id=uuid.uuid4(), asset_id=asset_id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_async_in_background, job_id=job.id, asset_id=asset_id)

    return ScanJobCreate(
        job_id=job.id,
        asset_id=asset_id,
        status="pending",
        message=f"Scan queued. Poll GET /scan/jobs/{job.id}",
    )


def _run_async_in_background(job_id: uuid.UUID, asset_id: uuid.UUID) -> None:
    import asyncio
    asyncio.run(run_scan_job(job_id=job_id, asset_id=asset_id))


@router.get(
    "/scan/jobs/{job_id}",
    response_model=ScanJobResponse,
    response_model_by_alias=True,
    summary="Get scan job status",
)
def get_scan_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> ScanJob:
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.get(
    "/scan/jobs",
    response_model=List[ScanJobResponse],
    response_model_by_alias=True,
    summary="List scan jobs",
)
def list_scan_jobs(
    asset_id:   Optional[uuid.UUID] = Query(None),
    job_status: Optional[str]       = Query(None, alias="status"),
    limit:      int                  = Query(50, ge=1, le=200),
    db:         Session              = Depends(get_db),
) -> List[ScanJob]:
    q = db.query(ScanJob)
    if asset_id:
        q = q.filter(ScanJob.asset_id == asset_id)
    if job_status:
        q = q.filter(ScanJob.status == job_status)
    return q.order_by(ScanJob.created_at.desc()).limit(limit).all()


@router.delete(
    "/scan/jobs/{job_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete scan job",
)
def delete_scan_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    db.delete(job)
    db.commit()