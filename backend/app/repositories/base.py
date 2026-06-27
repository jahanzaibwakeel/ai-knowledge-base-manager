from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.models.common import now_utc


def oid(value: str) -> ObjectId:
    return ObjectId(value)


def serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    for key, value in list(doc.items()):
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, list):
            doc[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    return doc


class MongoRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        timestamp = now_utc()
        payload = {**payload, "created_at": timestamp, "updated_at": timestamp}
        result = await self.collection.insert_one(payload)
        return serialize(await self.collection.find_one({"_id": result.inserted_id})) or {}

    async def get(self, entity_id: str) -> dict[str, Any] | None:
        return serialize(await self.collection.find_one({"_id": oid(entity_id)}))

    async def update(self, entity_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        payload = {key: value for key, value in payload.items() if value is not None}
        if not payload:
            return await self.get(entity_id)
        payload["updated_at"] = now_utc()
        await self.collection.update_one({"_id": oid(entity_id)}, {"$set": payload})
        return await self.get(entity_id)

    async def delete(self, entity_id: str) -> bool:
        result = await self.collection.delete_one({"_id": oid(entity_id)})
        return result.deleted_count == 1
