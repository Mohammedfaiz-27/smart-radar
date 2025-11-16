"""
Cleanup script to remove non-(Tamil/English/Tanglish) posts from posts_table collection
Only keeps: Tamil, English, Tanglish, and Mixed language posts
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def cleanup_non_english_posts():
    """Remove posts that are not Tamil, English, or Tanglish from posts_table"""

    # Connect to MongoDB
    mongo_url = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")
    client = AsyncIOMotorClient(mongo_url)
    db = client.smart_radar
    posts_table = db.posts_table

    print("🔍 Analyzing posts by language...")

    # Get language distribution
    pipeline = [
        {"$group": {"_id": "$language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    lang_stats = await posts_table.aggregate(pipeline).to_list(length=None)

    print("\n📊 Current language distribution:")
    for stat in lang_stats:
        lang = stat["_id"] or "null"
        count = stat["count"]
        print(f"   {lang}: {count} posts")

    # Define languages to keep (Tamil, English, Tanglish, Mixed)
    languages_to_keep = [
        'en', 'english', 'English', 'EN',
        'Tamil', 'tamil', 'ta',
        'Tanglish', 'tanglish',
        'Mixed', 'mixed',
        None, 'unknown', 'Unknown'
    ]

    # Count posts to delete
    delete_query = {
        "language": {
            "$exists": True,
            "$nin": languages_to_keep
        }
    }

    count_to_delete = await posts_table.count_documents(delete_query)

    if count_to_delete == 0:
        print("\n✅ No unwanted language posts found. Database is clean!")
        print("   Keeping: Tamil, English, Tanglish, Mixed")
        return

    print(f"\n🗑️  Found {count_to_delete} posts to delete (non-Tamil/English/Tanglish)")
    print("\nLanguages to be removed:")

    # Show what will be deleted
    delete_langs = await posts_table.aggregate([
        {"$match": delete_query},
        {"$group": {"_id": "$language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=None)

    for stat in delete_langs:
        print(f"   {stat['_id']}: {stat['count']} posts")

    # Auto-confirm and delete
    print(f"\n⚠️  Proceeding to delete {count_to_delete} unwanted language posts...")
    print("   Keeping only: Tamil, English, Tanglish, Mixed")

    # Delete unwanted posts
    print("\n🧹 Deleting posts...")
    result = await posts_table.delete_many(delete_query)

    print(f"✅ Deleted {result.deleted_count} non-English posts")

    # Show final statistics
    total_remaining = await posts_table.count_documents({})
    print(f"\n📊 Remaining posts: {total_remaining}")

    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_non_english_posts())
