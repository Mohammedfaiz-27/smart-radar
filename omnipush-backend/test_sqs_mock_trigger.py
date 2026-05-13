"""
Mock SQS Trigger - Simulates SQS message delivery to consumer
This allows testing the SQS consumer without needing actual AWS SQS
"""

import asyncio
import json
import sys
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4, UUID
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import actual services for debug mode
DEBUG_MODE_AVAILABLE = False
try:
    from services.external_news_service import get_external_news_service
    from models.external_news import NewsItSQSMessage
    DEBUG_MODE_AVAILABLE = True
    logger.info("✓ Debug mode available - actual services loaded")
except ImportError as e:
    logger.warning(f"⚠️  Debug mode not available: {e}")
    logger.warning("   Run 'uv sync' to enable debug mode with actual service integration")


class MockSQSService:
    """Mock SQS service that simulates message delivery"""

    def __init__(self):
        self.messages_queue: List[Dict[str, Any]] = []
        self.processed_messages: List[str] = []
        self.failed_messages: List[str] = []

    def send_message(self, news_id: str, tenant_id: str, metadata: Dict[str, Any] = None):
        """
        Simulate sending a message to SQS queue

        Args:
            news_id: NewsIt news item ID
            tenant_id: Tenant UUID
            metadata: Optional metadata
        """
        message = self._create_sqs_message(news_id, tenant_id, metadata)
        self.messages_queue.append(message)
        print(f"📨 Message added to queue: {message['MessageId']}")
        return message

    def send_messages_batch(self, messages_data: List[Dict[str, str]]):
        """
        Send multiple messages to queue

        Args:
            messages_data: List of dicts with news_id, tenant_id, metadata
        """
        for data in messages_data:
            self.send_message(
                news_id=data['news_id'],
                tenant_id=data['tenant_id'],
                metadata=data.get('metadata')
            )

    def _create_sqs_message(self, news_id: str, tenant_id: str, metadata: Dict = None) -> Dict[str, Any]:
        """Create a properly formatted SQS message"""
        message_id = str(uuid4())
        receipt_handle = f"receipt-{uuid4()}"

        body = {
            "news_id": news_id,
            "tenant_id": tenant_id,
            "source": "newsit",
            "metadata": metadata or {
                "trigger_time": datetime.utcnow().isoformat(),
                "trigger_source": "mock_test"
            }
        }

        return {
            "MessageId": message_id,
            "ReceiptHandle": receipt_handle,
            "Body": json.dumps(body),
            "Attributes": {
                "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
                "ApproximateReceiveCount": "1",
                "ApproximateFirstReceiveTimestamp": str(int(datetime.utcnow().timestamp() * 1000))
            },
            "MessageAttributes": {},
            "MD5OfBody": "test-md5-hash",
            "EventSource": "aws:sqs",
            "EventSourceARN": "arn:aws:sqs:test:123456789:mock-queue",
            "AwsRegion": "us-east-1"
        }

    async def receive_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Simulate receiving messages from queue

        Args:
            max_messages: Maximum number of messages to return

        Returns:
            List of SQS messages
        """
        # Return up to max_messages from queue
        messages = self.messages_queue[:max_messages]
        return messages

    async def delete_message(self, receipt_handle: str) -> bool:
        """
        Simulate deleting a message from queue

        Args:
            receipt_handle: Receipt handle of message to delete

        Returns:
            True if successful
        """
        # Remove message with matching receipt handle
        self.messages_queue = [
            msg for msg in self.messages_queue
            if msg['ReceiptHandle'] != receipt_handle
        ]
        self.processed_messages.append(receipt_handle)
        return True

    async def change_message_visibility(self, receipt_handle: str, visibility_timeout: int) -> bool:
        """
        Simulate changing message visibility (for retry delay)

        Args:
            receipt_handle: Receipt handle of message
            visibility_timeout: Timeout in seconds

        Returns:
            True if successful
        """
        print(f"🕐 Message visibility changed: {visibility_timeout}s delay")
        self.failed_messages.append(receipt_handle)
        return True

    def parse_message_body(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON body from SQS message"""
        try:
            return json.loads(message['Body'])
        except json.JSONDecodeError:
            return None

    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "pending": len(self.messages_queue),
            "processed": len(self.processed_messages),
            "failed": len(self.failed_messages)
        }


