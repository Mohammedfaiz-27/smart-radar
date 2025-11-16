#!/usr/bin/env python3
"""
Facebook-only Data Collection Script
Fetches Facebook data for all clusters specifically
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Set environment variables
os.environ["MONGODB_URL"] = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Add backend to Python path
sys.path.append('/Users/Samrt radar Final /backend')

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.services.data_collection_service import DataCollectionService
from app.services.cluster_service import ClusterService

async def fetch_facebook_data():
    """Safely collect Facebook data for DMK and ADMK clusters - ONLY ADDS NEW DATA"""
    print("🚀 Starting Facebook Data Collection for DMK and ADMK")
    print("⚠️  SAFE MODE: This script only ADDS new data, never deletes existing data")
    print(f"⏰ Start time: {datetime.now()}")
    
    # Setup database connection
    client = AsyncIOMotorClient(os.environ["MONGODB_URL"])
    db = client.smart_radar
    
    try:
        # Show existing data count before collection
        existing_raw = await db.raw_data.count_documents({})
        existing_posts = await db.posts_table.count_documents({})
        existing_fb_raw = await db.raw_data.count_documents({"platform": "Facebook"})
        existing_fb_posts = await db.posts_table.count_documents({"platform": "Facebook"})
        
        print(f"\n📊 BEFORE COLLECTION:")
        print(f"   💾 Total raw_data: {existing_raw} (Facebook: {existing_fb_raw})")
        print(f"   📝 Total posts_table: {existing_posts} (Facebook: {existing_fb_posts})")
        
        # Target specific clusters - DMK and ADMK only (using ObjectId)
        target_clusters = [
            {"id": ObjectId("68d102c95b3f32b5abd27a86"), "name": "DMK"},
            {"id": ObjectId("68d102c95b3f32b5abd27a87"), "name": "ADMK"}
        ]
        
        # Initialize data collection service
        async with DataCollectionService() as collection_service:
            # Check if Facebook is configured
            if not collection_service.facebook_rapidapi_key:
                print("❌ Facebook API key not configured!")
                return
            
            print("✅ Facebook API configured")
            
            # Process only DMK and ADMK clusters
            total_new_posts = 0
            for i, cluster_info in enumerate(target_clusters, 1):
                print(f"\n📦 Processing {cluster_info['name']} cluster ({i}/{len(target_clusters)})")
                
                # Get cluster details from database
                cluster_doc = await db.clusters.find_one({"_id": cluster_info["id"]})
                if not cluster_doc:
                    print(f"   ❌ Cluster {cluster_info['name']} not found in database!")
                    continue
                
                keywords = cluster_doc.get('keywords', [])
                print(f"   📋 Keywords: {keywords}")
                
                try:
                    # Collect Facebook posts only for this cluster
                    # This uses DataCollectionService which only INSERTS new data
                    post_ids = await collection_service.collect_posts_for_cluster(
                        cluster_id=str(cluster_info["id"]),  # Convert ObjectId to string
                        keywords=keywords,
                        platforms=["facebook"]  # Facebook only
                    )
                    
                    cluster_posts = len(post_ids) if post_ids else 0
                    total_new_posts += cluster_posts
                    
                    print(f"   ✅ Collected {cluster_posts} new Facebook posts")
                    
                    # Small delay between clusters to avoid rate limiting
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ Error collecting data for cluster {cluster_info['name']}: {e}")
                    continue
        
        # Show final statistics - only new data added
        print(f"\n🎉 Facebook Collection Complete!")
        print(f"📊 New Facebook posts collected: {total_new_posts}")
        
        # Verify database counts AFTER collection
        final_raw = await db.raw_data.count_documents({})
        final_posts = await db.posts_table.count_documents({})
        final_fb_raw = await db.raw_data.count_documents({"platform": "Facebook"})
        final_fb_posts = await db.posts_table.count_documents({"platform": "Facebook"})
        
        print(f"\n📊 AFTER COLLECTION:")
        print(f"   💾 Total raw_data: {final_raw} (Facebook: {final_fb_raw})")
        print(f"   📝 Total posts_table: {final_posts} (Facebook: {final_fb_posts})")
        
        print(f"\n🔢 DATA ADDED:")
        print(f"   💾 New raw_data entries: {final_raw - existing_raw}")
        print(f"   📝 New posts: {final_posts - existing_posts}")
        print(f"   📱 New Facebook raw entries: {final_fb_raw - existing_fb_raw}")
        print(f"   📱 New Facebook posts: {final_fb_posts - existing_fb_posts}")
        
    except Exception as e:
        print(f"❌ Error during Facebook collection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

async def main():
    """Main function"""
    await fetch_facebook_data()

if __name__ == "__main__":
    asyncio.run(main())