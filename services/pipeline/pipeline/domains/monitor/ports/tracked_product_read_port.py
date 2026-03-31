"""Port for reading tracked products for the fan-out cycle."""
from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from pipeline.domains.monitor.models.domain.product_fan_out_payload import ProductFanOutPayload


@runtime_checkable
class TrackedProductReadPort(Protocol):
    async def list_all_for_fan_out(self, *, correlation_id: uuid.UUID) -> list[ProductFanOutPayload]: ...
