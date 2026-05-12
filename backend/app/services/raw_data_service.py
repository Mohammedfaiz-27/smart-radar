"""
Raw data service - stubbed for Supabase migration.
Raw API responses are no longer stored; pipeline saves directly to posts_table.
"""
from typing import List, Optional
from app.models.raw_data import (
    RawDataCreate, RawDataUpdate, RawDataResponse,
    RawDataQueryParams, RawDataStats, ProcessingStatus
)


class RawDataService:
    def __init__(self):
        pass

    async def initialize(self):
        pass

    async def create(self, entry: RawDataCreate) -> RawDataResponse:
        return None

    async def bulk_create(self, entries: List[RawDataCreate]) -> List[RawDataResponse]:
        return []

    async def update(self, entry_id: str, update: RawDataUpdate) -> Optional[RawDataResponse]:
        return None

    async def get(self, entry_id: str) -> Optional[RawDataResponse]:
        return None

    async def query(self, params: RawDataQueryParams) -> List[RawDataResponse]:
        return []

    async def get_stats(self) -> RawDataStats:
        return RawDataStats(
            total_records=0,
            records_by_platform={},
            records_by_status={},
            total_posts_extracted=0
        )

    async def get_pending(self, limit: int = 100) -> List[RawDataResponse]:
        return []

    async def mark_completed(self, entry_id: str, posts_extracted: int = 0):
        pass

    async def mark_failed(self, entry_id: str, error: str = ""):
        pass
