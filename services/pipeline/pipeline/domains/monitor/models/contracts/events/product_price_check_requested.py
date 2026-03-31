"""ProductPriceCheckRequested EventBridge event contract."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from pipeline.domains.monitor.models.domain.product_fan_out_payload import ProductFanOutPayload


class ProductPriceCheckRequestedDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    tracked_product_id: str
    url: str
    current_price: str  # Decimal as string
    user_id: str
    user_email: str  # PII — delivery only, NEVER logged
    product_name: str
    correlation_id: str

    @field_validator("current_price")
    @classmethod
    def validate_price_is_decimal(cls, v: str) -> str:
        Decimal(v)
        return v

    @classmethod
    def from_payload(cls, payload: ProductFanOutPayload) -> ProductPriceCheckRequestedDetail:
        return cls(
            tracked_product_id=str(payload.tracked_product_id),
            url=payload.url,
            current_price=str(payload.current_price),
            user_id=str(payload.user_id),
            user_email=payload.user_email,
            product_name=payload.product_name,
            correlation_id=str(payload.correlation_id),
        )
