"""SES email sender adapter."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from pipeline.domains.email.exceptions import EmailDeliveryError
from pipeline.domains.email.models.domain.email_alert_payload import EmailAlertPayload


@dataclass
class SESEmailSenderAdapter:
    _from_address: str
    _region: str

    async def send_price_drop_alert(self, payload: EmailAlertPayload) -> None:
        client = boto3.client("ses", region_name=self._region)
        try:
            await asyncio.to_thread(
                client.send_email,
                Source=self._from_address,
                Destination={"ToAddresses": [payload.to_email]},
                Message={
                    "Subject": {"Data": f"Price drop on {payload.product_name}"},
                    "Body": {
                        "Text": {
                            "Data": (
                                f"Good news! {payload.product_name} dropped from "
                                f"{payload.old_price} to {payload.new_price}.\n"
                                f"View it here: {payload.product_url}"
                            )
                        }
                    },
                },
            )
        except ClientError as exc:
            raise EmailDeliveryError(f"SES send failed: {exc}") from exc
