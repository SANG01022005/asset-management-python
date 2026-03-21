"""
tests/conftest.py
Shared fixtures cho toàn bộ test suite.

Bài học từ các lỗi cũ:
1. Inject db_module TRƯỚC khi import main (tránh connect_with_retry crash)
2. Mock lifespan TRƯỚC khi import main (tránh TestClient hang)
3. reset_db autouse → isolation tuyệt đối giữa các tests
4. client fixture export get_db override đúng db_session
"""
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── 1. Setup SQLite test engine TRƯỚC KHI import main ─────────────────────────
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

# Inject vào db_module TRƯỚC khi import main
db_module.engine       = _TEST_ENGINE
db_module.SessionLocal = _TestSession

# ── 2. Mock lifespan để không gọi connect_with_retry() hay engine.dispose() ──
@asynccontextmanager
async def _mock_lifespan(app):
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield  # không dispose — tránh phá _TEST_ENGINE

with patch("main.lifespan", _mock_lifespan):
    from main import app  # import SAU khi đã patch


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
    """SQLite session cho mỗi test."""
    session = _TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """TestClient với get_db override — dùng db_session của test."""
    from fastapi.testclient import TestClient

    def _override_get_db():
        yield db_session

    app.dependency_overrides[db_module.get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()