import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base

target_metadata = Base.metadata


def offline():
    context.configure(url=get_settings().database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(get_settings().database_url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    offline()
else:
    asyncio.run(online())
