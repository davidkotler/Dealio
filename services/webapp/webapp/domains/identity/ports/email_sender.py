from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailSender(Protocol):
    async def send_password_reset(self, to_email: str, reset_link: str) -> None: ...
