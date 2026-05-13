"""
Cleanup Service for Temporary Files and Old Generated Content

Handles automatic cleanup of:
- Old screenshots in static/screenshots/
- Old generated newscards in static/generated-newscards/
- Orphaned temporary files in /tmp
- Expired cache files
"""

import os
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up temporary and old generated files"""

    def __init__(self):
        """Initialize cleanup service with default paths"""
        self.base_dir = Path(__file__).parent.parent
        self.screenshots_dir = self.base_dir / "static" / "screenshots"
        self.newscards_dir = self.base_dir / "static" / "generated-newscards"
        self.temp_dir = Path(tempfile.gettempdir())

        # Default retention periods (in days)
        self.screenshot_retention_days = 30
        self.newscard_retention_days = 30
        self.temp_file_retention_hours = 24

        logger.info("Cleanup service initialized")

    def cleanup_old_screenshots(self, max_age_days: int = None) -> Dict[str, int]:
        """
        Clean up old screenshot files

        Args:
            max_age_days: Maximum age in days (default: 30)

        Returns:
            Dict with cleanup statistics
        """
        if max_age_days is None:
            max_age_days = self.screenshot_retention_days

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        if not self.screenshots_dir.exists():
            logger.info("Screenshots directory does not exist, skipping cleanup")
            return {"deleted": 0, "errors": 0, "bytes_freed": 0}

        deleted_count = 0
        error_count = 0
        bytes_freed = 0

        try:
            for screenshot_file in self.screenshots_dir.glob("screenshot_*.png"):
                try:
                    # Check file modification time
                    file_stat = screenshot_file.stat()
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                    if file_mtime < cutoff_date:
                        file_size = file_stat.st_size
                        screenshot_file.unlink()
                        deleted_count += 1
                        bytes_freed += file_size
                        logger.debug(f"Deleted old screenshot: {screenshot_file.name}")

                except Exception as e:
                    logger.error(f"Error deleting screenshot {screenshot_file}: {e}")
                    error_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old screenshots "
                    f"({bytes_freed / 1024 / 1024:.2f} MB freed)"
                )

        except Exception as e:
            logger.error(f"Error during screenshot cleanup: {e}")
            error_count += 1

        return {
            "deleted": deleted_count,
            "errors": error_count,
            "bytes_freed": bytes_freed
        }

    def cleanup_old_newscards(self, max_age_days: int = None) -> Dict[str, int]:
        """
        Clean up old newscard files using the newscard storage service

        Args:
            max_age_days: Maximum age in days (default: 30)

        Returns:
            Dict with cleanup statistics
        """
        if max_age_days is None:
            max_age_days = self.newscard_retention_days

        try:
            from services.newscard_storage_service import newscard_storage_service

            # Get stats before cleanup
            stats_before = newscard_storage_service.get_storage_stats()
            files_before = stats_before.get('total_files', 0)

            # Run cleanup
            newscard_storage_service.cleanup_old_newscards(max_age_days)

            # Get stats after cleanup
            stats_after = newscard_storage_service.get_storage_stats()
            files_after = stats_after.get('total_files', 0)

            deleted_count = files_before - files_after

            return {
                "deleted": deleted_count,
                "errors": 0,
                "bytes_freed": 0  # newscard service doesn't track this yet
            }

        except Exception as e:
            logger.error(f"Error during newscard cleanup: {e}")
            return {"deleted": 0, "errors": 1, "bytes_freed": 0}

    def cleanup_orphaned_temp_files(self, max_age_hours: int = None) -> Dict[str, int]:
        """
        Clean up orphaned temporary files in /tmp directory

        Removes temp files created by this application that are older than max_age_hours

        Args:
            max_age_hours: Maximum age in hours (default: 24)

        Returns:
            Dict with cleanup statistics
        """
        if max_age_hours is None:
            max_age_hours = self.temp_file_retention_hours

        cutoff_date = datetime.now() - timedelta(hours=max_age_hours)

        deleted_count = 0
        error_count = 0
        bytes_freed = 0

        # Patterns for temp files created by this application
        temp_patterns = [
            "tmp*.html",
            "tmp*.png",
            "*newscard*.html",
            "*newscard*.png",
            "screenshot_*.png",
            "*_original_*"  # Video conversion temp files
        ]

        try:
            for pattern in temp_patterns:
                for temp_file in self.temp_dir.glob(pattern):
                    try:
                        # Only delete files, not directories
                        if not temp_file.is_file():
                            continue

                        # Check file modification time
                        file_stat = temp_file.stat()
                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                        if file_mtime < cutoff_date:
                            file_size = file_stat.st_size
                            temp_file.unlink()
                            deleted_count += 1
                            bytes_freed += file_size
                            logger.debug(f"Deleted orphaned temp file: {temp_file.name}")

                    except Exception as e:
                        logger.error(f"Error deleting temp file {temp_file}: {e}")
                        error_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} orphaned temp files "
                    f"({bytes_freed / 1024 / 1024:.2f} MB freed)"
                )

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            error_count += 1

        return {
            "deleted": deleted_count,
            "errors": error_count,
            "bytes_freed": bytes_freed
        }

    def cleanup_all(self) -> Dict[str, Dict[str, int]]:
        """
        Run all cleanup tasks

        Returns:
            Dict with results from all cleanup tasks
        """
        logger.info("Starting comprehensive cleanup...")

        results = {
            "screenshots": self.cleanup_old_screenshots(),
            "newscards": self.cleanup_old_newscards(),
            "temp_files": self.cleanup_orphaned_temp_files()
        }

        # Calculate totals
        total_deleted = sum(r["deleted"] for r in results.values())
        total_errors = sum(r["errors"] for r in results.values())
        total_bytes = sum(r["bytes_freed"] for r in results.values())

        logger.info(
            f"Cleanup completed: {total_deleted} files deleted, "
            f"{total_bytes / 1024 / 1024:.2f} MB freed, "
            f"{total_errors} errors"
        )

        results["totals"] = {
            "deleted": total_deleted,
            "errors": total_errors,
            "bytes_freed": total_bytes
        }

        return results

    def get_cleanup_stats(self) -> Dict:
        """
        Get statistics about cleanable files

        Returns:
            Dict with counts and sizes of cleanable files
        """
        stats = {
            "screenshots": self._get_file_stats(
                self.screenshots_dir,
                "screenshot_*.png",
                self.screenshot_retention_days
            ),
            "temp_files": self._get_temp_file_stats(),
        }

        return stats

    def _get_file_stats(self, directory: Path, pattern: str, max_age_days: int) -> Dict:
        """Get statistics for files matching pattern in directory"""
        if not directory.exists():
            return {"count": 0, "size": 0, "old_count": 0, "old_size": 0}

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        total_count = 0
        total_size = 0
        old_count = 0
        old_size = 0

        try:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_stat = file_path.stat()
                    total_count += 1
                    total_size += file_stat.st_size

                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                    if file_mtime < cutoff_date:
                        old_count += 1
                        old_size += file_stat.st_size

        except Exception as e:
            logger.error(f"Error getting file stats: {e}")

        return {
            "count": total_count,
            "size": total_size,
            "old_count": old_count,
            "old_size": old_size,
            "retention_days": max_age_days
        }

    def _get_temp_file_stats(self) -> Dict:
        """Get statistics for temporary files"""
        cutoff_date = datetime.now() - timedelta(hours=self.temp_file_retention_hours)

        total_count = 0
        total_size = 0
        old_count = 0
        old_size = 0

        temp_patterns = [
            "tmp*.html",
            "tmp*.png",
            "*newscard*.html",
            "*newscard*.png",
            "screenshot_*.png",
            "*_original_*"
        ]

        try:
            for pattern in temp_patterns:
                for file_path in self.temp_dir.glob(pattern):
                    if file_path.is_file():
                        file_stat = file_path.stat()
                        total_count += 1
                        total_size += file_stat.st_size

                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        if file_mtime < cutoff_date:
                            old_count += 1
                            old_size += file_stat.st_size

        except Exception as e:
            logger.error(f"Error getting temp file stats: {e}")

        return {
            "count": total_count,
            "size": total_size,
            "old_count": old_count,
            "old_size": old_size,
            "retention_hours": self.temp_file_retention_hours
        }


# Global cleanup service instance
cleanup_service = CleanupService()
