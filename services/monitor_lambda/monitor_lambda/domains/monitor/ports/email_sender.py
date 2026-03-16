from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailSender(Protocol):
    async def send_price_drop_alert(
        self,
        to_email: str,
        product_name: str,
        product_url: str,
        old_price: Decimal,
        new_price: Decimal,
    ) -> None: ...
