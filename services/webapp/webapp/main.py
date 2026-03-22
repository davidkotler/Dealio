"""FastAPI application entry point."""
from __future__ import annotations
from uvicorn import run
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from webapp.config import get_settings
from webapp.domains.identity.adapters.in_memory_token_store import InMemoryTokenStore
import webapp.infrastructure.database  # noqa: F401 — registers all ORM models with WebappBase.metadata
from webapp.infrastructure.database.base import WebappBase
from webapp.domains.identity.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOIDCStateError,
    InvalidResetTokenError,
    OIDCExchangeError,
    OIDCTokenVerificationError,
    PasswordChangeNotAllowedError,
    WeakPasswordError,
)
from webapp.domains.identity.routes.v1.auth import router as auth_router
from webapp.domains.notifier.exceptions import NotificationNotFoundError
from webapp.domains.tracker.exceptions import (
    DuplicateProductError,
    InvalidProductUrlError,
    ProductLimitExceededError,
    ProductNotFoundError,
    ScrapingFailedError,
)
from webapp.domains.tracker.routes.v1.notifications import router as notifications_router
from webapp.domains.tracker.routes.v1.products import router as products_router
from webapp.middleware import RequestLoggingMiddleware
from webapp.models.contracts.api.errors import ErrorResponse



logger = structlog.get_logger()


def configure_logging() -> None:
    use_json = False
    log_level = "INFO"

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Any = structlog.processors.JSONRenderer() if use_json else structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter_processors: list[Any] = [structlog.stdlib.ProcessorFormatter.remove_processors_meta]
    if use_json:
        formatter_processors.append(structlog.processors.dict_tracebacks)
    formatter_processors.append(renderer)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=formatter_processors,
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)


_DOMAIN_EXCEPTION_MAP: dict[type[Exception], tuple[int, str]] = {
    EmailAlreadyRegisteredError: (409, "EMAIL_ALREADY_REGISTERED"),
    InvalidCredentialsError: (401, "INVALID_CREDENTIALS"),
    WeakPasswordError: (422, "WEAK_PASSWORD"),
    PasswordChangeNotAllowedError: (422, "PASSWORD_CHANGE_NOT_ALLOWED"),
    InvalidResetTokenError: (400, "INVALID_RESET_TOKEN"),
    InvalidOIDCStateError: (400, "INVALID_OIDC_STATE"),
    OIDCExchangeError: (502, "OIDC_EXCHANGE_FAILED"),
    OIDCTokenVerificationError: (401, "OIDC_TOKEN_VERIFICATION_FAILED"),
    InvalidProductUrlError: (422, "INVALID_PRODUCT_URL"),
    ProductLimitExceededError: (422, "PRODUCT_LIMIT_EXCEEDED"),
    DuplicateProductError: (409, "DUPLICATE_PRODUCT"),
    ScrapingFailedError: (422, "SCRAPING_FAILED"),
    ProductNotFoundError: (404, "PRODUCT_NOT_FOUND"),
    NotificationNotFoundError: (404, "NOTIFICATION_NOT_FOUND"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(WebappBase.metadata.create_all)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.token_store = InMemoryTokenStore()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Dealio Webapp", version="1.0.0", lifespan=lifespan)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=[settings.app_base_url],
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _make_domain_handler(status_code: int, code: str):  # type: ignore[return]
        async def handler(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=status_code,
                content=ErrorResponse(detail=str(exc), code=code).model_dump(),
            )
        return handler

    for exc_class, (status_code, code) in _DOMAIN_EXCEPTION_MAP.items():
        app.add_exception_handler(exc_class, _make_domain_handler(status_code, code))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=detail, code=detail).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = str(errors[0].get("msg", "Validation error")) if errors else "Validation error"
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(detail=message, code="VALIDATION_ERROR").model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        await logger.aexception(
            "request.unhandled_exception",
            http_method=request.method,
            http_path=request.url.path,
            error_type=type(exc).__name__,
            error_code="INTERNAL_ERROR",
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="Internal server error", code="INTERNAL_ERROR").model_dump(),
        )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(products_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health(request: Request) -> dict[str, str]:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}

    return app


app = create_app()

if __name__ == '__main__':
    run("main:app",host="localhost",port=8001,reload=True)
