import unittest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        hashed = hash_password("correct horse battery staple")

        self.assertTrue(verify_password("correct horse battery staple", hashed))
        self.assertFalse(verify_password("wrong password", hashed))

    def test_jwt_round_trip(self):
        token = create_access_token("user-123", {"scope": "test"})

        payload = decode_access_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "user-123")
        self.assertEqual(payload["scope"], "test")

    def test_invalid_jwt_returns_none(self):
        self.assertIsNone(decode_access_token("not-a-token"))


if __name__ == "__main__":
    unittest.main()
