"""
app/api/export_router.py
Bài 6.5 — Export Reports (CSV + JSON).
Fix: dùng joinedload để tránh lazy loading sau khi session đóng.
"""
import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.domain.models import Asset, ScanJob, Tag
from app.domain.schemas import AssetStatus, AssetType
from app.infrastructure.database import get_db

router = APIRouter(prefix="/export", tags=["Export Reports"])


def _build_csv(headers: list, rows: list, filename_prefix: str) -> StreamingResponse:
    """Build StreamingResponse — serialize toàn bộ trước khi stream."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([str(c) if c is not None else "" for c in row])
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename_prefix}_{timestamp}.csv"},
    )


@router.get("/assets", summary="Export assets as CSV")
def export_assets(
    type:   Optional[AssetType]   = Query(None),
    status: Optional[AssetStatus] = Query(None),
    db:     Session                = Depends(get_db),
):
    q = db.query(Asset).options(joinedload(Asset.tags))
    if type:
        q = q.filter(Asset.type == type.value)
    if status:
        q = q.filter(Asset.status == status.value)
    assets = q.order_by(Asset.created_at.desc()).all()

    headers = ["id", "name", "type", "status", "tags", "created_at",
               "last_scan_status", "last_scan_at"]
    rows = []
    for asset in assets:
        last_job = (
            db.query(ScanJob)
            .filter(ScanJob.asset_id == asset.id)
            .order_by(ScanJob.created_at.desc())
            .first()
        )
        rows.append([
            asset.id, asset.name, asset.type, asset.status,
            ";".join(t.name for t in asset.tags),
            asset.created_at.isoformat() if asset.created_at else "",
            last_job.status if last_job else "",
            last_job.completed_at.isoformat() if last_job and last_job.completed_at else "",
        ])
    return _build_csv(headers, rows, "assets")


@router.get("/scan-results", summary="Export scan results as CSV")
def export_scan_results(
    asset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(ScanJob)
        .options(joinedload(ScanJob.asset))
        .filter(ScanJob.status == "completed")
        .order_by(ScanJob.completed_at.desc())
    )
    if asset_id:
        q = q.filter(ScanJob.asset_id == asset_id)
    jobs = q.all()

    headers = ["job_id", "asset_id", "asset_name", "asset_type",
               "status", "started_at", "completed_at",
               "country", "city", "asn_number", "asn_name", "open_ports"]
    rows = []
    for job in jobs:
        asset = job.asset
        geo, asn, open_ports = {}, {}, ""
        if job.result:
            try:
                result    = json.loads(job.result)
                ip_scan   = result.get("ip_scan") or {}
                geo       = ip_scan.get("geolocation") or {}
                asn       = ip_scan.get("asn") or {}
                ports     = (result.get("port_scan") or {}).get("open_ports") or []
                open_ports = ";".join(f"{p['port']}/{p['service']}" for p in ports)
            except Exception:
                pass
        rows.append([
            job.id, job.asset_id,
            asset.name if asset else "", asset.type if asset else "",
            job.status,
            job.started_at.isoformat()   if job.started_at   else "",
            job.completed_at.isoformat() if job.completed_at else "",
            geo.get("country", ""), geo.get("city", ""),
            asn.get("number", ""), asn.get("name", ""),
            open_ports,
        ])
    return _build_csv(headers, rows, "scan_results")


@router.get("/report", summary="JSON summary report")
def export_report(db: Session = Depends(get_db)) -> JSONResponse:
    assets    = db.query(Asset).options(joinedload(Asset.tags)).all()
    scan_jobs = db.query(ScanJob).all()
    tags      = db.query(Tag).options(joinedload(Tag.assets)).all()

    by_type   = {"domain": 0, "ip": 0, "service": 0}
    by_status = {"active": 0, "inactive": 0}
    for a in assets:
        by_type[a.type]     = by_type.get(a.type, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1

    scan_by_status = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
    for j in scan_jobs:
        scan_by_status[j.status] = scan_by_status.get(j.status, 0) + 1

    completed    = scan_by_status["completed"]
    failed       = scan_by_status["failed"]
    total_done   = completed + failed
    success_rate = round(completed / total_done * 100, 1) if total_done else 0
    scanned_ids  = {j.asset_id for j in scan_jobs}

    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assets": {"total": len(assets), "by_type": by_type, "by_status": by_status},
        "scans": {"total": len(scan_jobs), "by_status": scan_by_status,
                  "success_rate": f"{success_rate}%"},
        "tags": {
            "total": len(tags),
            "summary": [{"name": t.name, "color": t.color, "asset_count": len(t.assets)}
                        for t in sorted(tags, key=lambda t: t.name)],
        },
        "never_scanned": [a.name for a in assets if a.id not in scanned_ids],
    })