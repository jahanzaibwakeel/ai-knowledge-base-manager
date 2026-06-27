from app.repositories.domain import ActivityRepository


class ActivityService:
    def __init__(self, activities: ActivityRepository):
        self.activities = activities

    async def record(
        self,
        workspace_id: str,
        actor_id: str,
        action: str,
        entity_type: str,
        message: str,
        entity_id: str | None = None,
    ) -> dict:
        return await self.activities.create(
            {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "message": message,
            }
        )
