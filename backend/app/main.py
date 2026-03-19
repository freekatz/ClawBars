import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.database import engine
from app.core.exceptions import AppError, app_error_to_payload
from app.core.logging import setup_logging

# Initialise structured logging before anything else
setup_logging()

logger = logging.getLogger(__name__)

# Import all models so Base.metadata is populated before create_all
import app.models.activity  # noqa: F401
import app.models.agent     # noqa: F401
import app.models.bar       # noqa: F401
import app.models.coin      # noqa: F401
import app.models.config    # noqa: F401
import app.models.invite    # noqa: F401
import app.models.post      # noqa: F401
import app.models.tag       # noqa: F401
import app.models.user      # noqa: F401
import app.models.vote      # noqa: F401
from app.models.base import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting ClawBars API (debug=%s, workers=%s)", settings.debug, settings.workers)

    # Create tables only if alembic hasn't run (fallback for local dev).
    # In production, Dockerfile runs `alembic upgrade head` before starting.
    from sqlalchemy import inspect as sa_inspect

    async with engine.begin() as conn:
        has_tables = await conn.run_sync(lambda c: sa_inspect(c).has_table("users"))
        if not has_tables:
            logger.info("No tables found — running Base.metadata.create_all (dev fallback)")
            await conn.run_sync(Base.metadata.create_all)

    # Bootstrap initial admin user from env config
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.user import User
    import bcrypt
    from nanoid import generate as nanoid

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(User).where(User.email == settings.init_admin_email, User.deleted_at.is_(None))
        )
        if not result.scalar_one_or_none():
            admin = User(
                id=nanoid(size=21),
                email=settings.init_admin_email,
                password_hash=bcrypt.hashpw(
                    settings.init_admin_password.encode(), bcrypt.gensalt()
                ).decode(),
                name=settings.init_admin_name,
                role="admin",
                status="active",
            )
            session.add(admin)
            await session.commit()
            logger.info("Admin user seeded: %s", settings.init_admin_email)

    logger.info("ClawBars API ready")
    yield
    logger.info("Shutting down ClawBars API")
    await engine.dispose()


app = FastAPI(title="ClawBars API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "AppError %s: %s (path=%s)",
        exc.code,
        exc.message,
        request.url.path,
    )
    payload = app_error_to_payload(exc)
    return JSONResponse(status_code=exc.http_status, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    payload = app_error_to_payload(AppError(code=40002, message="Validation failed", detail=exc.errors()))
    return JSONResponse(status_code=400, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log and return safe 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    payload = app_error_to_payload(AppError(code=50000, message="Internal server error", http_status=500))
    return JSONResponse(status_code=500, content=payload.model_dump())


app.include_router(api_router, prefix="/api/v1")
