import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings
from app.core.metrics import request_metrics

logger = logging.getLogger("knowledge_base")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", uuid4().hex)
        start = time.perf_counter()
        request_metrics.start_request()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            request_metrics.finish_request(request.method, request.url.path, status_code, elapsed_ms)
            logger.info(
                "request complete",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "elapsed_ms": elapsed_ms,
                },
            )


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in {"/health", "/ready", "/metrics", "/metrics.json", "/safety"}:
            return await call_next(request)
        settings = get_settings()
        key = request.headers.get("authorization") or request.client.host if request.client else "anonymous"
        allowed = await self.allow_request(key, settings.rate_limit_requests, settings.rate_limit_window_seconds)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"retry-after": str(settings.rate_limit_window_seconds)},
            )
        return await call_next(request)

    async def allow_request(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self.requests[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class DistributedRateLimitMiddleware(InMemoryRateLimitMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis: Redis | None = None

    async def allow_request(self, key: str, limit: int, window_seconds: int) -> bool:
        settings = get_settings()
        if settings.rate_limit_backend.lower() != "redis":
            return await super().allow_request(key, limit, window_seconds)
        try:
            if self.redis is None:
                self.redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            redis_key = f"kbm:rate:{key}"
            count = await self.redis.incr(redis_key)
            if count == 1:
                await self.redis.expire(redis_key, window_seconds)
            return count <= limit
        except Exception:
            logger.warning("redis rate limiter unavailable; falling back to memory", exc_info=True)
            return await super().allow_request(key, limit, window_seconds)
