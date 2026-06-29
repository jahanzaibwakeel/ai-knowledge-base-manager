from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import now_utc
from app.repositories.base import MongoRepository, serialize


class UserRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.users)

    async def get_by_email(self, email: str) -> dict | None:
        return serialize(await self.collection.find_one({"email": email.lower()}))

    async def set_password(self, user_id: str, password_hash: str) -> dict | None:
        return await self.update(user_id, {"password_hash": password_hash})


class PasswordResetTokenRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.password_reset_tokens)

    async def create_for_user(self, user_id: str, token_hash: str, expires_at) -> dict:
        await self.collection.update_many({"user_id": user_id, "used_at": None}, {"$set": {"used_at": now_utc()}})
        return await self.create({"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at, "used_at": None})

    async def get_active(self, token_hash: str, now) -> dict | None:
        return serialize(
            await self.collection.find_one(
                {"token_hash": token_hash, "used_at": None, "expires_at": {"$gt": now}}
            )
        )

    async def mark_used(self, token_id: str) -> dict | None:
        return await self.update(token_id, {"used_at": now_utc()})
