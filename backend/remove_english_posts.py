"""
Script to remove English posts from posts_table collection, keeping only Tamil content
"""
import asyncio
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

def is_tamil_content(text):
    """
    Check if text contains Tamil characters
    Tamil Unicode range: \u0B80-\u0BFF
    """
    if not text:
        return False

    tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
    tamil_chars = len(tamil_pattern.findall(text))

    # If at least 20% of non-space characters are Tamil, consider it Tamil content
    non_space_chars = len(text.replace(' ', ''))
    if non_space_chars == 0:
        return False

    tamil_percentage = (tamil_chars / non_space_chars) * 100
    return tamil_percentage >= 15  # At least 15% Tamil characters

async def remove_english_posts():
    """Remove posts that don't contain Tamil content"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.smart_radar
    posts_table = db.posts_table

    print("🔍 Analyzing posts_table collection...")

    # Get all posts
    total_count = await posts_table.count_documents({})
    print(f"📊 Total posts in collection: {total_count}")

    # Find English posts (posts without Tamil content)
    english_posts = []
    tamil_posts = []

    cursor = posts_table.find({})
    async for post in cursor:
        content = post.get('content', '') or post.get('post_text', '')
        title = post.get('title', '')
        combined_text = f"{title} {content}"

        if is_tamil_content(combined_text):
            tamil_posts.append(post['_id'])
        else:
            english_posts.append(post['_id'])

    print(f"✅ Tamil posts found: {len(tamil_posts)}")
    print(f"❌ English posts found: {len(english_posts)}")

    if len(english_posts) == 0:
        print("✨ No English posts to remove!")
        client.close()
        return

    # Confirm deletion
    print(f"\n⚠️  About to delete {len(english_posts)} English posts")
    print("This will keep only Tamil content in the database.")

    # Delete English posts
    result = await posts_table.delete_many({
        '_id': {'$in': english_posts}
    })

    print(f"\n✅ Deleted {result.deleted_count} English posts")

    # Verify final count
    final_count = await posts_table.count_documents({})
    print(f"📊 Remaining posts (Tamil only): {final_count}")

    client.close()

if __name__ == "__main__":
    print("=" * 60)
    print("REMOVING ENGLISH POSTS FROM posts_table")
    print("Keeping only Tamil content")
    print("=" * 60)
    asyncio.run(remove_english_posts())
    print("\n✨ Done!")
