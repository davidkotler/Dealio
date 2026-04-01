"""Send alert flow."""
from __future__ import annotations

import structlog

from pipeline.domains.email.models.domain.email_alert_payload import EmailAlertPayload
from pipeline.domains.email.ports.email_sender_port import EmailSenderPort

log = structlog.get_logger()


async def send_alert_flow(
    *,
    payload: EmailAlertPayload,
    email_sender: EmailSenderPort,
) -> None:
    bound_log = log.bind(
        correlation_id=str(payload.correlation_id),
        user_id=str(payload.user_id),
        stage="email",
    )
    bound_log.info("email.alert.sending")
    await email_sender.send_price_drop_alert(payload)
    bound_log.info("email.alert.sent")
