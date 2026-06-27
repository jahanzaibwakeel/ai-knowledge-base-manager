import unittest

from app.core.config import get_settings
from app.core.middleware import InMemoryRateLimitMiddleware


class MiddlewareTests(unittest.TestCase):
    def test_rate_limit_middleware_uses_configured_settings(self):
        settings = get_settings()
        self.assertGreater(settings.rate_limit_requests, 0)
        self.assertGreater(settings.rate_limit_window_seconds, 0)

    def test_rate_limit_middleware_can_be_constructed(self):
        middleware = InMemoryRateLimitMiddleware(lambda scope, receive, send: None)
        self.assertEqual(dict(middleware.requests), {})


if __name__ == "__main__":
    unittest.main()
