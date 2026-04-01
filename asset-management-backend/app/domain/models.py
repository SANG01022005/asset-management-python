"""
app/domain/models.py
SQLAlchemy ORM models: Tag, Asset, ScanJob
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base

# ── Asset ↔ Tag (many-to-many) ────────────────────────────────────────────────
asset_tags = Table(
    "asset_tags",
    Base.metadata,
    Column("asset_id", UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id",   UUID(as_uuid=True), ForeignKey("tags.id",   ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name       = Column(String(64), nullable=False, unique=True, index=True)
    color      = Column(String(7), nullable=False, default="#6b7280")
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    assets = relationship("Asset", secondary=asset_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


class Asset(Base):
    __tablename__ = "assets"

    id     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name   = Column(String(255), nullable=False, index=True)
    type   = Column(SAEnum("domain", "ip", "service", name="asset_type_enum"), nullable=False)
    status = Column(SAEnum("active", "inactive", name="asset_status_enum"),
                    nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    tags      = relationship("Tag",     secondary=asset_tags, back_populates="assets")
    scan_jobs = relationship("ScanJob", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset(name='{self.name}', type='{self.type}')>"


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    status   = Column(
        SAEnum("pending", "running", "completed", "failed", name="scan_job_status_enum"),
        nullable=False, default="pending", server_default="pending", index=True,
    )
    result       = Column(Text, nullable=True)
    error        = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    asset = relationship("Asset", back_populates="scan_jobs")

    def __repr__(self):
        return f"<ScanJob(id={self.id}, status='{self.status}')>"