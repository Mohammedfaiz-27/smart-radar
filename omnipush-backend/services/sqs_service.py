"""
AWS SQS Service for External News Integration
Handles receiving and managing messages from AWS SQS queue
"""

import boto3
import json
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, BotoCoreError

from core.config import settings

logger = logging.getLogger(__name__)


class SQSService:
    """Service for interacting with AWS SQS"""

    def __init__(self, queue_url: Optional[str] = None):
        """
        Initialize SQS client with AWS credentials from settings

        Args:
            queue_url: Optional queue URL override. If not provided, uses settings.aws_sqs_queue_url
        """
        try:
            self.sqs_client = boto3.client(
                'sqs',
                region_name=settings.aws_sqs_region,
                aws_access_key_id=settings.aws_sqs_access_key,
                aws_secret_access_key=settings.aws_sqs_secret
            )
            self.queue_url = queue_url or settings.aws_sqs_queue_url
            self.max_messages = settings.aws_sqs_max_messages
            self.wait_time = settings.aws_sqs_wait_time

            logger.info(f"SQS Service initialized for region: {settings.aws_sqs_region}, queue: {self.queue_url}")
        except Exception as e:
            logger.error(f"Failed to initialize SQS client: {e}")
            raise

    async def receive_messages(
        self,
        max_messages: Optional[int] = None,
        wait_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from SQS queue using long polling

        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds (0-20)

        Returns:
            List of message dictionaries
        """
        if not self.queue_url:
            logger.warning("SQS queue URL not configured, skipping message retrieval")
            return []

        max_msgs = max_messages or self.max_messages
        wait_secs = wait_time or self.wait_time

        # Ensure valid ranges
        max_msgs = max(1, min(10, max_msgs))
        wait_secs = max(0, min(20, wait_secs))

        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_msgs,
                WaitTimeSeconds=wait_secs,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )

            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")

            return messages

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"SQS ClientError ({error_code}): {e}")
            raise
        except BotoCoreError as e:
            logger.error(f"SQS BotoCoreError: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error receiving SQS messages: {e}")
            raise

    async def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete (acknowledge) a message from the queue

        Args:
            receipt_handle: Receipt handle from the received message

        Returns:
            True if successful, False otherwise
        """
        if not self.queue_url:
            logger.warning("SQS queue URL not configured")
            return False

        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Successfully deleted message from SQS")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting message: {e}")
            return False

    async def delete_messages_batch(self, receipt_handles: List[str]) -> Dict[str, Any]:
        """
        Delete multiple messages in a batch (up to 10)

        Args:
            receipt_handles: List of receipt handles

        Returns:
            Dictionary with success and failure counts
        """
        if not self.queue_url or not receipt_handles:
            return {"successful": 0, "failed": 0}

        # Batch delete supports max 10 messages
        batch_size = 10
        results = {"successful": 0, "failed": 0}

        for i in range(0, len(receipt_handles), batch_size):
            batch = receipt_handles[i:i + batch_size]
            entries = [
                {"Id": str(idx), "ReceiptHandle": handle}
                for idx, handle in enumerate(batch)
            ]

            try:
                response = self.sqs_client.delete_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )

                results["successful"] += len(response.get('Successful', []))
                results["failed"] += len(response.get('Failed', []))

            except Exception as e:
                logger.error(f"Batch delete error: {e}")
                results["failed"] += len(batch)

        logger.info(f"Batch delete results: {results}")
        return results

    async def change_message_visibility(
        self,
        receipt_handle: str,
        visibility_timeout: int
    ) -> bool:
        """
        Change the visibility timeout of a message (delay reprocessing)

        Args:
            receipt_handle: Receipt handle from the received message
            visibility_timeout: New visibility timeout in seconds (0-43200)

        Returns:
            True if successful, False otherwise
        """
        if not self.queue_url:
            return False

        try:
            self.sqs_client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=max(0, min(43200, visibility_timeout))
            )
            logger.debug(f"Changed message visibility to {visibility_timeout}s")
            return True

        except Exception as e:
            logger.error(f"Failed to change message visibility: {e}")
            return False

    async def get_queue_attributes(self) -> Dict[str, Any]:
        """
        Get queue attributes (message count, etc.)

        Returns:
            Dictionary of queue attributes
        """
        if not self.queue_url:
            return {}

        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )
            return response.get('Attributes', {})

        except Exception as e:
            logger.error(f"Failed to get queue attributes: {e}")
            return {}

    def parse_message_body(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse message body JSON

        Args:
            message: SQS message dictionary

        Returns:
            Parsed message body or None if parsing fails
        """
        try:
            body = message.get('Body', '{}')
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message body: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing message: {e}")
            return None

    def get_message_attributes(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract message attributes

        Args:
            message: SQS message dictionary

        Returns:
            Dictionary of message attributes
        """
        attrs = {}
        message_attrs = message.get('MessageAttributes', {})

        for key, value in message_attrs.items():
            data_type = value.get('DataType', 'String')
            if data_type == 'String':
                attrs[key] = value.get('StringValue')
            elif data_type == 'Number':
                attrs[key] = float(value.get('StringValue', 0))
            else:
                attrs[key] = value.get('StringValue')

        return attrs


# Singleton instance for default queue
_sqs_service_instance: Optional[SQSService] = None


def get_sqs_service(queue_url: Optional[str] = None) -> SQSService:
    """
    Get or create SQS service instance

    Args:
        queue_url: Optional queue URL. If provided, creates a new instance.
                   If not provided, returns the singleton for the default queue.

    Returns:
        SQSService instance
    """
    global _sqs_service_instance

    # If queue_url is provided, create a new instance (not singleton)
    if queue_url:
        return SQSService(queue_url=queue_url)

    # Otherwise use singleton for default queue
    if _sqs_service_instance is None:
        _sqs_service_instance = SQSService()

    return _sqs_service_instance
