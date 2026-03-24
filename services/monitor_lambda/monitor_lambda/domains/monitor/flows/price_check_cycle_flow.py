"""Orchestrates a full price-check cycle across all tracked products."""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from monitor_lambda.domains.monitor.exceptions import EmailDeliveryError, ProductCheckError
from monitor_lambda.domains.monitor.models.domain.notification import Notification
from monitor_lambda.domains.monitor.models.domain.price_check_log import PriceCheckLog
from monitor_lambda.domains.monitor.models.domain.price_check_result import PriceCheckResult
from monitor_lambda.domains.monitor.models.domain.scraper_result import ScraperFailure, ScraperSuccess
from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary
from monitor_lambda.domains.monitor.ports.email_sender import EmailSender
from monitor_lambda.domains.monitor.ports.notification_write_repository import NotificationWriteRepository
from monitor_lambda.domains.monitor.ports.price_check_log_repository import PriceCheckLogRepository
from monitor_lambda.domains.monitor.ports.scraper_port import ScraperPort
from monitor_lambda.domains.monitor.ports.tracked_product_repository import TrackedProductRepository

log = structlog.get_logger(__name__)

_MAX_CONCURRENCY = 10
_FAILURE_RATE_THRESHOLD = 0.05


@dataclass
class PriceCheckCycleFlow:
    product_repo: TrackedProductRepository
    price_check_log_repo: PriceCheckLogRepository
    notification_repo: NotificationWriteRepository
    scraper: ScraperPort
    email_sender: EmailSender

    async def run(self) -> None:
        products = await self.product_repo.list_all_active()
        print("products:")
        print(products)
        if not products:
            log.info("price_check_cycle.no_products")
            return

        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
        tasks = [self._check_product(semaphore, product) for product in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        failures = sum(1 for r in results if isinstance(r, Exception))
        successes = len(results) - failures

        log.info(
            "price_check_cycle.complete",
            total=len(products),
            successes=successes,
            failures=failures,
        )

        if failures / len(products) > _FAILURE_RATE_THRESHOLD:
            log.error(
                "price_check_cycle.high_failure_rate",
                failure_rate=round(failures / len(products), 3),
                failures=failures,
                total=len(products),
            )

    async def _check_product(
        self, semaphore: asyncio.Semaphore, product: TrackedProductSummary
    ) -> None:
        async with semaphore:
            try:
                await self._check_one(product)
            except Exception as exc:
                url_hash = hashlib.sha256(product.url.encode()).hexdigest()[:16]
                log.error(
                    "price_check.unhandled_error",
                    url_hash=url_hash,
                    user_id=str(product.user_id),
                    error=str(exc),
                )
                raise ProductCheckError(f"Failed to check product {url_hash}") from exc

    async def _check_one(self, product: TrackedProductSummary) -> None:
        url_hash = hashlib.sha256(product.url.encode()).hexdigest()[:16]
        now = datetime.now(tz=timezone.utc)
        result = await self.scraper.scrape(product.url)

        if isinstance(result, ScraperFailure):
            log.warning(
                "price_check.scraper_failure",
                url_hash=url_hash,
                user_id=str(product.user_id),
                error_type=result.error_type.value,
                retry_count=result.retry_count,
            )
            await self.price_check_log_repo.save(
                PriceCheckLog(
                    id=uuid.uuid4(),
                    tracked_product_id=product.id,
                    result=PriceCheckResult.failure(result.message),
                    checked_at=now,
                    retry_count=result.retry_count,
                )
            )
            return

        assert isinstance(result, ScraperSuccess)

        if result.price < product.current_price:
            await self.product_repo.update_prices(
                product_id=product.id,
                new_price=result.price,
                previous_price=product.current_price,
                last_checked_at=now,
            )
            await self.notification_repo.save(
                Notification(
                    id=uuid.uuid4(),
                    user_id=product.user_id,
                    tracked_product_id=product.id,
                    product_name=product.product_name,
                    product_url=product.url,
                    old_price=product.current_price,
                    new_price=result.price,
                    created_at=now,
                    read_at=None,
                )
            )
            try:
                await self.email_sender.send_price_drop_alert(
                    to_email=product.user_email,
                    product_name=product.product_name,
                    product_url=product.url,
                    old_price=product.current_price,
                    new_price=result.price,
                )
            except EmailDeliveryError as exc:
                log.warning(
                    "price_check.email_delivery_failed",
                    url_hash=url_hash,
                    user_id=str(product.user_id),
                    error=str(exc),
                )
            log.info(
                "price_check.price_drop_detected",
                url_hash=url_hash,
                user_id=str(product.user_id),
            )
        else:
            await self.product_repo.update_last_checked_at(
                product_id=product.id,
                last_checked_at=now,
            )

        await self.price_check_log_repo.save(
            PriceCheckLog(
                id=uuid.uuid4(),
                tracked_product_id=product.id,
                result=PriceCheckResult.success(),
                checked_at=now,
                retry_count=0,
            )
        )
