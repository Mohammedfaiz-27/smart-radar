"""
SQS Message Validation and Testing Tool
Provides sample SQS message payloads and simulates SQS message processing
"""

import asyncio
import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Conditional imports - only import when needed for processing
try:
    from workers.newsit_consumer import NewsItConsumer
    from models.external_news import NewsItSQSMessage
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    import warnings
    warnings.warn(f"Could not import required modules: {e}. Sample display only mode available.")
    # Create dummy types for type hints
    NewsItConsumer = Any
    NewsItSQSMessage = Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =====================================================
# Sample SQS Message Payloads
# =====================================================

def get_sample_sqs_message_simple() -> Dict[str, Any]:
    """
    Simple SQS message with minimal NewsIt payload
    This mimics the actual AWS SQS message structure
    """
    return {
        "MessageId": "test-message-" + str(uuid4()),
        "ReceiptHandle": "test-receipt-handle-" + str(uuid4()),
        "Body": json.dumps({
            "news_id": "newsit-123456",
            "tenant_id": "replace-with-actual-tenant-uuid",  # User must replace
            "source": "newsit",
            "metadata": {
                "trigger_time": datetime.utcnow().isoformat(),
                "trigger_source": "newsit_webhook"
            }
        }),
        "Attributes": {
            "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "ApproximateReceiveCount": "1",
            "ApproximateFirstReceiveTimestamp": str(int(datetime.utcnow().timestamp() * 1000))
        },
        "MessageAttributes": {},
        "MD5OfBody": "test-md5-hash",
        "EventSource": "aws:sqs",
        "EventSourceARN": "arn:aws:sqs:us-east-1:123456789:test-queue",
        "AwsRegion": "us-east-1"
    }


def get_sample_sqs_message_with_metadata() -> Dict[str, Any]:
    """
    SQS message with additional metadata and message attributes
    """
    return {
        "MessageId": "test-message-" + str(uuid4()),
        "ReceiptHandle": "test-receipt-handle-" + str(uuid4()),
        "Body": json.dumps({
            "news_id": "newsit-789012",
            "tenant_id": "replace-with-actual-tenant-uuid",
            "source": "newsit",
            "metadata": {
                "trigger_time": datetime.utcnow().isoformat(),
                "trigger_source": "newsit_webhook",
                "priority": "high",
                "is_breaking": True,
                "category": "politics",
                "language": "en"
            }
        }),
        "Attributes": {
            "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "ApproximateReceiveCount": "1",
            "ApproximateFirstReceiveTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "SenderId": "AIDAIT2UOQQY3AUEKVGXU"
        },
        "MessageAttributes": {
            "Priority": {
                "StringValue": "high",
                "DataType": "String"
            },
            "Source": {
                "StringValue": "newsit",
                "DataType": "String"
            }
        },
        "MD5OfBody": "test-md5-hash",
        "MD5OfMessageAttributes": "test-md5-attributes",
        "EventSource": "aws:sqs",
        "EventSourceARN": "arn:aws:sqs:us-east-1:123456789:newsit-queue",
        "AwsRegion": "us-east-1"
    }


def get_sample_sqs_message_batch() -> list:
    """
    Batch of SQS messages (simulates receiving multiple messages)
    """
    messages = []
    news_ids = ["newsit-001", "newsit-002", "newsit-003"]

    for news_id in news_ids:
        messages.append({
            "MessageId": "test-message-" + str(uuid4()),
            "ReceiptHandle": "test-receipt-handle-" + str(uuid4()),
            "Body": json.dumps({
                "news_id": news_id,
                "tenant_id": "replace-with-actual-tenant-uuid",
                "source": "newsit",
                "metadata": {
                    "trigger_time": datetime.utcnow().isoformat(),
                    "batch_index": news_ids.index(news_id)
                }
            }),
            "Attributes": {
                "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
                "ApproximateReceiveCount": "1"
            },
            "MessageAttributes": {},
            "MD5OfBody": "test-md5-hash"
        })

    return messages


