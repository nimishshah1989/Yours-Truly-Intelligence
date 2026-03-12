"""Simple in-memory sliding-window rate limiter per IP.

Returns 429 when rate_limit_per_minute is exceeded.
Disabled when rate_limit_per_minute <= 0.
"""

import logging
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

logger = logging.getLogger("ytip.middleware.rate_limit")

PUBLIC_PATHS = frozenset({"/api/health", "/docs", "/openapi.json", "/redoc"})

_request_log: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per client IP."""

    async def dispatch(self, request: Request, call_next):
        limit = settings.rate_limit_per_minute
        if limit <= 0:
            return await call_next(request)

        path = request.url.path
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60.0

        with _rate_lock:
            timestamps = _request_log[client_ip]
            timestamps[:] = [t for t in timestamps if t > window_start]

            if len(timestamps) >= limit:
                logger.warning(
                    "Rate limit exceeded for %s (%d/%d in 60s)",
                    client_ip, len(timestamps), limit,
                )
                return Response(
                    content='{"detail":"Rate limit exceeded. Try again shortly."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"},
                )

            timestamps.append(now)

        response = await call_next(request)

        remaining = max(0, limit - len(_request_log.get(client_ip, [])))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
