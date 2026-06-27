import unittest

from bson import ObjectId

from app.repositories.base import oid, serialize


class RepositoryBaseTests(unittest.TestCase):
    def test_oid_accepts_valid_object_id(self):
        value = ObjectId()

        self.assertEqual(oid(str(value)), value)

    def test_serialize_converts_object_ids_without_mutating_caller_copy_expectations(self):
        owner_id = ObjectId()
        tag_id = ObjectId()
        document = {"_id": ObjectId(), "owner_id": owner_id, "items": [tag_id, "plain"]}

        result = serialize(document.copy())

        self.assertIsNotNone(result)
        self.assertIn("id", result)
        self.assertEqual(result["owner_id"], str(owner_id))
        self.assertEqual(result["items"], [str(tag_id), "plain"])

    def test_serialize_handles_none(self):
        self.assertIsNone(serialize(None))


if __name__ == "__main__":
    unittest.main()
