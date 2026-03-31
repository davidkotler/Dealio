"""Gemini adapter for LLM-based product data extraction."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from pipeline.shared.scraper_domain.adapters.openai_llm_client import _LLMResponse
from pipeline.shared.scraper_domain.exceptions import LLMExtractionError
from pipeline.shared.scraper_domain.models.domain.llm_extraction_result import (
    LLMExtractionResult,
)

_SYSTEM_PROMPT = (
    "Extract product price and name from HTML. "
    'Return ONLY valid JSON: {"price": "29.99 or null", "product_name": "string or null"}. '
    "Rules: primary current price only, no currency symbols, null if not found."
)


@dataclass
class GeminiLLMClient:
    _api_key: str
    _model: str = field(default="gemini-2.5-flash")

    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult:
        try:
            content = await asyncio.to_thread(self._call_gemini, cleaned_html)
        except LLMExtractionError:
            raise
        except Exception as exc:
            raise LLMExtractionError(f"Gemini request failed: {exc}") from exc

        return _parse_response(content)

    def _call_gemini(self, cleaned_html: str) -> str:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model,
                contents=cleaned_html,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            return response.text or ""
        except Exception as exc:
            raise LLMExtractionError(f"Gemini request failed: {exc}") from exc


def _parse_response(content: str) -> LLMExtractionResult:
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
