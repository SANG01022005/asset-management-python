"""
app/domain/schemas.py
Pydantic schemas cho Asset API.
"""
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    domain  = "domain"
    ip      = "ip"
    service = "service"


class AssetStatus(str, Enum):
    active   = "active"
    inactive = "inactive"


class AssetBase(BaseModel):
    name:   str         = Field(..., min_length=1, max_length=255)
    type:   AssetType
    status: AssetStatus = AssetStatus.active


class AssetCreate(AssetBase):
    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        allowed = {e.value for e in AssetType}
        if v not in allowed:
            raise ValueError(f"Invalid type '{v}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        allowed = {e.value for e in AssetStatus}
        if v not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed: {sorted(allowed)}")
        return v


class AssetResponse(AssetBase):
    id:         UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchCreateRequest(BaseModel):
    assets: List[AssetCreate] = Field(..., min_length=1)


class BatchCreateResponse(BaseModel):
    created_count: int
    ids:           List[UUID]