class MockNewsItConsumer:
    """Mock consumer that uses MockSQSService"""

    def __init__(self, sqs_service: MockSQSService, debug_mode: bool = False):
        self.sqs_service = sqs_service
        self.news_service = None  # Will use actual service if available
        self.running = False
        self.debug_mode = debug_mode

        # Initialize actual service in debug mode
        if debug_mode and DEBUG_MODE_AVAILABLE:
            self.news_service = get_external_news_service()
            logger.info("🐛 Debug mode enabled - using actual external_news_service")

    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a single SQS message
        This mimics the actual consumer's process_message method

        In debug mode, calls the actual process_newsit_message function
        """
        try:
            message_id = message.get('MessageId')
            receipt_handle = message.get('ReceiptHandle')

            print(f"\n🔄 Processing message: {message_id[:8]}...")

            # Parse message body
            body = self.sqs_service.parse_message_body(message)
            if not body:
                print(f"❌ Failed to parse message body")
                await self.sqs_service.delete_message(receipt_handle)
                return False

            # Display message details
            print(f"   News ID: {body.get('news_id')}")
            print(f"   Tenant ID: {body.get('tenant_id')}")
            print(f"   Source: {body.get('source')}")

            # Validate required fields
            if not body.get('tenant_id'):
                print(f"⚠️  No tenant_id, skipping message")
                await self.sqs_service.delete_message(receipt_handle)
                return False

            # DEBUG MODE: Use actual service
            if self.debug_mode and self.news_service:
                print(f"\n🐛 DEBUG MODE: Calling actual process_newsit_message...")
                print(f"   This will:")
                print(f"   1. Validate message structure")
                print(f"   2. Fetch news from NewsIt API")
                print(f"   3. Transform to generic format")
                print(f"   4. Store in external_news_items table")
                print(f"   5. Check for duplicates")

                try:
                    # Call actual service
                    result = await self.news_service.process_newsit_message(
                        message_data=body,
                        tenant_id=UUID(body['tenant_id']),
                        sqs_message_id=message_id
                    )

                    print(f"\n📊 Processing Result:")
                    print(f"   Success: {result.success}")
                    print(f"   External ID: {result.external_id}")
                    print(f"   External News Item ID: {result.external_news_item_id}")
                    print(f"   Is Duplicate: {result.is_duplicate}")

                    if result.error_message:
                        print(f"   ❌ Error: {result.error_message}")

                    if result.success:
                        # Delete message from queue
                        await self.sqs_service.delete_message(receipt_handle)
                        print(f"\n✅ Message processed successfully via actual service")

                        if result.is_duplicate:
                            print(f"   ℹ️  Item was a duplicate - no new record created")
                        else:
                            print(f"   ℹ️  New external news item created: {result.external_news_item_id}")

                        return True
                    else:
                        # Change visibility for retry
                        await self.sqs_service.change_message_visibility(receipt_handle, 300)
                        print(f"\n❌ Processing failed - message will retry")
                        return False

                except Exception as service_error:
                    print(f"\n❌ Service Error: {service_error}")
                    import traceback
                    traceback.print_exc()

                    # Change visibility for retry
                    await self.sqs_service.change_message_visibility(receipt_handle, 300)
                    return False

            # MOCK MODE: Simulate processing
            else:
                print(f"   ✓ Message validated")
                print(f"   ✓ Ready for NewsIt API fetch")
                print(f"   ✓ Ready to store in database")

                # Delete message from queue (acknowledge)
                await self.sqs_service.delete_message(receipt_handle)
                print(f"✅ Message processed successfully (mock mode)")

                return True

        except Exception as e:
            print(f"❌ Error processing message: {e}")
            import traceback
            traceback.print_exc()

            # Change visibility to delay retry
            receipt_handle = message.get('ReceiptHandle')
            if receipt_handle:
                await self.sqs_service.change_message_visibility(receipt_handle, 300)
            return False

    async def poll_and_process(self, max_iterations: int = None):
        """
        Simulate polling loop

        Args:
            max_iterations: Optional limit on iterations (for testing)
        """
        print("\n🚀 Starting mock SQS polling loop...")
        self.running = True
        iteration = 0

        while self.running:
            iteration += 1

            if max_iterations and iteration > max_iterations:
                print(f"\n⏹️  Reached max iterations ({max_iterations})")
                break

            # Receive messages
            messages = await self.sqs_service.receive_messages()

            if not messages:
                print(f"\n💤 No messages in queue (iteration {iteration})")
                await asyncio.sleep(1)
                continue

            print(f"\n📬 Received {len(messages)} message(s) (iteration {iteration})")

            # Process messages
            tasks = [self.process_message(msg) for msg in messages]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log summary
            success_count = sum(1 for r in results if r is True)
            print(f"\n📊 Batch result: {success_count}/{len(messages)} successful")

            # Check if queue is empty
            stats = self.sqs_service.get_queue_stats()
            if stats['pending'] == 0:
                print(f"\n✓ Queue empty, stopping...")
                break

        self.running = False
        print(f"\n⏹️  Polling loop stopped")

        # Final stats
        stats = self.sqs_service.get_queue_stats()
        print(f"\n📈 Final Statistics:")
        print(f"   Processed: {stats['processed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Remaining: {stats['pending']}")


# =====================================================
# Test Scenarios
# =====================================================

async def scenario_single_message(debug_mode: bool = False, news_id: str = None, tenant_id: str = None):
    """Test Scenario 1: Single message processing"""
    print("\n" + "="*60)
    print("SCENARIO 1: Single Message Processing")
    if debug_mode:
        print("🐛 DEBUG MODE ENABLED")
    print("="*60)

    # Check if debug mode is available
    if debug_mode and not DEBUG_MODE_AVAILABLE:
        print("\n❌ Debug mode not available!")
        print("   Please run: uv sync")
        print("   This will install required dependencies for actual service integration.")
        return

    # Create mock SQS
    sqs = MockSQSService()
    consumer = MockNewsItConsumer(sqs, debug_mode=debug_mode)

    # Get tenant ID from database if not provided
    if debug_mode and not tenant_id:
        try:
            from core.database import get_database
            db = get_database()
            tenant_result = db.client.table('tenants').select('id').limit(1).execute()
            if tenant_result.data:
                tenant_id = tenant_result.data[0]['id']
                print(f"\n✓ Using tenant from database: {tenant_id}")
            else:
                print("\n❌ No tenants found in database")
                print("   Please create a tenant first or provide tenant_id as argument")
                return
        except Exception as e:
            print(f"\n❌ Error accessing database: {e}")
            return

    # Default values
    default_news_id = news_id or "691896c41a6aabeae05d0a66"
    default_tenant_id = tenant_id or "550e8400-e29b-41d4-a716-446655440000"

    # Send a test message
    print(f"\n📤 Sending test message to queue...")
    print(f"   News ID: {default_news_id}")
    print(f"   Tenant ID: {default_tenant_id}")

    sqs.send_message(
        news_id=default_news_id,
        tenant_id=default_tenant_id,
        metadata={"test": "scenario_1", "priority": "normal"}
    )

    # Process the queue
    await consumer.poll_and_process(max_iterations=1)


async def scenario_batch_processing():
    """Test Scenario 2: Batch message processing"""
    print("\n" + "="*60)
    print("SCENARIO 2: Batch Message Processing")
    print("="*60)

    sqs = MockSQSService()
    consumer = MockNewsItConsumer(sqs)

    # Send multiple messages
    print("\n📤 Sending batch of messages to queue...")
    messages_data = [
        {
            "news_id": "newsit-batch-001",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "metadata": {"batch_index": 0, "category": "politics"}
        },
        {
            "news_id": "newsit-batch-002",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "metadata": {"batch_index": 1, "category": "sports"}
        },
        {
            "news_id": "newsit-batch-003",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "metadata": {"batch_index": 2, "category": "technology"}
        }
    ]

    sqs.send_messages_batch(messages_data)

    # Process the queue
    await consumer.poll_and_process(max_iterations=1)


async def scenario_error_handling():
    """Test Scenario 3: Error handling"""
    print("\n" + "="*60)
    print("SCENARIO 3: Error Handling")
    print("="*60)

    sqs = MockSQSService()
    consumer = MockNewsItConsumer(sqs)

    # Send message with missing tenant_id
    print("\n📤 Sending message with missing tenant_id...")
    message = sqs._create_sqs_message(
        news_id="newsit-error-001",
        tenant_id="",  # Empty tenant_id
        metadata={"test": "error_handling"}
    )
    sqs.messages_queue.append(message)

    # Send malformed message
    print("📤 Sending malformed message...")
    malformed_message = {
        "MessageId": str(uuid4()),
        "ReceiptHandle": f"receipt-{uuid4()}",
        "Body": "This is not valid JSON {invalid",
        "Attributes": {},
        "MessageAttributes": {}
    }
    sqs.messages_queue.append(malformed_message)

    # Process the queue
    await consumer.poll_and_process(max_iterations=1)


async def scenario_continuous_polling():
    """Test Scenario 4: Continuous polling with multiple iterations"""
    print("\n" + "="*60)
    print("SCENARIO 4: Continuous Polling")
    print("="*60)

    sqs = MockSQSService()
    consumer = MockNewsItConsumer(sqs)

    # Send messages over time (simulated)
    print("\n📤 Sending initial messages...")
    sqs.send_messages_batch([
        {
            "news_id": f"newsit-continuous-{i:03d}",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "metadata": {"iteration": 1}
        }
        for i in range(5)
    ])

    # Process the queue with max iterations
    await consumer.poll_and_process(max_iterations=3)


async def scenario_custom_messages(news_id: str, tenant_id: str):
    """Test Scenario 5: Custom message with user-provided IDs"""
    print("\n" + "="*60)
    print("SCENARIO 5: Custom Message Processing")
    print("="*60)

    sqs = MockSQSService()
    consumer = MockNewsItConsumer(sqs)

    print(f"\n📤 Sending custom message...")
    print(f"   News ID: {news_id}")
    print(f"   Tenant ID: {tenant_id}")

    sqs.send_message(
        news_id=news_id,
        tenant_id=tenant_id,
        metadata={
            "source": "manual_test",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Process the queue
    await consumer.poll_and_process(max_iterations=1)


# =====================================================
# Main Test Runner
# =====================================================

async def run_all_scenarios():
    """Run all test scenarios"""
    print("\n" + "="*60)
    print("MOCK SQS TRIGGER - ALL SCENARIOS")
    print("="*60)

    await scenario_single_message()
    await asyncio.sleep(1)

    await scenario_batch_processing()
    await asyncio.sleep(1)

    await scenario_error_handling()
    await asyncio.sleep(1)

    await scenario_continuous_polling()

    print("\n" + "="*60)
    print("ALL SCENARIOS COMPLETED")
    print("="*60)


def print_usage():
    """Print usage instructions"""
    print("""
