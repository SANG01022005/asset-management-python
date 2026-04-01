"""
app/api/health.py
Health check endpoint.
"""
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.infrastructure.database as db_module  # import MODULE, không import variable
from app.infrastructure.database import get_db

router = APIRouter(tags=["Health"])


def _parse_pool_status(raw: str) -> Dict[str, Any]:
    patterns = {
        "pool_size": r"Pool size:\s*(\d+)",
        "idle":      r"Connections in pool:\s*(\d+)",
        "overflow":  r"Current Overflow:\s*(-?\d+)",
        "in_use":    r"Current Checked out connections:\s*(\d+)",
    }
    parsed: Dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        parsed[key] = int(match.group(1)) if match else 0
    parsed["max_open"]         = parsed["pool_size"] + max(parsed["overflow"], 0)
    parsed["open_connections"] = parsed["in_use"] + parsed["idle"]
    return parsed


@router.get("/health", summary="Health check")
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": {"connected": False}, "message": str(exc)},
        ) from exc

    try:
        # Đọc db_module.engine SAU khi connect_with_retry() đã gán — không import trực tiếp
        raw_pool   = db_module.engine.pool.status()
        pool_stats = _parse_pool_status(raw_pool)
    except Exception:
        pool_stats = {}

    return {
        "status":   "ok",
        "database": {
            "connected":        db_connected,
            "open_connections": pool_stats.get("open_connections", "N/A"),
            "in_use":           pool_stats.get("in_use",           "N/A"),
            "idle":             pool_stats.get("idle",             "N/A"),
            "max_open":         pool_stats.get("max_open",         "N/A"),
        },
    }