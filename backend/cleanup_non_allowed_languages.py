"""
Cleanup script to delete posts in non-allowed languages
Only keeps English, Tamil, and Tanglish posts
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup_languages():
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.smart_radar

    # Allowed languages
    allowed_languages = ['en', 'english', 'tamil', 'tanglish', 'mixed', 'unknown', None]

    print("🔍 Finding posts in non-allowed languages...")

    # Find posts with non-allowed languages
    query = {
        "language": {
            "$exists": True,
            "$nin": allowed_languages,
            "$regex": "^(?!en$|english$|tamil$|tanglish$|mixed$|unknown$)",
            "$options": "i"
        }
    }

    # Count posts to delete
    count = await db.posts_table.count_documents(query)
    print(f"📊 Found {count} posts in non-allowed languages")

    if count == 0:
        print("✅ No posts to delete!")
        client.close()
        return

    # Show sample posts
    print("\n📋 Sample posts to be deleted:")
    async for post in db.posts_table.find(query).limit(5):
        lang = post.get("language", "Unknown")
        content = post.get("content", post.get("post_text", ""))[:60]
        print(f"   - {lang}: {content}...")

    # Confirm deletion
    print(f"\n⚠️  About to delete {count} posts in languages other than English/Tamil/Tanglish")
    print("   Press Ctrl+C to cancel, or Enter to continue...")
    input()

    # Delete posts
    result = await db.posts_table.delete_many(query)
    print(f"✅ Deleted {result.deleted_count} posts from posts_table")

    # Also cleanup raw_data
    raw_count = await db.raw_data.count_documents(query)
    if raw_count > 0:
        raw_result = await db.raw_data.delete_many(query)
        print(f"✅ Deleted {raw_result.deleted_count} raw_data entries")

    client.close()
    print("\n🎉 Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup_languages())