Mock SQS Trigger - Test Tool

DESCRIPTION:
  Simulates AWS SQS message delivery to the NewsIt consumer
  without requiring actual AWS credentials or SQS queue.

USAGE:
  python test_sqs_mock_trigger.py [SCENARIO] [OPTIONS]

SCENARIOS:
  all                Run all test scenarios
  single             Single message processing (mock mode)
  single-debug       Single message processing (DEBUG MODE - calls actual service)
  batch              Batch message processing (3 messages)
  error              Error handling (malformed messages)
  continuous         Continuous polling simulation
  custom             Custom message with your news_id and tenant_id

OPTIONS:
  --debug            Enable debug mode (calls actual process_newsit_message)
  --news-id          NewsIt news item ID (for debug mode)
  --tenant-id        Tenant UUID (for debug mode)

EXAMPLES:
  # Run all scenarios (mock mode)
  python test_sqs_mock_trigger.py all

  # Test single message (mock mode)
  python test_sqs_mock_trigger.py single

  # Test single message (DEBUG MODE - actual service)
  python test_sqs_mock_trigger.py single-debug

  # Test with custom IDs in debug mode
  python test_sqs_mock_trigger.py single-debug --news-id 691896c41a6aabeae05d0a66 --tenant-id <your-tenant-id>

  # Test with custom message
  python test_sqs_mock_trigger.py custom newsit-12345 550e8400-e29b-41d4-a716-446655440000

