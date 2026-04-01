from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from pipeline.domains.scraper.models.domain.price_drop_message import PriceDropMessage


class PriceDropSNSMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    tracked_product_id: Annotated[str, Field(description="UUID of the tracked product")]
    user_id: Annotated[str, Field(description="UUID of the user who owns the tracked product")]
    user_email: Annotated[str, Field(description="Email address of the user")]
    product_name: Annotated[str, Field(description="Name of the product")]
    product_url: Annotated[str, Field(description="URL of the product page")]
    old_price: Annotated[str, Field(description="Previous price as a decimal string")]
    new_price: Annotated[str, Field(description="New (lower) price as a decimal string")]
    correlation_id: Annotated[str, Field(description="Correlation ID for tracing")]

    @classmethod
    def from_domain(cls, msg: PriceDropMessage) -> PriceDropSNSMessage:
        return cls(
            tracked_product_id=str(msg.tracked_product_id),
            user_id=str(msg.user_id),
            user_email=msg.user_email,
            product_name=msg.product_name,
            product_url=msg.product_url,
            old_price=str(msg.old_price),
            new_price=str(msg.new_price),
            correlation_id=str(msg.correlation_id),
        )
