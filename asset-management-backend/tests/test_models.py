"""
tests/test_models.py
Unit tests cho SQLAlchemy ORM models.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from app.domain.models import Asset, ScanJob


def make_asset(db, **overrides) -> Asset:
    defaults = dict(id=uuid.uuid4(), name="example.com", type="domain",
                    status="active", created_at=datetime.now(timezone.utc))
    asset = Asset(**{**defaults, **overrides})
    db.add(asset)
    db.flush()
    return asset


class TestAssetPersistence:

    def test_create_domain(self, db_session):
        asset = make_asset(db_session, name="example.com", type="domain")
        fetched = db_session.query(Asset).filter_by(id=asset.id).one()
        assert fetched.name == "example.com"
        assert fetched.type == "domain"
        assert fetched.status == "active"
        assert isinstance(fetched.id, uuid.UUID)

    def test_create_ip(self, db_session):
        asset = make_asset(db_session, name="10.0.0.1", type="ip")
        assert db_session.query(Asset).filter_by(id=asset.id).one().type == "ip"

    def test_create_service(self, db_session):
        asset = make_asset(db_session, name="nginx", type="service", status="inactive")
        assert db_session.query(Asset).filter_by(id=asset.id).one().status == "inactive"

    def test_default_status_active(self, db_session):
        asset = Asset(id=uuid.uuid4(), name="t.io", type="domain")
        db_session.add(asset)
        db_session.flush()
        assert asset.status == "active"

    def test_uuid_primary_key_unique(self, db_session):
        a1 = make_asset(db_session, name="a1.com")
        a2 = make_asset(db_session, name="a2.com")
        assert a1.id != a2.id


class TestAssetConstraints:

    def test_missing_name_raises(self, db_session):
        with pytest.raises((IntegrityError, StatementError)):
            db_session.add(Asset(id=uuid.uuid4(), type="domain"))
            db_session.flush()

    def test_missing_type_raises(self, db_session):
        with pytest.raises((IntegrityError, StatementError)):
            db_session.add(Asset(id=uuid.uuid4(), name="no-type.com"))
            db_session.flush()

    def test_duplicate_pk_raises(self, db_session):
        shared_id = uuid.uuid4()
        make_asset(db_session, id=shared_id, name="first.com")
        with pytest.raises(IntegrityError):
            make_asset(db_session, id=shared_id, name="second.com")

    def test_valid_enum_types(self, db_session):
        for t in ("domain", "ip", "service"):
            asset = Asset(id=uuid.uuid4(), name=f"{t}.com", type=t)
            db_session.add(asset)
            db_session.flush()
            assert db_session.query(Asset).filter_by(id=asset.id).one().type == t


class TestScanJobPersistence:

    def test_create_scan_job(self, db_session):
        asset = make_asset(db_session)
        job   = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status="pending")
        db_session.add(job)
        db_session.flush()
        fetched = db_session.query(ScanJob).filter_by(id=job.id).one()
        assert fetched.status == "pending"
        assert fetched.result is None

    def test_status_transitions(self, db_session):
        asset = make_asset(db_session)
        for st in ("pending", "running", "completed", "failed"):
            job = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status=st)
            db_session.add(job)
            db_session.flush()
            assert db_session.query(ScanJob).filter_by(id=job.id).one().status == st

    def test_orphan_asset_raises(self, db_session):
        with pytest.raises((IntegrityError, StatementError)):
            db_session.add(ScanJob(id=uuid.uuid4(), asset_id=uuid.uuid4(), status="pending"))
            db_session.flush()

    def test_stores_result_json(self, db_session):
        import json
        asset  = make_asset(db_session)
        result = json.dumps({"open_ports": [{"port": 22, "service": "ssh"}]})
        job    = ScanJob(id=uuid.uuid4(), asset_id=asset.id, status="completed", result=result)
        db_session.add(job)
        db_session.flush()
        parsed = json.loads(db_session.query(ScanJob).filter_by(id=job.id).one().result)
        assert parsed["open_ports"][0]["port"] == 22