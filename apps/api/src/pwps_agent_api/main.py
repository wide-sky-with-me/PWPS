import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from pwps_agent_api.api.documents import DocumentApiError
from pwps_agent_api.api.documents import router as documents_router
from pwps_agent_api.api.runs import RunApiError
from pwps_agent_api.api.runs import router as runs_router
from pwps_agent_api.core.config import get_settings
from pwps_agent_api.core.readiness import ApplicationReadinessChecker
from pwps_agent_api.db.session import AsyncSessionMaker
from pwps_agent_api.schemas.api import ErrorResponse

APP_VERSION = "0.1.0"
log = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="pWPS Agent API",
    version=APP_VERSION,
)
app.state.limiter = limiter

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)
app.include_router(documents_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded: {exc.detail}",
            details={},
        ).model_dump(mode="json"),
    )


@app.exception_handler(RunApiError)
def run_api_error_handler(_: object, exc: RunApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.error.model_dump(mode="json"),
    )


@app.exception_handler(DocumentApiError)
def doc_api_error_handler(_: object, exc: DocumentApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.error.model_dump(mode="json"),
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(_: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with SCHEMA_VALIDATION_ERROR code."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code="SCHEMA_VALIDATION_ERROR",
            message="Request or response schema validation failed.",
            details={"errors": exc.errors()},
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled errors — returns WORKFLOW_INTERRUPTED."""
    log.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="WORKFLOW_INTERRUPTED",
            message="An unexpected error occurred.",
            details={"type": type(exc).__name__},
        ).model_dump(mode="json"),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "service": "pwps-agent-api",
        "status": "ok",
        "version": APP_VERSION,
    }


async def get_readiness_checker() -> ApplicationReadinessChecker:
    redis = Redis.from_url(get_settings().redis_url, decode_responses=False)
    return ApplicationReadinessChecker(AsyncSessionMaker, redis)


@app.get("/ready")
async def ready(
    checker: Annotated[ApplicationReadinessChecker, Depends(get_readiness_checker)],
) -> dict[str, Any]:
    checks = await checker.check()
    return {
        "service": "pwps-agent-api",
        "status": "ready" if all(value == "ok" for value in checks.values()) else "not_ready",
        "checks": checks,
    }
