import time
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.infrastructure.database import connect_with_retry, engine
from app.domain.models import Base
from app.api.health import router as health_router
from app.api.assets import router as assets_router

# ── Logging setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("🚀 Starting Asset Management API...")

    connect_with_retry(max_retries=5)
    logger.info("📦 Running Base.metadata.create_all()...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ All tables verified / created.")

    yield  # application is live and serving requests

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down — disposing database engine...")
    engine.dispose()
    logger.info("👋 Shutdown complete.")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Asset Management API",
    description=(
        "Manage digital assets (domains, IPs, services) "
        "with full CRUD and batch operations."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware: request timing log ───────────────────────────────────────────

@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:                          # safety net
        elapsed = (time.perf_counter() - start) * 1000
        logger.error(
            "💥 %s %s — UNHANDLED ERROR after %.1f ms: %s",
            request.method, request.url.path, elapsed, exc,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    elapsed = (time.perf_counter() - start) * 1000
    status  = response.status_code

    # Choose emoji based on HTTP status range for quick visual scanning
    icon = "✅" if status < 300 else "↩️" if status < 400 else "⚠️" if status < 500 else "💥"

    logger.info(
        "%s %s %s — %s %.1f ms",
        icon, request.method, request.url.path, status, elapsed,
    )
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(assets_router)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )