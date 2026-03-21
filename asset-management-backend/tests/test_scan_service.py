"""
tests/test_scan_service.py
Unit tests cho run_scan_job().
Fix: patch tại nơi được import (scan_service.py), không phải nơi định nghĩa.
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.models import Asset, ScanJob
from app.domain.scan_service import run_scan_job


@pytest.mark.asyncio
async def test_ip_asset_completed(db_session):
    asset = Asset(id=uuid.uuid4(), name="8.8.8.8", type="ip", status="active")
    job   = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status="pending")
    db_session.add_all([asset, job])
    db_session.commit()

    mock_ip   = {"status": "ok", "ip": "8.8.8.8"}
    mock_port = {"status": "ok", "open_ports": []}

    with patch("app.domain.scan_service.IPScanner") as MockIP, \
         patch("app.domain.scan_service.PortScanner") as MockPort, \
         patch("app.domain.scan_service.db_module.SessionLocal", return_value=db_session):
        MockIP.return_value.scan   = AsyncMock(return_value=mock_ip)
        MockPort.return_value.scan = AsyncMock(return_value=mock_port)
        await run_scan_job(job.id, asset.id)

    db_session.expire_all()
    updated = db_session.query(ScanJob).filter_by(id=job.id).first()
    assert updated.status == "completed"
    result = json.loads(updated.result)
    assert result["asset_type"]        == "ip"
    assert result["ip_scan"]["status"] == "ok"
    assert "port_scan" in result


@pytest.mark.asyncio
async def test_domain_asset_completed(db_session):
    asset = Asset(id=uuid.uuid4(), name="google.com", type="domain", status="active")
    job   = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status="pending")
    db_session.add_all([asset, job])
    db_session.commit()

    mock_ip = {"status": "ok", "ip": "142.250.4.100"}

    with patch("app.domain.scan_service.IPScanner") as MockIP, \
         patch("app.domain.scan_service.db_module.SessionLocal", return_value=db_session):
        MockIP.return_value.scan = AsyncMock(return_value=mock_ip)
        await run_scan_job(job.id, asset.id)

    db_session.expire_all()
    updated = db_session.query(ScanJob).filter_by(id=job.id).first()
    assert updated.status == "completed"
    result = json.loads(updated.result)
    assert result["asset_type"] == "domain"
    assert "port_scan" not in result


@pytest.mark.asyncio
async def test_fails_gracefully(db_session):
    asset = Asset(id=uuid.uuid4(), name="fail.com", type="domain", status="active")
    job   = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status="pending")
    db_session.add_all([asset, job])
    db_session.commit()

    with patch("app.domain.scan_service.IPScanner") as MockIP, \
         patch("app.domain.scan_service.db_module.SessionLocal", return_value=db_session):
        MockIP.return_value.scan = AsyncMock(side_effect=Exception("Network timeout"))
        await run_scan_job(job.id, asset.id)

    db_session.expire_all()
    updated = db_session.query(ScanJob).filter_by(id=job.id).first()
    assert updated.status == "failed"
    assert "Network timeout" in updated.error


@pytest.mark.asyncio
async def test_not_found_silent(db_session):
    """job_id không tồn tại → return silently, không crash."""
    with patch("app.domain.scan_service.db_module.SessionLocal", return_value=db_session):
        await run_scan_job(uuid.uuid4(), uuid.uuid4())