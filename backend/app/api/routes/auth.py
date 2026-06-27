from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> TokenResponse:
    users = UserRepository(db)
    if await users.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = await users.create(
        {"email": payload.email.lower(), "name": payload.name, "password_hash": hash_password(payload.password)}
    )
    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user=public_user(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> TokenResponse:
    user = await UserRepository(db).get_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user["id"]), user=public_user(user))


@router.get("/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return public_user(user)
