import unittest

from app.core.config import get_settings
from app.core.middleware import DistributedRateLimitMiddleware, InMemoryRateLimitMiddleware


class MiddlewareTests(unittest.TestCase):
    def test_rate_limit_middleware_uses_configured_settings(self):
        settings = get_settings()
        self.assertGreater(settings.rate_limit_requests, 0)
        self.assertGreater(settings.rate_limit_window_seconds, 0)

    def test_rate_limit_middleware_can_be_constructed(self):
        middleware = InMemoryRateLimitMiddleware(lambda scope, receive, send: None)
        self.assertEqual(dict(middleware.requests), {})

    def test_distributed_rate_limit_middleware_can_be_constructed(self):
        middleware = DistributedRateLimitMiddleware(lambda scope, receive, send: None)
        self.assertIsNone(middleware.redis)


class RateLimitBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_rate_limiter_blocks_after_limit(self):
        middleware = InMemoryRateLimitMiddleware(lambda scope, receive, send: None)

        self.assertTrue(await middleware.allow_request("user-1", limit=2, window_seconds=60))
        self.assertTrue(await middleware.allow_request("user-1", limit=2, window_seconds=60))
        self.assertFalse(await middleware.allow_request("user-1", limit=2, window_seconds=60))


if __name__ == "__main__":
    unittest.main()
