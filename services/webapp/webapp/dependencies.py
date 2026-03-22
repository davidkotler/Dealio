"""FastAPI shared dependency providers."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.config import Settings
from webapp.config import get_settings as _get_settings
from webapp.domains.identity.adapters.jwt_service import decode_jwt
from webapp.domains.identity.adapters.sqlalchemy_user_repository import SQLAlchemyUserRepository
from webapp.domains.identity.models.domain.user import User


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_settings() -> Settings:
    return _get_settings()


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    session_cookie: str | None = Cookie(default=None, alias="session"),
    settings: Settings = Depends(get_settings),
) -> User:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    try:
        user_id = decode_jwt(session_cookie, settings.jwt_secret)
    except JWTError:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    user = await SQLAlchemyUserRepository(session).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    return user
