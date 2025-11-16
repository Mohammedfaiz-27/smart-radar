#!/usr/bin/env python3
"""
Script to delete posts in languages other than English and Tamil
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

from app.core.database import connect_to_mongo, close_mongo_connection
from motor.motor_asyncio import AsyncIOMotorClient

# Languages to KEEP (English/Tamil relevant)
KEEP_LANGUAGES = {
    'Tamil',
    'English', 
    'Mixed',
    'Tanglish'
}

async def cleanup_non_english_tamil_posts():
    """Delete posts in languages other than English and Tamil"""
    try:
        await connect_to_mongo()
        
        # Get MongoDB client
        client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
        db = client.smart_radar
        
        print("🔍 Analyzing current language distribution...")
        
        # First, show current distribution
        pipeline = [
            {'$group': {'_id': '$language', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        languages_to_delete = []
        total_to_delete = 0
        total_to_keep = 0
        
        print("\nCurrent language distribution:")
        async for result in db.posts_table.aggregate(pipeline):
            language = result['_id']
            count = result['count']
            
            if language in KEEP_LANGUAGES:
                print(f"  ✅ KEEP: {language} - {count} posts")
                total_to_keep += count
            else:
                print(f"  ❌ DELETE: {language} - {count} posts")
                languages_to_delete.append(language)
                total_to_delete += count
        
        print(f"\n📊 Summary:")
        print(f"  Posts to keep: {total_to_keep}")
        print(f"  Posts to delete: {total_to_delete}")
        print(f"  Languages to delete: {languages_to_delete}")
        
        if total_to_delete == 0:
            print("✅ No posts need to be deleted!")
            return
        
        # Confirm deletion
        print(f"\n⚠️  This will permanently delete {total_to_delete} posts in {len(languages_to_delete)} languages.")
        print("Languages that will be deleted:", languages_to_delete)
        print("\n✅ Proceeding with deletion as requested...")
        
        print(f"\n🗑️  Deleting posts in non-English/Tamil languages...")
        
        # Delete posts not in keep languages
        delete_filter = {'language': {'$nin': list(KEEP_LANGUAGES)}}
        result = await db.posts_table.delete_many(delete_filter)
        
        print(f"✅ Deleted {result.deleted_count} posts")
        
        # Show final distribution
        print(f"\n📊 Final language distribution:")
        async for result in db.posts_table.aggregate(pipeline):
            language = result['_id']
            count = result['count']
            print(f"  {language}: {count} posts")
        
        # Check total remaining
        total_remaining = await db.posts_table.count_documents({})
        print(f"\nTotal posts remaining: {total_remaining}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_mongo_connection()
        print("\n✅ Disconnected from MongoDB")

def main():
    """Main entry point"""
    print("🧹 Language Cleanup Tool")
    print("This tool will delete posts in languages other than English and Tamil")
    print("=" * 60)
    
    asyncio.run(cleanup_non_english_tamil_posts())

if __name__ == "__main__":
    main()