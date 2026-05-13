"""
Integration Test for External News Publishing Flow
Tests the complete flow: External News -> Post Record -> Publishing
"""

import asyncio
import sys
from uuid import UUID
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/home/vinothkumarravi/idxp/Codes/smartpost/smartpost/omnipush-backend')

from services.external_news_service import ExternalNewsService
from core.database import get_database


async def test_publish_flow():
    """Test the external news publishing flow"""

    print("=" * 60)
    print("External News Publishing Integration Test")
    print("=" * 60)

    # Initialize service
    service = ExternalNewsService()
    db = get_database()

    # Test parameters - replace with actual values from your database
    # You'll need to:
    # 1. Create or use existing external news item
    # 2. Use valid tenant_id, user_id, channel_group_id

    print("\n[Step 1] Checking test prerequisites...")

    # Check if we have any external news items
    try:
        news_result = db.client.table('external_news_items')\
            .select('*')\
            .eq('approval_status', 'approved')\
            .limit(1)\
            .execute()

        if not news_result.data:
            print("❌ No approved external news items found.")
            print("   Please create a test news item first:")
            print("   1. Run newsit_consumer.py to fetch news")
            print("   2. Approve a news item via API or database")
            return

        news_item = news_result.data[0]
        news_id = UUID(news_item['id'])
        tenant_id = UUID(news_item['tenant_id'])

        print(f"✓ Found approved news item: {news_item['title'][:50]}...")
        print(f"  News ID: {news_id}")
        print(f"  Tenant ID: {tenant_id}")

    except Exception as e:
        print(f"❌ Error checking news items: {e}")
        return

    # Check for channel groups
    try:
        cg_result = db.client.table('channel_groups')\
            .select('id, name, social_account_ids')\
            .eq('tenant_id', str(tenant_id))\
            .limit(1)\
            .execute()

        if not cg_result.data or not cg_result.data[0].get('social_account_ids'):
            print("❌ No channel groups with social accounts found.")
            print("   Please create a channel group with social accounts first.")
            return

        channel_group = cg_result.data[0]
        channel_group_id = UUID(channel_group['id'])

        print(f"✓ Found channel group: {channel_group['name']}")
        print(f"  Channel Group ID: {channel_group_id}")
        print(f"  Social Accounts: {len(channel_group['social_account_ids'])} accounts")

    except Exception as e:
        print(f"❌ Error checking channel groups: {e}")
        return

    # Get a user from tenant
    try:
        user_result = db.client.table('users')\
            .select('id')\
            .eq('tenant_id', str(tenant_id))\
            .limit(1)\
            .execute()

        if not user_result.data:
            print("❌ No users found for tenant.")
            return

        user_id = UUID(user_result.data[0]['id'])
        print(f"✓ Found user ID: {user_id}")

    except Exception as e:
        print(f"❌ Error checking users: {e}")
        return

    print("\n[Step 2] Testing publish_to_channel_groups...")
    print(f"  Publishing news '{news_item['title'][:40]}...'")
    print(f"  To channel group: {channel_group['name']}")

    try:
        # Call the publish method
        result = await service.publish_to_channel_groups(
            news_id=news_id,
            channel_group_ids=[channel_group_id],
            tenant_id=tenant_id,
            initiated_by=user_id,
            selected_language='en'
        )

        print("\n[Step 3] Publishing Results:")
        print(f"  Success: {result.get('success')}")
        print(f"  Total Publications: {len(result.get('publications', []))}")
        print(f"  Errors: {len(result.get('errors', []))}")

        if result.get('errors'):
            print("\n  Errors encountered:")
            for error in result['errors']:
                print(f"    - {error}")

        # Check if Post record was created
        if result.get('publications'):
            pub = result['publications'][0]
            if pub.get('post_id'):
                post_id = pub['post_id']
                print(f"\n[Step 4] Verifying Post Record...")
                print(f"  Post ID: {post_id}")

                # Fetch the post
                post_result = db.client.table('posts')\
                    .select('*')\
                    .eq('id', post_id)\
                    .single()\
                    .execute()

                if post_result.data:
                    post = post_result.data
                    print(f"  ✓ Post record created successfully!")
                    print(f"  Title: {post.get('title')}")
                    print(f"  Status: {post.get('status')}")
                    print(f"  External News ID: {post.get('external_news_id')}")
                    print(f"  Channel Group ID: {post.get('channel_group_id')}")

                    if post.get('publish_results'):
                        results = post['publish_results']
                        print(f"  Publish Results:")
                        print(f"    - Total Accounts: {results.get('total_accounts', 0)}")
                        print(f"    - Success Count: {results.get('success_count', 0)}")
                        print(f"    - Failure Count: {results.get('failure_count', 0)}")

                    print("\n✓ Integration Test PASSED!")
                    print("  External News -> Post Record -> Publishing flow is working correctly.")
                else:
                    print("  ❌ Post record not found!")
            else:
                print("\n  ⚠ No post_id in publication record")
        else:
            print("\n  ⚠ No publications created")

    except Exception as e:
        print(f"\n❌ Error during publishing: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_publish_flow())
