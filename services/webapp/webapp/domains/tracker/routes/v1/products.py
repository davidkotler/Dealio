"""Tracker product routes — v1."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.config import Settings
from webapp.dependencies import get_current_user, get_db_session, get_settings
from webapp.domains.scraper_client.adapters.scraper_lambda_client import ScraperLambdaClient
from webapp.domains.tracker.adapters.sqlalchemy_notification_read_repository import (
    SQLAlchemyNotificationReadRepository,
)
from webapp.domains.tracker.adapters.sqlalchemy_tracked_product_repository import (
    SQLAlchemyTrackedProductRepository,
)
from webapp.domains.tracker.flows.add_tracked_product import AddTrackedProduct
from webapp.domains.tracker.flows.get_dashboard import GetDashboard
from webapp.domains.tracker.flows.remove_tracked_product import RemoveTrackedProduct
from webapp.domains.tracker.models.contracts.api.products import (
    AddProductRequest,
    DashboardResponse,
    ProductResponse,
)
from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct
from webapp.domains.tracker.models.domain.types import TrackedProductId
from webapp.domains.identity.models.domain.user import User

router = APIRouter(tags=["products"])


def _to_product_response(p: TrackedProduct) -> ProductResponse:
    return ProductResponse(
        id=str(p.id),
        url=p.url.value,
        product_name=p.product_name,
        current_price=str(p.current_price.value),
        previous_price=str(p.previous_price.value) if p.previous_price is not None else None,
        last_checked_at=p.last_checked_at,
        created_at=p.created_at,
    )


@router.get("/products", status_code=200, response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    data = await GetDashboard(
        product_repo=SQLAlchemyTrackedProductRepository(session),
        notification_read_repo=SQLAlchemyNotificationReadRepository(session),
    ).execute(current_user.id)
    return DashboardResponse(
        products=[_to_product_response(p) for p in data.products],
        unread_notification_count=data.unread_notification_count,
    )


@router.post("/products", status_code=201, response_model=ProductResponse)
async def add_product(
    body: AddProductRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    product = await AddTrackedProduct(
        product_repo=SQLAlchemyTrackedProductRepository(session),
        scraper=ScraperLambdaClient(lambda_name=settings.scraper_lambda_name),
    ).execute(current_user.id, body.url)
    return _to_product_response(product)


@router.delete("/products/{product_id}", status_code=204)
async def remove_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await RemoveTrackedProduct(
        product_repo=SQLAlchemyTrackedProductRepository(session),
    ).execute(TrackedProductId(product_id), current_user.id)
