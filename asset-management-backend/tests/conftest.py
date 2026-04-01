"""
tests/conftest.py
Shared fixtures — SQLite in-memory, không cần PostgreSQL.

Chiến lược: inject _TEST_ENGINE vào db_module TRƯỚC khi import main.
main.py tự phát hiện SQLite → bỏ qua connect_with_retry().
Không cần mock lifespan nữa.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── 1. Setup SQLite TRƯỚC KHI import main ─────────────────────────────────────
import app.infrastructure.database as db_module
from app.domain.models import Base

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(_TEST_ENGINE, "connect")
def _set_fk(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

_TestSession = sessionmaker(bind=_TEST_ENGINE, autocommit=False, autoflush=False)

# Inject TRƯỚC khi import main — main.py sẽ detect SQLite và skip connect_with_retry
db_module.engine       = _TEST_ENGINE
db_module.SessionLocal = _TestSession

# ── 2. Import main SAU KHI inject ─────────────────────────────────────────────
from main import app  # noqa: E402 — main.py detect SQLite, không gọi PostgreSQL


# ── 3. Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    return _TEST_ENGINE


@pytest.fixture(autouse=True)
def reset_db():
    """Drop + recreate tất cả bảng trước mỗi test → isolation tuyệt đối."""
    Base.metadata.drop_all(bind=_TEST_ENGINE)
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture
def db_session():
    session = _TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient

    def _override_get_db():
        yield db_session

    app.dependency_overrides[db_module.get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()