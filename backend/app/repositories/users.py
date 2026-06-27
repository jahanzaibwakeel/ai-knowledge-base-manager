from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import MongoRepository, serialize


class UserRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.users)

    async def get_by_email(self, email: str) -> dict | None:
        return serialize(await self.collection.find_one({"email": email.lower()}))
