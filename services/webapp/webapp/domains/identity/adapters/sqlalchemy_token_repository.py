"""SQLAlchemy async adapter for TokenRepository."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.domains.identity.models.domain.password_reset_token import PasswordResetToken
from webapp.domains.identity.models.domain.types import PasswordResetTokenId, UserId
from webapp.domains.identity.models.persistence.password_reset_token_record import (
    PasswordResetTokenRecord,
)


@dataclass
class SQLAlchemyTokenRepository:
    _session: AsyncSession

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetTokenRecord).where(
                PasswordResetTokenRecord.token_hash == token_hash
            )
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def save(self, token: PasswordResetToken) -> None:
        stmt = insert(PasswordResetTokenRecord).values(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_used(self, token_id: PasswordResetTokenId, used_at: datetime) -> None:
        await self._session.execute(
            update(PasswordResetTokenRecord)
            .where(PasswordResetTokenRecord.id == token_id)
            .values(used_at=used_at)
        )
        await self._session.flush()

    async def delete_by_user_id(self, user_id: UserId) -> None:
        await self._session.execute(
            delete(PasswordResetTokenRecord).where(
                PasswordResetTokenRecord.user_id == user_id
            )
        )
        await self._session.flush()


def _to_domain(record: PasswordResetTokenRecord) -> PasswordResetToken:
    return PasswordResetToken(
        id=PasswordResetTokenId(record.id),
        user_id=UserId(record.user_id),
        token_hash=record.token_hash,
        expires_at=record.expires_at,
        used_at=record.used_at,
    )
