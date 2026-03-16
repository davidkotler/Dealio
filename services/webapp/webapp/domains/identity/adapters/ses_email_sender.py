"""AWS SES adapter for EmailSender."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial
from typing import Any


@dataclass
class SESEmailSender:
    """EmailSender backed by AWS SES.

    The boto3 ``send_email`` call is synchronous; it is dispatched to a thread pool
    executor to avoid blocking the event loop.
    """

    _client: Any  # boto3 SES client
    _from_address: str

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        loop = asyncio.get_event_loop()
        send = partial(
            self._client.send_email,
            Source=self._from_address,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": "Reset your Dealio password"},
                "Body": {
                    "Text": {"Data": f"Reset link: {reset_link}"},
                    "Html": {"Data": f'<a href="{reset_link}">Reset password</a>'},
                },
            },
        )
        await loop.run_in_executor(None, send)
