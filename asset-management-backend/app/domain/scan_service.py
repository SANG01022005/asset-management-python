"""
app/domain/scan_service.py
Background scan service: pending → running → completed | failed
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import app.infrastructure.database as db_module
from app.domain.models import Asset, ScanJob
from app.domain.scanners import IPScanner, PortScanner

logger = logging.getLogger(__name__)


async def run_scan_job(job_id: UUID, asset_id: UUID) -> None:
    db = db_module.SessionLocal()
    try:
        # 1. pending → running
        job: ScanJob = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job is None:
            logger.error("run_scan_job: job %s not found", job_id)
            return

        job.status     = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("🔄 Scan job %s started (asset=%s)", job_id, asset_id)

        # 2. Fetch asset
        asset: Asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset is None:
            raise ValueError(f"Asset {asset_id} not found.")

        target = asset.name

        # 3. Dispatch scanners
        if asset.type == "ip":
            ip_result, port_result = await asyncio.gather(
                IPScanner().scan(target),
                PortScanner().scan(target),
            )
            scan_result = {"asset_type": "ip", "ip_scan": ip_result, "port_scan": port_result}
        else:
            ip_result = await IPScanner().scan(target)
            scan_result = {"asset_type": asset.type, "ip_scan": ip_result}

        # 4a. running → completed
        job.status       = "completed"
        job.result       = json.dumps(scan_result)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("✅ Scan job %s completed", job_id)

    except Exception as exc:
        logger.exception("💥 Scan job %s failed: %s", job_id, exc)
        try:
            db.rollback()
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if job:
                job.status       = "failed"
                job.error        = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as inner:
            logger.error("Failed to persist error state: %s", inner)
            db.rollback()
    finally:
        db.close()