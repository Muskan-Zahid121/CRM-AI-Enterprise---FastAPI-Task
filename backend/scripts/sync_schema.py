"""Sync PostgreSQL columns with Tortoise model fields (dev helper)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tortoise import Tortoise

from app.config import settings
from app.database.schema_sync import sync_schema


async def main():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models.user", "app.models.crm", "app.models.ai"]},
    )
    await sync_schema()
    await Tortoise.close_connections()
    print("Schema sync complete.")


if __name__ == "__main__":
    asyncio.run(main())