def get_malformed_sqs_message() -> Dict[str, Any]:
    """
    Malformed SQS message for error handling testing
    """
    return {
        "MessageId": "test-message-malformed",
        "ReceiptHandle": "test-receipt-handle-malformed",
        "Body": "This is not valid JSON {invalid}",
        "Attributes": {
            "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000))
        },
        "MessageAttributes": {}
    }


def get_missing_fields_sqs_message() -> Dict[str, Any]:
    """
    SQS message with missing required fields (no tenant_id)
    """
    return {
        "MessageId": "test-message-missing-fields",
        "ReceiptHandle": "test-receipt-handle-missing-fields",
        "Body": json.dumps({
            "news_id": "newsit-999999",
            "source": "newsit"
            # Missing tenant_id
        }),
        "Attributes": {
            "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000))
        },
        "MessageAttributes": {}
    }


# =====================================================
# Message Validation Functions
# =====================================================

def validate_sqs_message_structure(message: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that SQS message has the correct structure

    Returns:
        (is_valid, error_message)
    """
    required_fields = ['MessageId', 'ReceiptHandle', 'Body']

    for field in required_fields:
        if field not in message:
            return False, f"Missing required field: {field}"

    # Try to parse body
    try:
        body = json.loads(message['Body'])
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in Body: {e}"

    # Validate body structure
    if 'news_id' not in body:
        return False, "Missing 'news_id' in message body"

    if 'source' not in body:
        return False, "Missing 'source' in message body"

    return True, "Valid"


def validate_newsit_message_payload(body: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate NewsIt message payload structure

    Returns:
        (is_valid, error_message)
    """
    try:
        # Basic validation if imports not available
        if not IMPORTS_AVAILABLE:
            if 'news_id' not in body:
                return False, "news_id is required"
            if 'tenant_id' not in body or not body['tenant_id']:
                return False, "tenant_id is required for processing"
            return True, "Valid NewsIt message (basic validation)"

        # Try to parse as NewsItSQSMessage if available
        sqs_message = NewsItSQSMessage(**body)

        if not sqs_message.news_id:
            return False, "news_id is required"

        if not sqs_message.tenant_id:
            return False, "tenant_id is required for processing"

        return True, "Valid NewsIt message"

    except Exception as e:
        return False, f"Invalid NewsIt message structure: {e}"


# =====================================================
# Test Functions
# =====================================================

async def test_single_message_processing(consumer: NewsItConsumer, message: Dict[str, Any]):
    """Test processing a single SQS message"""

    print("\n" + "="*60)
    print("TEST: Single Message Processing")
    print("="*60)

    # Validate message structure
    is_valid, error_msg = validate_sqs_message_structure(message)
    print(f"\n1. Message Structure Validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
    if not is_valid:
        print(f"   Error: {error_msg}")
        return False

    # Validate payload
    try:
        body = json.loads(message['Body'])
        is_valid, error_msg = validate_newsit_message_payload(body)
        print(f"2. Payload Validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
        if not is_valid:
            print(f"   Error: {error_msg}")
            return False
    except Exception as e:
        print(f"2. Payload Validation: ✗ FAIL")
        print(f"   Error: {e}")
        return False

    # Display message details
    print(f"\n3. Message Details:")
    print(f"   Message ID: {message['MessageId']}")
    print(f"   News ID: {body.get('news_id')}")
    print(f"   Tenant ID: {body.get('tenant_id')}")
    print(f"   Source: {body.get('source')}")
    if body.get('metadata'):
        print(f"   Metadata: {json.dumps(body['metadata'], indent=6)}")

    # Process the message
    print(f"\n4. Processing Message...")
    try:
        # Note: This will actually try to fetch from NewsIt API
        # Make sure you have a valid news_id and tenant_id
        result = await consumer.process_message(message)

        print(f"   Processing Result: {'✓ SUCCESS' if result else '✗ FAILED'}")
        return result

    except Exception as e:
        print(f"   Processing Result: ✗ EXCEPTION")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_batch_message_processing(consumer: NewsItConsumer, messages: list):
    """Test processing a batch of SQS messages"""

    print("\n" + "="*60)
    print("TEST: Batch Message Processing")
    print("="*60)

    print(f"\nProcessing {len(messages)} messages in batch...")

    tasks = []
    for idx, message in enumerate(messages):
        print(f"\n--- Message {idx + 1}/{len(messages)} ---")
        body = json.loads(message['Body'])
        print(f"News ID: {body.get('news_id')}")
        print(f"Message ID: {message['MessageId']}")

        tasks.append(consumer.process_message(message))

    print(f"\nExecuting batch processing...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r is True)
    failure_count = len(results) - success_count

    print(f"\nBatch Processing Results:")
    print(f"  Total: {len(messages)}")
    print(f"  ✓ Success: {success_count}")
    print(f"  ✗ Failed: {failure_count}")

    return success_count, failure_count


async def test_error_handling(consumer: NewsItConsumer):
    """Test error handling with malformed messages"""

    print("\n" + "="*60)
    print("TEST: Error Handling")
    print("="*60)

    # Test malformed JSON
    print("\n1. Testing malformed JSON message...")
    malformed_msg = get_malformed_sqs_message()
    result = await consumer.process_message(malformed_msg)
    print(f"   Result: {'✓ Handled gracefully' if result is False else '✗ Unexpected success'}")

    # Test missing fields
    print("\n2. Testing message with missing tenant_id...")
    missing_fields_msg = get_missing_fields_sqs_message()
    result = await consumer.process_message(missing_fields_msg)
    print(f"   Result: {'✓ Handled gracefully' if result is False else '✗ Unexpected success'}")


def display_sample_payloads():
    """Display sample SQS message payloads"""

    print("\n" + "="*60)
    print("SAMPLE SQS MESSAGE PAYLOADS")
    print("="*60)

    print("\n1. Simple SQS Message (Minimal)")
    print("-" * 60)
    simple_msg = get_sample_sqs_message_simple()
    print(json.dumps(simple_msg, indent=2))

    print("\n\n2. SQS Message with Metadata")
    print("-" * 60)
    metadata_msg = get_sample_sqs_message_with_metadata()
    print(json.dumps(metadata_msg, indent=2))

    print("\n\n3. SQS Message Body (Payload Only)")
    print("-" * 60)
    body = json.loads(simple_msg['Body'])
    print(json.dumps(body, indent=2))

    print("\n\n4. NewsIt SQS Message Schema")
    print("-" * 60)
    print("""
{
  "news_id": "string (required) - NewsIt news item ID",
  "tenant_id": "uuid (required) - Tenant UUID to route message to",
  "source": "string (default: newsit) - Source identifier",
  "metadata": {
    "trigger_time": "ISO datetime - When message was triggered",
    "trigger_source": "string - Source that triggered message",
    "priority": "string - Message priority (optional)",
    "is_breaking": "boolean - Breaking news flag (optional)",
    "category": "string - News category (optional)",
    "language": "string - Language code (optional)"
  }
}
    """)


# =====================================================
# Main Test Runner
# =====================================================

async def run_tests(tenant_id: str = None, news_id: str = None):
    """
    Run SQS message validation and processing tests

    Args:
        tenant_id: Optional tenant UUID to use in test messages
        news_id: Optional NewsIt news ID to use in test messages
    """

    print("\n" + "="*60)
    print("SQS MESSAGE VALIDATION AND TESTING TOOL")
    print("="*60)

    # Display sample payloads
    display_sample_payloads()

    # Check if imports are available
    if not IMPORTS_AVAILABLE:
        print("\n" + "="*60)
        print("IMPORTS NOT AVAILABLE")
        print("="*60)
        print("\n⚠️  Required modules not available.")
        print("   Full integration testing requires:")
        print("   - uv sync (to install dependencies)")
        print("   - .env configuration")
        print("\nFor now, sample payloads are displayed above.")
        return

    # Check if we should run processing tests
    if not tenant_id:
        print("\n" + "="*60)
        print("CONFIGURATION REQUIRED")
        print("="*60)
        print("\nTo test message processing, you need to provide:")
        print("  1. tenant_id - A valid tenant UUID from your database")
        print("  2. news_id - A valid NewsIt news item ID (optional)")
        print("\nUsage:")
        print("  python test_sqs_message.py <tenant_id> [news_id]")
        print("\nExample:")
        print("  python test_sqs_message.py 123e4567-e89b-12d3-a456-426614174000 newsit-12345")
        print("\nTo just view sample payloads without processing:")
        print("  python test_sqs_message.py --samples-only")
        return

    # Initialize consumer
    print("\n" + "="*60)
    print("INITIALIZING CONSUMER")
    print("="*60)

    try:
        consumer = NewsItConsumer()
        print("✓ Consumer initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize consumer: {e}")
        print("\nPlease check:")
        print("  1. AWS credentials are configured in .env")
        print("  2. SQS queue URL is configured")
        print("  3. NewsIt API credentials are configured")
        return

    # Create test messages with provided IDs
    test_news_id = news_id or "newsit-test-123456"

    # Test 1: Single message processing
    test_message = get_sample_sqs_message_simple()
    test_body = json.loads(test_message['Body'])
    test_body['tenant_id'] = tenant_id
    test_body['news_id'] = test_news_id
    test_message['Body'] = json.dumps(test_body)

    await test_single_message_processing(consumer, test_message)

    # Test 2: Error handling
    await test_error_handling(consumer)

    # Test 3: Batch processing (optional)
    print("\n" + "="*60)
    print("Would you like to test batch processing? (y/n)")
    print("Note: This will process 3 messages")
    print("="*60)

    # For automated testing, skip interactive prompt
    # Uncomment below for interactive mode:
    # response = input("Run batch test? (y/n): ")
    # if response.lower() == 'y':
    #     batch_messages = get_sample_sqs_message_batch()
    #     for msg in batch_messages:
    #         body = json.loads(msg['Body'])
    #         body['tenant_id'] = tenant_id
    #         msg['Body'] = json.dumps(body)
    #     await test_batch_message_processing(consumer, batch_messages)


def print_usage():
    """Print usage instructions"""
    print("""
SQS Message Validation and Testing Tool

USAGE:
  python test_sqs_message.py [OPTIONS]

OPTIONS:
  --samples-only              Display sample payloads without processing
  <tenant_id> [news_id]       Run tests with specified tenant and news ID

EXAMPLES:
  # View sample SQS message payloads
  python test_sqs_message.py --samples-only

  # Test with actual tenant and news ID
  python test_sqs_message.py 123e4567-e89b-12d3-a456-426614174000 newsit-12345

  # Test with just tenant ID (uses default test news ID)
  python test_sqs_message.py 123e4567-e89b-12d3-a456-426614174000

REQUIREMENTS:
  1. Configure .env file with:
     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - AWS_SQS_QUEUE_URL
     - AWS_SQS_REGION
     - NEWSIT_API_KEY
     - NEWSIT_API_URL

  2. Database with external_news_items table
  3. Valid tenant in database
  4. Valid NewsIt news item ID (optional)

OUTPUT:
  - Sample SQS message payloads
  - Message structure validation results
  - Message processing results
  - Error handling test results
    """)


if __name__ == "__main__":
    import sys

    # Parse command line arguments
    if len(sys.argv) == 1:
        print_usage()
        display_sample_payloads()
    elif '--samples-only' in sys.argv:
        display_sample_payloads()
    elif '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
    else:
        tenant_id = sys.argv[1] if len(sys.argv) > 1 else None
        news_id = sys.argv[2] if len(sys.argv) > 2 else None

        # Run async tests
        asyncio.run(run_tests(tenant_id, news_id))
