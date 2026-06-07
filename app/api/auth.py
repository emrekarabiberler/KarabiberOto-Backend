import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.database import get_database

router = APIRouter()

bearer_scheme = HTTPBearer(auto_error=False)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-coolify")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
PASSWORD_HASH_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "210000"))


class AuthRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class AdminUserResponse(UserResponse):
    created_at: Optional[datetime] = None


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
        raise HTTPException(status_code=422, detail="Invalid email address")
    return normalized


def serialize_user(user) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
    )


def serialize_admin_user(user) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        created_at=user.get("created_at"),
    )


def create_access_token(user) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(actual_digest, expected_digest)
    except (AttributeError, ValueError):
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_database),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization token is required")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.post("/register")
async def register(request: AuthRequest, db=Depends(get_database)):
    email = normalize_email(request.email)
    existing_user = await db["users"].find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")

    user_document = {
        "email": email,
        "name": request.name or email.split("@")[0],
        "password_hash": hash_password(request.password),
        "created_at": datetime.now(timezone.utc),
    }

    result = await db["users"].insert_one(user_document)
    user_document["_id"] = result.inserted_id

    return {
        "status": "success",
        "token": create_access_token(user_document),
        "user": serialize_user(user_document).model_dump(),
    }


@router.post("/login")
async def login(request: AuthRequest, db=Depends(get_database)):
    email = normalize_email(request.email)
    user = await db["users"].find_one({"email": email})

    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "status": "success",
        "token": create_access_token(user),
        "user": serialize_user(user).model_dump(),
    }


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return serialize_user(current_user)


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db=Depends(get_database)):
    users = await db["users"].find().to_list(500)
    return [serialize_admin_user(user) for user in users]
