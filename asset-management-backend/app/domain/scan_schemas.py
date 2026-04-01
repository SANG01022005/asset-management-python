"""
app/domain/scan_schemas.py
Pydantic schemas cho Scan Job API.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ScanJobCreate(BaseModel):
    """Returned immediately after POST /assets/{id}/scan — 202 Accepted."""
    job_id:   UUID
    asset_id: UUID
    status:   str = "pending"
    message:  str = "Scan job queued."


class ScanJobResponse(BaseModel):
    """
    Full job record returned by GET /scan/jobs/{job_id}.
    ORM has column `id` → exposed as `job_id` in API.
    """
    job_id: UUID = Field(
        validation_alias="id",
        serialization_alias="job_id",
    )
    asset_id:     UUID
    status:       str
    result:       Optional[Dict[str, Any]] = None
    error:        Optional[str]            = None
    created_at:   datetime
    started_at:   Optional[datetime]       = None
    completed_at: Optional[datetime]       = None

    @field_validator("result", mode="before")
    @classmethod
    def parse_result(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }