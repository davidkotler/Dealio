from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://dealio:dealio@localhost:5433/dealio?ssl=disable",
        )
    )
    aws_region: str = field(
        default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1")
    )
    eventbridge_bus_name: str = field(
        default_factory=lambda: os.environ.get("EVENTBRIDGE_BUS_NAME", "dealio-pipeline")
    )
    sns_price_drop_topic_arn: str = field(
        default_factory=lambda: os.environ.get("SNS_PRICE_DROP_TOPIC_ARN", "")
    )
    ses_from_address: str = field(
        default_factory=lambda: os.environ.get("SES_FROM_ADDRESS", "")
    )
    llm_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "gemini")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.environ.get("LLM_API_KEY", "")
    )
    llm_model: str = field(
        default_factory=lambda: os.environ.get("LLM_MODEL", "gemini-2.5-flash")
    )
