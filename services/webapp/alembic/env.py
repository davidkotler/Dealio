"""Alembic environment configuration for async SQLAlchemy with asyncpg."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from webapp.config import get_settings

config = context.config
settings = get_settings()

# Override sqlalchemy.url from Settings so secrets are never stored in alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all webapp ORM models so Alembic detects them for autogenerate
from webapp.infrastructure.database.base import WebappBase
import webapp.domains.identity.models.persistence.user_record  # noqa: F401
import webapp.domains.identity.models.persistence.password_reset_token_record  # noqa: F401
import webapp.domains.tracker.models.persistence.tracked_product_record  # noqa: F401
import webapp.domains.notifier.models.persistence.notification_record  # noqa: F401

target_metadata = WebappBase.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection (SQL script mode)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live database using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
