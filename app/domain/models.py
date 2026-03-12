import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )
    name = Column(
        String(255),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum("domain", "ip", "service", name="asset_type_enum"),
        nullable=False,
    )
    status = Column(
        SAEnum("active", "inactive", name="asset_status_enum"),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Asset(id={self.id}, name='{self.name}', "
            f"type='{self.type}', status='{self.status}')>"
        )