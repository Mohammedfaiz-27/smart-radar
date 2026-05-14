"""
Database connection - Supabase (PostgreSQL via asyncpg)
"""
import os
import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def connect_to_mongo():
    """Connect to Supabase PostgreSQL (name kept for compatibility)."""
    global _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    _pool = await asyncpg.create_pool(
        url,
        min_size=3,
        max_size=25,
        command_timeout=60,
        ssl="require",
        statement_cache_size=0,  # required for Supabase pooler (PgBouncer/Supavisor)
    )
    logger.info("✅ Connected to Supabase PostgreSQL")


async def close_mongo_connection():
    """Close the connection pool (name kept for compatibility)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
    logger.info("✅ Supabase PostgreSQL connection closed")


def get_database():
    """Return the asyncpg pool. Services call pool methods directly."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised — startup not complete")
    return _pool


async def get_pool() -> asyncpg.Pool:
    return get_database()
