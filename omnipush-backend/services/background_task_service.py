#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Task Service for OmniPush Platform

Handles background processing of posts including newscard generation,
content adaptation, and publishing without blocking the API response.
Uses asyncio for task management with status tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from uuid import uuid4, UUID
from concurrent.futures import ThreadPoolExecutor

from core.logging_config import get_logger
from models.content import PostStatus
from services.publish_service import PublishService, PublishConfig

logger = get_logger(__name__)


class TaskStatus:
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTask:
    """Represents a background task with status tracking"""

    def __init__(self, task_id: str, task_type: str, data: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.data = data
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.progress: Dict[str, Any] = {}


class BackgroundTaskService:
    """Service for managing background tasks"""

    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.db_client = None

    def set_db_client(self, db_client):
        """Set database client for updating post status"""
        self.db_client = db_client

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and progress"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
            "result": task.result,
            "progress": task.progress
        }

    async def create_and_publish_post_task(
        self,
        post_id: str,
        title: str,
        content: str,
        tenant_id: str,
        user_id: str,
        channel_group_id: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
        image_url: Optional[str] = None,
        post_mode: Optional[str] = None,
        headline: Optional[str] = None,  # User-provided headline
        social_accounts: Optional[List[Dict[str, Any]]] = None,
        source_image_url: Optional[str] = None  # Original reshare post image for LLM vision
    ) -> str:
        """
        Create and queue a background task for immediate post publishing

        Returns:
            task_id: ID of the created background task
        """
        task_id = str(uuid4())

        task_data = {
            "post_id": post_id,
            "title": title,
            "content": content,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "channel_group_id": channel_group_id,
            "media_ids": media_ids or [],
            "image_url": image_url,
            "post_mode": post_mode,
            "headline": headline,  # User-provided headline
            "social_accounts": social_accounts or [],
            "source_image_url": source_image_url  # Original reshare image for LLM
        }

        task = BackgroundTask(task_id, "publish_post", task_data)
        self.tasks[task_id] = task

        # Start the task asynchronously
        asyncio.create_task(self._process_publish_post_task(task))

        logger.info(f"Created background publish task {task_id} for post {post_id}")
        return task_id

    async def _process_publish_post_task(self, task: BackgroundTask):
        """Process a post publishing task in the background"""
        try:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            self.running_tasks.add(task.task_id)

            data = task.data
            post_id = data["post_id"]

            logger.info(f"Starting background processing for post {post_id}")

            # Step 1: Update post status to PUBLISHING
            await self._update_post_status(
                post_id, PostStatus.PUBLISHING, data["tenant_id"],
                {"processing_task_id": task.task_id}
            )
            task.progress["status_updated"] = "publishing"

            # Step 2: Initialize publish service with social accounts
            publish_config = PublishConfig(
                channels=[],
                publish_text=True,
                publish_image=True,
                generate_news_card=True if data["post_mode"] in ["news_card", "newscard_with_image"] else False,
                channel_group_id=data["channel_group_id"],
                social_accounts=data["social_accounts"]
            )

            publish_service = PublishService(publish_config)
            publish_service.set_db_client(self.db_client)

            # Set headline flags for publish service
            headline = data.get("headline")
            should_include_headline = (
                data["post_mode"] in ["news_card", "newscard_with_image"] and
                not headline  # Only generate if not provided by user
            )
            publish_service._should_include_headline = should_include_headline
            publish_service._provided_headline = headline

            task.progress["publish_service_initialized"] = True

            # Step 3: Execute publishing (includes newscard generation, content adaptation)
            logger.info(f"Publishing post {post_id} in background...")
            publish_result = await publish_service.publish_post(
                post_id=post_id,
                title=data["title"],
                content=data["content"],
                tenant_id=data["tenant_id"],
                user_id=data["user_id"],
                image_url=data["image_url"],
                post_mode=data["post_mode"],
                preview_mode=False,
                source_image_url=data.get("source_image_url")  # Pass source image for LLM
            )

            task.progress["publishing_completed"] = True
            task.progress["channels_processed"] = len(publish_result.get("channels", {}))

            # Step 4: Store final result
            task.result = publish_result

            if publish_result.get("success"):
                task.status = TaskStatus.COMPLETED
                logger.info(f"Background publishing completed successfully for post {post_id}")

                # Update post with final results
                await self._update_post_status(
                    post_id, PostStatus.PUBLISHED, data["tenant_id"],
                    {
                        "published_at": datetime.utcnow().isoformat(),
                        "news_card_url": publish_result.get("news_card_url"),
                        "processing_task_id": None,
                        "publish_results": publish_result.get("channels", {}),
                        "metadata": {
                            "background_task_id": task.task_id,
                            "publish_summary": publish_result.get("summary", {})
                        }
                    }
                )
            else:
                task.status = TaskStatus.FAILED
                task.error = publish_result.get("error", "Publishing failed")
                logger.error(f"Background publishing failed for post {post_id}: {task.error}")

                # Update post status to failed
                await self._update_post_status(
                    post_id, PostStatus.FAILED, data["tenant_id"],
                    {
                        "processing_task_id": None,
                        "error_message": task.error,
                        "metadata": {
                            "background_task_id": task.task_id,
                            "failed_at": datetime.utcnow().isoformat()
                        }
                    }
                )

            task.completed_at = datetime.utcnow()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            logger.exception(f"Background task {task.task_id} failed: {e}")

            # Update post status to failed
            if self.db_client:
                try:
                    await self._update_post_status(
                        data["post_id"], PostStatus.FAILED, data["tenant_id"],
                        {
                            "processing_task_id": None,
                            "error_message": str(e),
                            "metadata": {
                                "background_task_id": task.task_id,
                                "failed_at": datetime.utcnow().isoformat()
                            }
                        }
                    )
                except Exception as update_error:
                    logger.exception(f"Failed to update post status after task failure: {update_error}")

        finally:
            # Clean up
            self.running_tasks.discard(task.task_id)

            # Clean up old completed tasks (keep last 100)
            if len(self.tasks) > 100:
                # Remove oldest completed tasks
                completed_tasks = [
                    (task_id, task) for task_id, task in self.tasks.items()
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                    and task.completed_at
                ]
                completed_tasks.sort(key=lambda x: x[1].completed_at)

                # Remove oldest 20 tasks
                for task_id, _ in completed_tasks[:20]:
                    del self.tasks[task_id]
                    logger.debug(f"Cleaned up old task {task_id}")

    async def _update_post_status(
        self,
        post_id: str,
        status: PostStatus,
        tenant_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Update post status in database"""
        try:
            if not self.db_client:
                logger.warning("Database client not set, skipping post status update")
                return

            # Skip database update for preview posts (non-UUID post_id like "preview")
            try:
                UUID(post_id)
            except (ValueError, AttributeError):
                logger.debug(f"Skipping database update for non-UUID post_id: {post_id}")
                return

            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }

            if additional_data:
                update_data.update(additional_data)

            # Get database client (handle wrapped clients)
            db_client = self.db_client
            if hasattr(self.db_client, 'service_client'):
                db_client = self.db_client.service_client
            elif hasattr(self.db_client, 'client'):
                db_client = self.db_client.client

            # Build and execute query
            query = db_client.table('posts').update(update_data).eq('id', post_id)
            if tenant_id:
                query = query.eq('tenant_id', tenant_id)

            result = query.execute()

            if result.data:
                logger.info(f"Updated post {post_id} status to {status.value}")
            else:
                logger.warning(f"Failed to update post {post_id} status - no rows affected")

        except Exception as e:
            logger.exception(f"Error updating post {post_id} status: {e}")

    async def get_post_processing_status(self, post_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get the processing status of a post by checking for active background tasks"""
        try:
            # Find active tasks for this post
            active_task = None
            for task in self.tasks.values():
                if (task.data.get("post_id") == post_id and
                    task.data.get("tenant_id") == tenant_id and
                    task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]):
                    active_task = task
                    break

            if active_task:
                return self.get_task_status(active_task.task_id)

            # Check database for processing task ID
            if self.db_client:
                db_client = self.db_client
                if hasattr(self.db_client, 'service_client'):
                    db_client = self.db_client.service_client
                elif hasattr(self.db_client, 'client'):
                    db_client = self.db_client.client

                post_response = db_client.table('posts').select(
                    'status, processing_task_id, metadata'
                ).eq('id', post_id).eq('tenant_id', tenant_id).maybe_single().execute()

                if post_response.data:
                    post_data = post_response.data
                    processing_task_id = post_data.get('processing_task_id')

                    if processing_task_id and processing_task_id in self.tasks:
                        return self.get_task_status(processing_task_id)

                    # Return basic status info
                    return {
                        "post_id": post_id,
                        "status": post_data.get('status'),
                        "metadata": post_data.get('metadata', {})
                    }

            return None

        except Exception as e:
            logger.exception(f"Error getting post processing status: {e}")
            return None

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all currently active (pending/processing) tasks"""
        active_tasks = []
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                active_tasks.append(self.get_task_status(task.task_id))
        return active_tasks

    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about background tasks"""
        total_tasks = len(self.tasks)
        running_count = len(self.running_tasks)

        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_count,
            "status_breakdown": status_counts,
            "task_types": list(set(task.task_type for task in self.tasks.values()))
        }


# Global background task service instance
background_task_service = BackgroundTaskService()


def get_background_task_service() -> BackgroundTaskService:
    """Get the global background task service instance"""
    return background_task_service