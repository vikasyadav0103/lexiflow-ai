import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine, init_db
from app.routes import word_routes
from app.services.ml_service import MLService

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

ml_service: MLService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize dependencies once per application process."""
    global ml_service
    logger.info("Starting LexiFlow AI API")
    init_db()
    ml_service = MLService()
    app.state.ml_service = ml_service
    try:
        yield
    finally:
        logger.info("Stopping LexiFlow AI API")
        engine.dispose()


app = FastAPI(
    title="LexiFlow AI API",
    description="Dictionary lookup and language-analysis endpoints.",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(word_routes.router, prefix="/api", tags=["words"])


@app.get("/", tags=["health"])
async def root():
    return {
        "name": "LexiFlow AI API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health/live", tags=["health"])
async def liveness():
    """Process liveness; does not trigger network or model downloads."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness():
    """Readiness reports initialization state without downloading assets."""
    model_ready = bool(ml_service and getattr(ml_service, "_initialized", False))
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ready = True
    except Exception:
        logger.exception("Database readiness check failed")
        database_ready = False

    # The embedding model is intentionally lazy-loaded; it is not required for
    # the dictionary-only endpoints to serve requests.
    ready = database_ready
    payload = {
        "status": "ready" if ready else "not_ready",
        "database": database_ready,
        "ml_service": "initialized" if model_ready else "lazy",
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get("/health", include_in_schema=False)
async def health_compatibility():
    """Compatibility alias for older deployments."""
    return await liveness()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request exception: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
