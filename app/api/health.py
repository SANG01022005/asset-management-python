import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.database import engine, get_db

router = APIRouter(tags=["Health"])


def _parse_pool_status(raw: str) -> Dict[str, Any]:
    """
    Parse the string returned by engine.pool.status(), e.g.:
    'Pool size: 10  Connections in pool: 2 Current Overflow: 0 Current Checked out connections: 1'
    Returns a clean dict with integer values.
    """
    patterns = {
        "pool_size":     r"Pool size:\s*(\d+)",
        "idle":          r"Connections in pool:\s*(\d+)",
        "overflow":      r"Current Overflow:\s*(-?\d+)",
        "in_use":        r"Current Checked out connections:\s*(\d+)",
    }
    parsed: Dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        parsed[key] = int(match.group(1)) if match else 0

    parsed["max_open"] = parsed["pool_size"] + max(parsed["overflow"], 0)
    parsed["open_connections"] = parsed["in_use"] + parsed["idle"]
    return parsed


@router.get(
    "/health",
    summary="Health check",
    description="Verifies API liveness and database connectivity.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Database unreachable"},
    },
)
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    # ── Database ping ────────────────────────────────────────────────────────
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status":   "error",
                "database": {"connected": False},
                "message":  f"Database unreachable: {exc}",
            },
        ) from exc

    # ── Connection pool stats ────────────────────────────────────────────────
    try:
        raw_pool   = engine.pool.status()
        pool_stats = _parse_pool_status(raw_pool)
    except Exception:
        pool_stats = {}

    return {
        "status":   "ok",
        "database": {
            "connected":       db_connected,
            "open_connections": pool_stats.get("open_connections", "N/A"),
            "in_use":          pool_stats.get("in_use",           "N/A"),
            "idle":            pool_stats.get("idle",             "N/A"),
            "max_open":        pool_stats.get("max_open",         "N/A"),
        },
    }