#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Social Media Scraper Background Runner

A configurable background service that runs social media scraping jobs based on
user-defined schedules and keywords. This replaces the hardcoded demo_job.py
with a flexible, multi-tenant system.
"""

import asyncio
import os
import sys
import signal
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Configure beautiful logging BEFORE other imports
from core.logging_config import setup_logging, get_logger

setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/scraper_runner.log"),
    use_colors=os.getenv("LOG_COLORS", "true").lower() == "true",
    use_emojis=os.getenv("LOG_EMOJIS", "true").lower() == "true",
)

from core.database import SupabaseClient
from services.scraper_service import ScraperJobService
from core.config import settings

logger = get_logger(__name__)


class ScraperRunner:
    """Background runner for social media scraper jobs"""

    def __init__(self):
        self.running = False
        self.db_client = None
        self.scraper_service = None
        self.check_interval = 30  # Check for jobs every 30 seconds
        self.active_jobs: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize database connection and services"""
        try:
            # Initialize Supabase client wrapper
            if (
                not hasattr(settings, "supabase_url")
                or not settings.supabase_url
                or not settings.supabase_service_key
            ):
                raise Exception(
                    "Database configuration missing - SUPABASE_URL and SUPABASE_SERVICE_KEY are required"
                )

            self.db_client = SupabaseClient()
            self.scraper_service = ScraperJobService(self.db_client)

            logger.info("Scraper runner initialized successfully")

        except Exception as e:
            logger.exception(f"Failed to initialize scraper runner: {e}")
            raise

    async def start(self):
        """Start the background runner"""
        logger.info("🚀 Starting Social Media Scraper Runner")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  • Check interval: {self.check_interval} seconds")
        logger.info(f"  • Database: Connected")
        logger.info("=" * 60)

        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while self.running:
                await self._check_and_run_jobs()
                await asyncio.sleep(self.check_interval)

        except Exception as e:
            logger.exception(f"Scraper runner error: {e}")
            raise
        finally:
            await self._cleanup()

    async def stop(self):
        """Stop the background runner"""
        logger.info("🛑 Stopping scraper runner...")
        self.running = False

        # Cancel all active jobs
        for job_id, task in self.active_jobs.items():
            if not task.done():
                logger.info(f"Canceling active job: {job_id}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.active_jobs.clear()
        logger.info("✅ Scraper runner stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.stop())

    async def _check_and_run_jobs(self):
        """Check for jobs that are ready to run and execute them"""
        try:
            # Get all jobs that are ready to run (enabled and next_run_at <= now)
            ready_jobs = await self.scraper_service.get_jobs_ready_to_run()
            ready_job_ids = {str(job.id) for job in ready_jobs}

            # Cancel any running jobs that are no longer enabled
            jobs_to_cancel = []
            for job_id in list(self.active_jobs.keys()):
                if job_id not in ready_job_ids:
                    # Job is running but no longer enabled or not ready to run
                    # Check if it's actually disabled
                    try:
                        job_status = await self.scraper_service.get_job_status(job_id)
                        if job_status and not job_status.get('is_enabled'):
                            jobs_to_cancel.append(job_id)
                    except Exception as e:
                        logger.warning(f"Failed to check status for job {job_id}: {e}")

            # Cancel disabled jobs
            for job_id in jobs_to_cancel:
                if job_id in self.active_jobs:
                    task = self.active_jobs[job_id]
                    if not task.done():
                        logger.warning(f"🛑 Canceling disabled job: {job_id}")
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            logger.info(f"✅ Job {job_id} successfully canceled")
                    del self.active_jobs[job_id]

            if not ready_jobs:
                logger.debug("No jobs ready to run")
                return

            logger.info(f"Found {len(ready_jobs)} jobs ready to run")

            for job in ready_jobs:
                # Skip if job is already running
                if str(job.id) in self.active_jobs:
                    running_task = self.active_jobs[str(job.id)]
                    if not running_task.done():
                        logger.debug(f"Job {job.name} is already running, skipping")
                        continue
                    else:
                        # Clean up completed task
                        del self.active_jobs[str(job.id)]

                # Start the job
                logger.info(f"🚀 Starting job: {job.name} (ID: {job.id})")
                task = asyncio.create_task(
                    self._run_job_with_error_handling(job), name=f"scraper_job_{job.id}"
                )
                self.active_jobs[str(job.id)] = task

            # Clean up completed tasks
            await self._cleanup_completed_tasks()

        except Exception as e:
            logger.exception(f"Error checking for ready jobs: {e}")

    async def _run_job_with_error_handling(self, job):
        """Run a scraper job with comprehensive error handling"""
        try:
            logger.info(f"Executing scraper job: {job.name}")
            logger.info(f"  • Keywords: {', '.join(job.keywords)}")
            logger.info(f"  • Platforms: {', '.join(job.platforms)}")
            logger.info(f"  • Schedule: {job.schedule_cron}")

            start_time = datetime.now(timezone.utc)

            # Execute the job
            run_result = await self.scraper_service.execute_scraper_job(job)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Log results
            if run_result.status == "completed":
                logger.info(f"✅ Job completed: {job.name}")
                logger.info(f"  • Duration: {duration:.1f} seconds")
                logger.info(f"  • Posts found: {run_result.posts_found}")
                logger.info(f"  • Posts processed: {run_result.posts_processed}")
                logger.info(f"  • Posts approved: {run_result.posts_approved}")
                logger.info(f"  • Posts published: {run_result.posts_published}")
            else:
                logger.error(f"❌ Job failed: {job.name}")
                logger.error(f"  • Error: {run_result.error_message}")

        except Exception as e:
            logger.exception(f"Unhandled error in job {job.name}: {e}")
        finally:
            # Remove from active jobs when done
            if str(job.id) in self.active_jobs:
                del self.active_jobs[str(job.id)]

    async def _cleanup_completed_tasks(self):
        """Clean up completed tasks from active jobs tracking"""
        completed_jobs = []

        for job_id, task in self.active_jobs.items():
            if task.done():
                completed_jobs.append(job_id)

                # Log any exceptions from completed tasks
                try:
                    await task
                except Exception as e:
                    logger.exception(f"Task for job {job_id} completed with error: {e}")

        # Remove completed tasks
        for job_id in completed_jobs:
            del self.active_jobs[job_id]

    async def _cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")

        # Wait for all active jobs to complete or timeout
        if self.active_jobs:
            logger.info(f"Waiting for {len(self.active_jobs)} active jobs to complete...")

            try:
                # Wait up to 30 seconds for jobs to complete
                await asyncio.wait_for(
                    asyncio.gather(*self.active_jobs.values(), return_exceptions=True), timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some jobs did not complete within timeout, forcing shutdown")

                # Cancel remaining tasks
                for task in self.active_jobs.values():
                    if not task.done():
                        task.cancel()

        self.active_jobs.clear()
        logger.info("Cleanup completed")

    def get_status(self) -> Dict:
        """Get current status of the runner"""
        return {
            "running": self.running,
            "active_jobs": len(self.active_jobs),
            "active_job_ids": list(self.active_jobs.keys()),
            "check_interval": self.check_interval,
            "database_connected": self.db_client is not None,
        }

    def print_status(self):
        """Print current status"""
        status = self.get_status()

        print(f"\n{'=' * 60}")
        print("🔍 SOCIAL MEDIA SCRAPER RUNNER STATUS")
        print(f"{'=' * 60}")
        print(f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        print(f"Database: {'🟢 Connected' if status['database_connected'] else '🔴 Disconnected'}")
        print(f"Active Jobs: {status['active_jobs']}")

        if status["active_job_ids"]:
            print("Active Job IDs:")
            for job_id in status["active_job_ids"]:
                print(f"  • {job_id}")

        print(f"Check Interval: {status['check_interval']} seconds")
        print(f"{'=' * 60}")


class ScraperRunnerManager:
    """Manager for controlling the scraper runner"""

    def __init__(self):
        self.runner = ScraperRunner()

    async def start(self):
        """Start the runner"""
        try:
            await self.runner.initialize()
            await self.runner.start()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.exception(f"Runner failed: {e}")
            return 1

        return 0

    async def status(self):
        """Show runner status"""
        try:
            await self.runner.initialize()

            # Get and display some basic statistics
            jobs = await self.runner.scraper_service.list_jobs(
                # This would need a way to get all tenants or be run per tenant
                tenant_id="00000000-0000-0000-0000-000000000000",  # Placeholder
                page=1,
                size=100,
            )

            print(f"\n{'=' * 60}")
            print("📊 SCRAPER JOBS OVERVIEW")
            print(f"{'=' * 60}")
            print(f"Total Jobs: {jobs['total']}")

            enabled_jobs = [job for job in jobs["jobs"] if job.is_enabled]
            print(f"Enabled Jobs: {len(enabled_jobs)}")

            if enabled_jobs:
                print("\nEnabled Jobs:")
                for job in enabled_jobs[:10]:  # Show first 10
                    next_run = (
                        job.next_run_at.strftime("%Y-%m-%d %H:%M:%S")
                        if job.next_run_at
                        else "Not scheduled"
                    )
                    print(f"  • {job.name}")
                    print(f"    Keywords: {', '.join(job.keywords)}")
                    print(f"    Platforms: {', '.join(job.platforms)}")
                    print(f"    Next run: {next_run}")
                    print(f"    Success rate: {job.success_rate}%")
                    print()

            print(f"{'=' * 60}")

        except Exception as e:
            logger.exception(f"Failed to get status: {e}")
            return 1

        return 0


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Social Media Scraper Runner")
    parser.add_argument("command", choices=["start", "status"], help="Command to execute")
    parser.add_argument(
        "--check-interval", type=int, default=30, help="Job check interval in seconds (default: 30)"
    )

    args = parser.parse_args()

    manager = ScraperRunnerManager()

    if args.command == "start":
        if hasattr(args, "check_interval"):
            manager.runner.check_interval = args.check_interval

        logger.info("🚀 Starting Social Media Scraper Runner...")
        logger.info("⚠️ Press Ctrl+C to stop the runner")

        return await manager.start()

    elif args.command == "status":
        return await manager.status()

    return 0


async def debug():
    """Main entry point"""

    manager = ScraperRunnerManager()

    return await manager.start()


if __name__ == "__main__":
    exit(asyncio.run(debug()))
