"""
WARNING: This script will DELETE ALL DATA from the database
Run with caution! This is for implementing Entity-Centric Sentiment Process v19.0
"""
import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

async def delete_all_data():
    """Delete all data from MongoDB collections"""
    
    # Connect to MongoDB
    mongo_url = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")
    client = AsyncIOMotorClient(mongo_url)
    db = client.smart_radar
    
    print(f"[{datetime.now()}] ⚠️  STARTING COMPLETE DATA DELETION...")
    print("This will delete ALL data from the following collections:")
    
    # Collections to delete
    collections = [
        'social_posts',
        'news_articles', 
        'response_logs',
        'threat_campaigns'
    ]
    
    total_deleted = 0
    
    for collection_name in collections:
        try:
            collection = db[collection_name]
            
            # Count documents before deletion
            count_before = await collection.count_documents({})
            print(f"  📊 {collection_name}: {count_before} documents")
            
            # Delete all documents
            result = await collection.delete_many({})
            deleted_count = result.deleted_count
            total_deleted += deleted_count
            
            print(f"  ✅ Deleted {deleted_count} documents from {collection_name}")
            
        except Exception as e:
            print(f"  ❌ Error deleting from {collection_name}: {e}")
    
    print(f"\n[{datetime.now()}] 🗑️  COMPLETE DATA DELETION FINISHED!")
    print(f"Total documents deleted: {total_deleted}")
    print("\n✨ Database is now clean and ready for Entity-Centric Sentiment Process v19.0")
    
    # Close connection
    client.close()

async def confirm_deletion():
    """Ask for confirmation before deletion"""
    print("⚠️  DANGER: Complete Data Deletion for v19.0 Implementation")
    print("This will permanently delete ALL existing data from:")
    print("  - social_posts")
    print("  - news_articles")
    print("  - response_logs")
    print("  - threat_campaigns")
    print()
    
    response = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if response == "DELETE ALL DATA":
        await delete_all_data()
    else:
        print("❌ Deletion cancelled. Exiting...")

if __name__ == "__main__":
    asyncio.run(confirm_deletion())