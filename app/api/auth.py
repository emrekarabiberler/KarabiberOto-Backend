from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

users = {}


class AuthRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


@router.post("/login")
async def login(request: AuthRequest):
    user = users.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "status": "success",
        "token": str(uuid4()),
        "user": {"email": request.email, "name": user["name"]},
    }


@router.post("/register")
async def register(request: AuthRequest):
    if request.email in users:
        raise HTTPException(status_code=409, detail="User already exists")

    users[request.email] = {
        "password": request.password,
        "name": request.name or request.email.split("@")[0],
    }

    return {
        "status": "success",
        "token": str(uuid4()),
        "user": {"email": request.email, "name": users[request.email]["name"]},
    }
