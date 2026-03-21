"""
app/api/scan.py
Direct scan endpoints (không qua background job).
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.domain.models import Asset
from app.domain.scanners import IPScanner, PortScanner
from app.infrastructure.database import get_db

router = APIRouter(prefix="/scan", tags=["Scan"])


class IPScanRequest(BaseModel):
    target: str = Field(..., min_length=1)


class PortScanRequest(BaseModel):
    target:  str               = Field(..., min_length=1)
    ports:   Optional[List[int]] = None
    timeout: float             = Field(1.0, ge=0.1, le=10.0)


@router.post("/ip", summary="IP Geolocation & ASN scan")
async def scan_ip(body: IPScanRequest) -> Dict[str, Any]:
    try:
        return await IPScanner().scan(body.target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"IP scan failed unexpectedly: {exc}") from exc


@router.post("/ports", summary="TCP Port scan (internal IPs only)")
async def scan_ports(body: PortScanRequest) -> Dict[str, Any]:
    try:
        return await PortScanner(ports=body.ports, timeout=body.timeout).scan(body.target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Port scan failed unexpectedly: {exc}") from exc


@router.post("/asset/{asset_id}", summary="Auto-scan asset by type")
async def scan_asset(asset_id: UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")

    try:
        import asyncio
        if asset.type == "ip":
            ip_result, port_result = await asyncio.gather(
                IPScanner().scan(asset.name),
                PortScanner().scan(asset.name),
            )
            return {"asset_id": str(asset.id), "asset_name": asset.name,
                    "asset_type": asset.type, "ip_scan": ip_result, "port_scan": port_result}
        else:
            ip_result = await IPScanner().scan(asset.name)
            return {"asset_id": str(asset.id), "asset_name": asset.name,
                    "asset_type": asset.type, "ip_scan": ip_result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Asset scan failed: {exc}") from exc