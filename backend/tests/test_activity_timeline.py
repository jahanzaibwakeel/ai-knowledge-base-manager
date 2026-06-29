import unittest

from app.repositories.domain import ActivityRepository


class FakeCursor:
    def __init__(self):
        self.sort_args = None
        self.skip_value = None
        self.limit_value = None
        self.rows = [
            {
                "_id": "activity-1",
                "workspace_id": "workspace-1",
                "actor_id": "user-1",
                "action": "created",
                "entity_type": "document",
                "message": "Created a document",
            }
        ]

    def sort(self, *args):
        self.sort_args = args
        return self

    def skip(self, value):
        self.skip_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    async def __aiter__(self):
        for row in self.rows:
            yield row


class FakeActivityCollection:
    def __init__(self):
        self.cursor = FakeCursor()
        self.query = None
        self.count_query = None

    def find(self, query):
        self.query = query
        return self.cursor

    async def count_documents(self, query):
        self.count_query = query
        return 1


class ActivityTimelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_activity_filters_stay_inside_accessible_workspaces(self):
        repo = ActivityRepository.__new__(ActivityRepository)
        repo.collection = FakeActivityCollection()

        items = await repo.list_for_workspaces(
            ["workspace-1"],
            workspace_id="workspace-1",
            action="created",
            entity_type="document",
            limit=10,
            skip=5,
        )
        total = await repo.count_for_workspaces(
            ["workspace-1"],
            workspace_id="workspace-1",
            action="created",
            entity_type="document",
        )

        expected = {"workspace_id": "workspace-1", "action": "created", "entity_type": "document"}
        self.assertEqual(repo.collection.query, expected)
        self.assertEqual(repo.collection.count_query, expected)
        self.assertEqual(repo.collection.cursor.sort_args, ("created_at", -1))
        self.assertEqual(repo.collection.cursor.skip_value, 5)
        self.assertEqual(repo.collection.cursor.limit_value, 10)
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["id"], "activity-1")

    async def test_activity_rejects_inaccessible_workspace_filter(self):
        repo = ActivityRepository.__new__(ActivityRepository)
        repo.collection = FakeActivityCollection()

        items = await repo.list_for_workspaces(["workspace-1"], workspace_id="workspace-2")
        total = await repo.count_for_workspaces(["workspace-1"], workspace_id="workspace-2")

        self.assertEqual(items, [])
        self.assertEqual(total, 0)
        self.assertIsNone(repo.collection.query)


if __name__ == "__main__":
    unittest.main()
