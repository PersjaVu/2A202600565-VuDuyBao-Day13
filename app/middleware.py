from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear contextvars to avoid leakage between requests (structlog binds
        # are process-global per async task; reset before binding new context).
        clear_contextvars()

        # Reuse an inbound x-request-id if the caller already has one (trace
        # propagation across services), otherwise mint a fresh req-<8-hex> id.
        incoming = request.headers.get("x-request-id")
        if incoming:
            correlation_id = incoming
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        # Bind so every log emitted while handling this request carries the id.
        bind_contextvars(correlation_id=correlation_id)

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Echo the id + server-side processing time back to the client so the
        # correlation id is visible end-to-end (curl -i, browser dev tools).
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.2f}"

        return response
