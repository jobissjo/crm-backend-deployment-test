import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import User
from app.schemas import Login, Register, UserOut

Session = Annotated[AsyncSession, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)
passwords = PasswordHash.recommended()
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def current_user(session: Session, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    unauthorized = HTTPException(401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        claims = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]})
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized
    user = await session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: Register, session: Session):
    user = User(email=str(body.email).lower(), name=body.name, password_hash=await asyncio.to_thread(passwords.hash, body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Email already registered")
    await session.refresh(user)
    return user


@router.post("/login")
async def login(body: Login, session: Session):
    user = await session.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None or not await asyncio.to_thread(passwords.verify, body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=get_settings().access_token_minutes)}, get_settings().jwt_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
