"""
NewsIt SQS Consumer Worker
Background worker that polls SQS queue for NewsIt news items
and processes them into the external news system
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from services.sqs_service import get_sqs_service
from services.external_news_service import get_external_news_service
from models.external_news import NewsItSQSMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('newsit_consumer.log')
    ]
)

logger = logging.getLogger(__name__)


class NewsItConsumer:
    """SQS consumer for NewsIt news items"""

    def __init__(self):
        self.sqs_service = get_sqs_service()
        self.news_service = get_external_news_service()
        self.running = False
        self.poll_interval = 5  # seconds between polls when queue is empty
        self.error_backoff = 30  # seconds to wait after error

    async def process_message(self, message: dict) -> bool:
        """
        Process a single SQS message

        Args:
            message: SQS message dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            message_id = message.get('MessageId')
            receipt_handle = message.get('ReceiptHandle')

            logger.info(f"Processing message: {message_id}")

            # Parse message body
            body = self.sqs_service.parse_message_body(message)
            if not body:
                logger.error(f"Failed to parse message body: {message_id}")
                # Delete malformed message to prevent reprocessing
                await self.sqs_service.delete_message(receipt_handle)
                return False

            # Validate message structure
            try:
                sqs_message = NewsItSQSMessage(**body)
            except Exception as e:
                logger.error(f"Invalid message structure: {e}")
                # Delete invalid message
                await self.sqs_service.delete_message(receipt_handle)
                return False

            # Determine tenant ID
            # If message includes tenant_id, use it; otherwise use a default or configured tenant
            tenant_id = sqs_message.tenant_id
            if not tenant_id:
                # Option 1: Skip messages without tenant_id
                # Option 2: Use a default tenant from config
                # Option 3: Route to all tenants
                logger.warning(f"Message {message_id} has no tenant_id, skipping")
                await self.sqs_service.delete_message(receipt_handle)
                return False

            # Process the news item
            result = await self.news_service.process_newsit_message(
                message_data=body,
                tenant_id=tenant_id,
                sqs_message_id=message_id
            )

            if result.success:
                logger.info(
                    f"Successfully processed news item: {result.external_id} "
                    f"(duplicate: {result.is_duplicate})"
                )
                # Delete message from queue
                await self.sqs_service.delete_message(receipt_handle)
                return True
            else:
                logger.error(f"Failed to process news item: {result.error_message}")
                # Don't delete - let it retry or move to DLQ based on queue config
                # Optionally: change visibility to delay retry
                await self.sqs_service.change_message_visibility(receipt_handle, 300)  # 5 min delay
                return False

        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            # Change visibility to delay retry
            try:
                receipt_handle = message.get('ReceiptHandle')
                if receipt_handle:
                    await self.sqs_service.change_message_visibility(receipt_handle, 300)
            except:
                pass
            return False

    async def poll_and_process(self):
        """
        Main polling loop - receive and process messages
        """
        logger.info("Starting SQS polling loop")

        while self.running:
            try:
                # Receive messages from SQS (long polling)
                messages = await self.sqs_service.receive_messages()

                if not messages:
                    logger.debug("No messages received, continuing polling")
                    await asyncio.sleep(1)  # Short sleep before next poll
                    continue

                logger.info(f"Received {len(messages)} message(s)")

                # Process messages concurrently
                tasks = [self.process_message(msg) for msg in messages]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log summary
                success_count = sum(1 for r in results if r is True)
                logger.info(f"Processed {success_count}/{len(messages)} messages successfully")

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                # Back off on error
                logger.info(f"Backing off for {self.error_backoff}s due to error")
                await asyncio.sleep(self.error_backoff)

        logger.info("Polling loop stopped")

    async def start(self):
        """Start the consumer"""
        logger.info("=== NewsIt SQS Consumer Starting ===")
        logger.info(f"SQS Queue URL: {settings.aws_sqs_queue_url}")
        logger.info(f"AWS Region: {settings.aws_sqs_region}")
        logger.info(f"Max Messages: {settings.aws_sqs_max_messages}")
        logger.info(f"Wait Time: {settings.aws_sqs_wait_time}s")

        if not settings.aws_sqs_queue_url:
            logger.error("AWS_SQS_QUEUE_URL not configured, cannot start consumer")
            return

        self.running = True

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start polling
        await self.poll_and_process()

        logger.info("=== NewsIt SQS Consumer Stopped ===")

    async def stop(self):
        """Stop the consumer"""
        logger.info("Stopping consumer...")
        self.running = False


async def main():
    """Main entry point"""
    consumer = NewsItConsumer()
    await consumer.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
