"""
asset-management-backend/main.py
FastAPI entry point.
"""
import logging
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.infrastructure.database as db_module
from app.domain.models import Base
from app.api.health       import router as health_router
from app.api.assets       import router as assets_router
from app.api.scan_router  import router as scan_router
from app.api.scan         import router as scan_api_router
from app.api.tags_router  import router as tags_router
from app.api.export_router import router as export_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Asset Management API...")
    db_module.connect_with_retry(max_retries=5)
    Base.metadata.create_all(bind=db_module.engine)
    logger.info("✅ All tables verified / created.")
    yield
    logger.info("🛑 Shutting down...")
    db_module.engine.dispose()
    logger.info("👋 Shutdown complete.")


app = FastAPI(title="Asset Management API", lifespan=lifespan, docs_url="/docs")

# CORS
_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost")
ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        elapsed = (time.perf_counter() - start) * 1000
        logger.error("💥 %s %s — UNHANDLED ERROR %.1f ms: %s",
                     request.method, request.url.path, elapsed, exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    elapsed = (time.perf_counter() - start) * 1000
    status  = response.status_code
    icon    = "✅" if status < 300 else "↩️" if status < 400 else "⚠️" if status < 500 else "💥"
    logger.info("%s %s %s — %s %.1f ms", icon, request.method, request.url.path, status, elapsed)
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
    return response


app.include_router(health_router)
app.include_router(assets_router)
app.include_router(scan_router)
app.include_router(scan_api_router)
app.include_router(tags_router)
app.include_router(export_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)