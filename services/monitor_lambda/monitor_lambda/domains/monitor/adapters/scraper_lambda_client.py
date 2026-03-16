from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import boto3

from monitor_lambda.domains.monitor.models.domain import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)

_RETRYABLE = {ScraperErrorType.TIMEOUT, ScraperErrorType.HTTP_ERROR}


class ScraperLambdaClient:
    def __init__(self, lambda_name: str, max_retries: int = 3) -> None:
        self._lambda_name = lambda_name
        self._max_retries = max_retries
        self._client = boto3.client("lambda")

    async def scrape(self, url: str) -> ScraperResult:
        attempt = 0
        last_result: ScraperFailure | None = None
        while attempt < self._max_retries:
            result = await self._invoke(url)
            if isinstance(result, ScraperSuccess):
                return result
            if result.error_type not in _RETRYABLE:
                return result
            last_result = result
            attempt += 1
            if attempt < self._max_retries:
                await asyncio.sleep(2 ** (attempt - 1))  # 1s, 2s
        return ScraperFailure(  # type: ignore[union-attr]
            error_type=last_result.error_type,
            message=last_result.message,
            status_code=last_result.status_code,
            retry_count=attempt,
        )

    async def _invoke(self, url: str) -> ScraperResult:
        try:
            response = await asyncio.to_thread(
                self._client.invoke,
                FunctionName=self._lambda_name,
                InvocationType="RequestResponse",
                Payload=json.dumps({"url": url}).encode(),
            )
            payload = json.loads(response["Payload"].read())
        except Exception as e:
            return ScraperFailure(
                error_type=ScraperErrorType.HTTP_ERROR,
                message=str(e),
                status_code=None,
            )
        if payload.get("status") == "success":
            return ScraperSuccess(
                price=Decimal(payload["price"]),
                product_name=payload["product_name"],
            )
        return ScraperFailure(
            error_type=ScraperErrorType(payload.get("error_type", "parse_error")),
            message=payload.get("message", "Unknown error"),
            status_code=payload.get("status_code"),
        )
