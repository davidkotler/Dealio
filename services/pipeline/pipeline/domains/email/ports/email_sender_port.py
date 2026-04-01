"""Email sender port."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domains.email.models.domain.email_alert_payload import EmailAlertPayload


@runtime_checkable
class EmailSenderPort(Protocol):
    async def send_price_drop_alert(self, payload: EmailAlertPayload) -> None: ...
