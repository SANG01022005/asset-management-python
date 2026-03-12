from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetType(str, Enum):
    domain  = "domain"
    ip      = "ip"
    service = "service"


class AssetStatus(str, Enum):
    active   = "active"
    inactive = "inactive"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AssetBase(BaseModel):
    name:   str         = Field(..., min_length=1, max_length=255, examples=["example.com"])
    type:   AssetType   = Field(..., examples=[AssetType.domain])
    status: AssetStatus = Field(AssetStatus.active, examples=[AssetStatus.active])


# ---------------------------------------------------------------------------
# Create  (input)
# ---------------------------------------------------------------------------

class AssetCreate(AssetBase):
    """Payload received from the client when creating a single asset."""

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, value: str) -> str:
        allowed = {e.value for e in AssetType}
        if value not in allowed:
            raise ValueError(
                f"Invalid asset type '{value}'. "
                f"Allowed values: {sorted(allowed)}"
            )
        return value

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {e.value for e in AssetStatus}
        if value not in allowed:
            raise ValueError(
                f"Invalid asset status '{value}'. "
                f"Allowed values: {sorted(allowed)}"
            )
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"name": "example.com", "type": "domain", "status": "active"},
                {"name": "192.168.1.1",  "type": "ip",     "status": "active"},
                {"name": "nginx-proxy",  "type": "service","status": "inactive"},
            ]
        }
    }


# ---------------------------------------------------------------------------
# Response  (output)
# ---------------------------------------------------------------------------

class AssetResponse(AssetBase):
    """Full asset representation returned to the client."""

    id:         UUID
    created_at: datetime

    model_config = {
        "from_attributes": True,          # replaces orm_mode in Pydantic v2
        "json_schema_extra": {
            "examples": [
                {
                    "id":         "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name":       "example.com",
                    "type":       "domain",
                    "status":     "active",
                    "created_at": "2024-01-15T10:30:00Z",
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# Batch  (input / output)
# ---------------------------------------------------------------------------

class BatchCreateRequest(BaseModel):
    """Payload for creating multiple assets in a single request."""

    assets: List[AssetCreate] = Field(
        ...,
        min_length=1,
        description="List of assets to create (at least 1 item required).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "assets": [
                        {"name": "example.com", "type": "domain",  "status": "active"},
                        {"name": "10.0.0.1",    "type": "ip",      "status": "active"},
                        {"name": "redis-cache", "type": "service", "status": "inactive"},
                    ]
                }
            ]
        }
    }


class BatchCreateResponse(BaseModel):
    """Summary returned after a batch-create operation."""

    created_count: int       = Field(..., description="Number of assets successfully created.")
    ids:           List[UUID] = Field(..., description="UUIDs of the newly created assets.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "created_count": 3,
                    "ids": [
                        "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "7cf1b2a3-1234-4abc-def0-9876543210ab",
                        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    ],
                }
            ]
        }
    }