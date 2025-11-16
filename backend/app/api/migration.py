"""
Migration API endpoints for data reprocessing
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from app.services.migration_service import MigrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/migration", tags=["migration"])

migration_service = MigrationService()


@router.get("/stats")
async def get_migration_stats() -> Dict[str, Any]:
    """Get migration statistics for all collections"""
    try:
        stats = await migration_service.get_migration_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting migration stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-for-migration")
async def mark_existing_data_for_migration() -> Dict[str, Any]:
    """Mark all existing data that needs migration"""
    try:
        result = await migration_service.mark_existing_data_for_migration()
        return {
            "status": "success",
            "message": "Data marked for migration successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error marking data for migration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-batch")
async def process_migration_batch(
    collection_name: str = Query(..., description="Collection to process: news_articles or social_posts"),
    batch_size: Optional[int] = Query(None, description="Batch size (defaults to service config)"),
    dry_run: bool = Query(False, description="Perform dry run without making changes")
) -> Dict[str, Any]:
    """Process a batch of documents for migration"""
    try:
        if collection_name not in ["news_articles", "social_posts"]:
            raise HTTPException(
                status_code=400, 
                detail="collection_name must be 'news_articles' or 'social_posts'"
            )
        
        result = await migration_service.process_migration_batch(
            collection_name=collection_name,
            batch_size=batch_size,
            dry_run=dry_run
        )
        
        return {
            "status": "success",
            "message": f"Batch processing completed for {collection_name}",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error processing migration batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-full-migration")
async def run_full_migration(
    collection_name: str = Query(..., description="Collection to migrate: news_articles or social_posts"),
    max_batches: Optional[int] = Query(None, description="Maximum number of batches to process")
) -> Dict[str, Any]:
    """Run full migration for a collection"""
    try:
        if collection_name not in ["news_articles", "social_posts"]:
            raise HTTPException(
                status_code=400, 
                detail="collection_name must be 'news_articles' or 'social_posts'"
            )
        
        result = await migration_service.run_full_migration(
            collection_name=collection_name,
            max_batches=max_batches
        )
        
        return {
            "status": "success",
            "message": f"Full migration completed for {collection_name}",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error running full migration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_migration_status() -> Dict[str, Any]:
    """Get current migration status and progress"""
    try:
        stats = await migration_service.get_migration_stats()
        
        # Calculate progress percentages
        news_progress = 0
        posts_progress = 0
        
        if stats["news_articles"]["total"] > 0:
            news_progress = (stats["news_articles"]["migrated"] / stats["news_articles"]["total"]) * 100
        
        if stats["social_posts"]["total"] > 0:
            posts_progress = (stats["social_posts"]["migrated"] / stats["social_posts"]["total"]) * 100
        
        overall_progress = 0
        if stats["totals"]["total"] > 0:
            overall_progress = (stats["totals"]["migrated"] / stats["totals"]["total"]) * 100
        
        return {
            "status": "success",
            "data": {
                "migration_statistics": stats,
                "progress": {
                    "news_articles_percent": round(news_progress, 2),
                    "social_posts_percent": round(posts_progress, 2),
                    "overall_percent": round(overall_progress, 2)
                },
                "is_complete": stats["totals"]["pending"] == 0,
                "total_remaining": stats["totals"]["pending"]
            }
        }
    except Exception as e:
        logger.error(f"Error getting migration status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))