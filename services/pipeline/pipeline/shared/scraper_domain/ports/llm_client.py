"""LLMClient port — protocol for LLM-based product data extraction."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.shared.scraper_domain.models.domain.llm_extraction_result import (
    LLMExtractionResult,
)


@runtime_checkable
class LLMClient(Protocol):
    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult: ...
