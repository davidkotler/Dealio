"""AWS SES adapter for EmailSender port."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from monitor_lambda.domains.monitor.exceptions import EmailDeliveryError


@dataclass
class SESEmailSender:
    _from_address: str
    _region: str = "us-east-1"
    _client: Any = field(init=False)

    def __post_init__(self) -> None:
        self._client = boto3.client("ses", region_name=self._region)

    async def send_price_drop_alert(
        self,
        to_email: str,
        product_name: str,
        product_url: str,
        old_price: Decimal,
        new_price: Decimal,
    ) -> None:
        subject = f"Price drop alert: {product_name}"
        body_text = (
            f"Good news! The price for {product_name} has dropped.\n"
            f"Old price: ${old_price}\n"
            f"New price: ${new_price}\n"
            f"View product: {product_url}"
        )
        body_html = (
            f"<p>Good news! The price for <strong>{product_name}</strong> has dropped.</p>"
            f"<p>Old price: <strong>${old_price}</strong> &rarr; New price: <strong>${new_price}</strong></p>"
            f"<p><a href='{product_url}'>View product</a></p>"
        )
        try:
            await asyncio.to_thread(
                self._client.send_email,
                Source=self._from_address,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text, "Charset": "UTF-8"},
                        "Html": {"Data": body_html, "Charset": "UTF-8"},
                    },
                },
            )
        except ClientError as exc:
            raise EmailDeliveryError(f"SES delivery failed for {to_email!r}: {exc}") from exc
