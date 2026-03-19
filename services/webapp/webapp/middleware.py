"""HTTP request logging middleware."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        clear_contextvars()
        bind_contextvars(
            request_id=request.headers.get("x-request-id", str(uuid.uuid4())),
            http_method=request.method,
            http_path=request.url.path,
        )

        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        await logger.ainfo(
            "http.request_completed",
            http_status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response