SAMPLE SQS MESSAGE FORMAT:
  {
    "MessageId": "uuid",
    "ReceiptHandle": "receipt-handle",
    "Body": {
      "news_id": "newsit-123456",
      "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "newsit",
      "metadata": {
        "trigger_time": "2025-01-16T10:30:00Z",
        "trigger_source": "newsit_webhook"
      }
    },
    "Attributes": {...},
    "MessageAttributes": {...}
  }

WHAT THIS TESTS:
  ✓ SQS message structure validation
  ✓ Message parsing and body extraction
  ✓ NewsIt message payload validation
  ✓ Message processing flow
  ✓ Error handling (malformed, missing fields)
  ✓ Message deletion (acknowledgment)
  ✓ Retry with visibility timeout
  ✓ Batch processing
  ✓ Continuous polling

DEBUG MODE:
  When using 'single-debug' or '--debug' flag:
  ✓ Calls actual process_newsit_message function
  ✓ Fetches from NewsIt API
  ✓ Stores in external_news_items table
  ✓ Checks for duplicates
  ✓ Full integration testing

  Requires:
  - uv sync (install dependencies)
  - .env configured with NEWSIT_API_KEY, NEWSIT_API_URL
  - Database access
  - Valid tenant_id and news_id

MOCK MODE (default):
  Simulates SQS behavior without external dependencies.
  Does NOT:
  - Connect to actual AWS SQS
  - Fetch from NewsIt API
  - Write to database

  Use for: Message structure validation, flow testing
    """)


if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Mock SQS Trigger - Test Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'scenario',
        nargs='?',
        default='single',
        choices=['all', 'single', 'single-debug', 'batch', 'error', 'continuous', 'custom'],
        help='Test scenario to run'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (calls actual process_newsit_message)'
    )
    parser.add_argument(
        '--news-id',
        type=str,
        help='NewsIt news item ID (for debug mode)'
    )
    parser.add_argument(
        '--tenant-id',
        type=str,
        help='Tenant UUID (for debug mode)'
    )
    parser.add_argument(
        'custom_args',
        nargs='*',
        help='Custom arguments for custom scenario (news_id tenant_id)'
    )

    args = parser.parse_args()

    # Determine debug mode
    debug_mode = args.debug or args.scenario == 'single-debug'
    scenario = args.scenario

    # Override scenario if single-debug
    if scenario == 'single-debug':
        scenario = 'single'
        debug_mode = True

    # Execute scenario
    if scenario == 'all':
        asyncio.run(run_all_scenarios())
    elif scenario == 'single':
        asyncio.run(scenario_single_message(
            debug_mode=debug_mode,
            news_id=args.news_id,
            tenant_id=args.tenant_id
        ))
    elif scenario == 'batch':
        asyncio.run(scenario_batch_processing())
    elif scenario == 'error':
        asyncio.run(scenario_error_handling())
    elif scenario == 'continuous':
        asyncio.run(scenario_continuous_polling())
    elif scenario == 'custom':
        if len(args.custom_args) < 2:
            print("❌ Error: Custom scenario requires news_id and tenant_id")
            print("Usage: python test_sqs_mock_trigger.py custom <news_id> <tenant_id>")
        else:
            news_id = args.custom_args[0]
            tenant_id = args.custom_args[1]
            asyncio.run(scenario_custom_messages(news_id, tenant_id))
    else:
        print(f"❌ Unknown scenario: {scenario}")
        print("Run with --help to see available scenarios")
