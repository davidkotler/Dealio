"""SQLAlchemy async adapter for UserRepository."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.identity.models.domain.user import User
from webapp.domains.identity.models.persistence.user_record import UserRecord


@dataclass
class SQLAlchemyUserRepository:
    _session: AsyncSession

    async def get_by_id(self, user_id: UserId) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.email == email)
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def get_by_google_sub(self, sub: str) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.google_sub == sub)
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def save(self, user: User) -> None:
        values = _to_record(user)
        stmt = (
            insert(UserRecord)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "email": values["email"],
                    "password_hash": values["password_hash"],
                    "google_sub": values["google_sub"],
                    "updated_at": values["updated_at"],
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()


def _to_domain(record: UserRecord) -> User:
    return User(
        id=UserId(record.id),
        email=record.email,
        password_hash=HashedPassword(value=record.password_hash) if record.password_hash is not None else None,
        google_sub=record.google_sub,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_record(user: User) -> dict:  # type: ignore[type-arg]
    return {
        "id": user.id,
        "email": user.email,
        "password_hash": user.password_hash.value if user.password_hash is not None else None,
        "google_sub": user.google_sub,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
