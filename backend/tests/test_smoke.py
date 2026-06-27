import unittest


class SmokeTests(unittest.TestCase):
    def test_app_imports(self):
        from app.main import app

        self.assertEqual(app.title, "AI Knowledge Base Manager")


if __name__ == "__main__":
    unittest.main()
