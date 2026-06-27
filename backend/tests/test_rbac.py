import unittest

from app.api.routes.documents import normalize_terms
from app.api.routes.workspaces import ROLE_LEVELS


class RBACTests(unittest.TestCase):
    def test_role_levels_order_permissions(self):
        self.assertGreater(ROLE_LEVELS["owner"], ROLE_LEVELS["editor"])
        self.assertGreater(ROLE_LEVELS["editor"], ROLE_LEVELS["viewer"])

    def test_normalize_terms_splits_commas_and_dedupes(self):
        self.assertEqual(normalize_terms(["alpha, beta", "beta", "  gamma "]), ["alpha", "beta", "gamma"])


if __name__ == "__main__":
    unittest.main()
