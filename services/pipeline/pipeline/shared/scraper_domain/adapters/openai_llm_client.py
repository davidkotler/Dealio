"""OpenAI adapter for LLM-based product data extraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from pipeline.shared.scraper_domain.exceptions import LLMExtractionError
from pipeline.shared.scraper_domain.models.domain.llm_extraction_result import (
    LLMExtractionResult,
)

_SYSTEM_PROMPT = (
    "Extract product price and name from HTML. "
    'Return ONLY valid JSON: {"price": "29.99 or null", "product_name": "string or null"}. '
    "Rules: primary current price only, no currency symbols, null if not found."
)

_TIMEOUT = 30.0


class _LLMResponse(BaseModel):
    price: str | None = None
    product_name: str | None = None


@dataclass
class OpenAILLMClient:
    _api_key: str
    _model: str = field(default="gpt-4o-mini")

    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key, timeout=_TIMEOUT)
            response = await client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": cleaned_html},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMExtractionError(f"OpenAI request failed: {exc}") from exc

        content = response.choices[0].message.content or ""
        return _parse_response(content)


def _parse_response(content: str) -> LLMExtractionResult:
    import json

    try:
        data = json.loads(content)
        parsed = _LLMResponse.model_validate(data)
    except Exception:
        return LLMExtractionResult(price=None, product_name=None)

    price: Decimal | None = None
    if parsed.price is not None:
        try:
            price = Decimal(parsed.price.strip())
            if price <= 0:
                price = None
        except (InvalidOperation, ValueError, AttributeError):
            price = None

    return LLMExtractionResult(price=price, product_name=parsed.product_name)
