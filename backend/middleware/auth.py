"""API key authentication middleware.

Disabled when settings.api_key is empty (development mode).
Health check and docs endpoints are always public.
"""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

logger = logging.getLogger("ytip.middleware.auth")

PUBLIC_PATHS = frozenset({"/api/health", "/docs", "/openapi.json", "/redoc"})


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests missing a valid X-API-Key header."""

    async def dispatch(self, request: Request, call_next):
        if not settings.api_key:
            return await call_next(request)

        path = request.url.path
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != settings.api_key:
            logger.warning(
                "Unauthorized request to %s from %s",
                path,
                request.client.host if request.client else "unknown",
            )
            return Response(
                content='{"detail":"Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
