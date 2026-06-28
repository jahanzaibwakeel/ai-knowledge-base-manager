import os
import unittest

from fastapi import HTTPException

from app.api.routes.documents import validate_document_content_size
from app.core.config import get_settings


class IngestionLimitTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("MAX_DOCUMENT_CHARS", None)
        get_settings.cache_clear()

    def test_validate_document_content_size_allows_content_under_limit(self):
        os.environ["MAX_DOCUMENT_CHARS"] = "20"
        get_settings.cache_clear()

        validate_document_content_size("short content")

    def test_validate_document_content_size_rejects_content_over_limit(self):
        os.environ["MAX_DOCUMENT_CHARS"] = "5"
        get_settings.cache_clear()

        with self.assertRaises(HTTPException) as context:
            validate_document_content_size("too long")

        self.assertEqual(context.exception.status_code, 413)
        self.assertIn("5 character limit", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
