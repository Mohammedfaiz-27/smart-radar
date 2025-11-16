#!/usr/bin/env python3
"""
Standalone Facebook Data Collection Script
Collects 100 Facebook posts for DMK and ADMK clusters
Uses existing FacebookCollector without modifying any backend services or schemas
"""
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Set environment variables
os.environ["MONGODB_URL"] = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Add backend to path
sys.path.append('/Users/Samrt radar Final /backend')

from app.collectors.facebook_collector import FacebookCollector
from app.models.cluster import PlatformConfig
from app.models.posts_table import Platform
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class StandaloneFacebookCollector:
    """Standalone Facebook collector that preserves all existing schemas"""
    
    def __init__(self):
        self.collector = FacebookCollector()
        self.mongodb_url = os.getenv('MONGODB_URL', 'mongodb://admin:password@localhost:27017/smart_radar?authSource=admin')
        self.client = None
        self.db = None
        
    async def initialize(self):
        """Initialize database connection"""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client['smart_radar']
        print("✅ Connected to MongoDB")
        
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✅ Database connection closed")
    
    async def get_cluster_info(self, cluster_id: ObjectId) -> Dict[str, Any]:
        """Get cluster information from database"""
        cluster = await self.db.clusters.find_one({"_id": cluster_id})
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        return cluster
    
    async def save_raw_data(self, raw_data: Dict[str, Any], cluster_id: str, keyword: str) -> str:
        """Save raw API response to raw_data collection (preserves existing schema)"""
        raw_record = {
            "platform": "Facebook",  # Using existing RawDataPlatform enum value
            "cluster_id": cluster_id,
            "keyword": keyword,
            "raw_json": raw_data,
            "api_endpoint": self.collector.get_api_endpoint(),
            "api_params": {},
            "processing_status": "pending",  # Using existing ProcessingStatus enum
            "fetched_at": datetime.utcnow(),
            "response_size_bytes": len(json.dumps(raw_data)),
            "has_next_page": False,
            "posts_extracted": 0
        }
        
        result = await self.db.raw_data.insert_one(raw_record)
        print(f"💾 Saved raw data: {result.inserted_id}")
        return str(result.inserted_id)
    
    async def save_processed_post(self, post_data) -> str:
        """Save processed post to posts_table collection (preserves existing schema)"""
        # Convert PostCreate model to dict and add required fields
        post_dict = post_data.dict()
        post_dict["fetched_at"] = datetime.utcnow()
        
        # Ensure platform is saved as string (existing schema format)
        post_dict["platform"] = "Facebook"
        
        result = await self.db.posts_table.insert_one(post_dict)
        print(f"📝 Saved processed post: {result.inserted_id}")
        return str(result.inserted_id)
    
    async def collect_for_cluster(self, cluster_id: ObjectId, max_posts: int = 100):
        """Collect Facebook posts for a specific cluster"""
        try:
            # Get cluster information
            cluster = await self.get_cluster_info(cluster_id)
            cluster_name = cluster.get('name', 'Unknown')
            keywords = cluster.get('keywords', [])
            
            print(f"\n🎯 Collecting Facebook posts for {cluster_name} cluster")
            print(f"📋 Keywords: {keywords}")
            print(f"🎛️ Target: {max_posts} posts")
            
            # Create platform config (preserves existing PlatformConfig schema)
            config = PlatformConfig(
                location="Tamil Nadu",
                min_engagement=0,  # Start with any engagement
                language_filter=["Tamil", "English"]
            )
            
            total_collected = 0
            total_raw_data_saved = 0
            
            # Limit to first 3 keywords to avoid rate limits
            for keyword in keywords[:3]:  
                if total_collected >= max_posts:
                    break
                    
                print(f"\n🔍 Searching Facebook for: '{keyword}'")
                
                posts_for_keyword = 0
                try:
                    # Use existing FacebookCollector.search method (no schema changes)
                    async for raw_post in self.collector.search(keyword, config, max_results=50):
                        try:
                            # Save raw data using existing schema
                            raw_id = await self.save_raw_data(raw_post, str(cluster_id), keyword)
                            total_raw_data_saved += 1
                            
                            # Parse using existing FacebookCollector.parse_post method
                            processed_post = self.collector.parse_post(raw_post, str(cluster_id))
                            post_id = await self.save_processed_post(processed_post)
                            
                            posts_for_keyword += 1
                            total_collected += 1
                            
                            print(f"✅ Post {posts_for_keyword}: {processed_post.author_username} - {processed_post.post_text[:50]}...")
                            
                            if total_collected >= max_posts:
                                break
                                
                        except Exception as e:
                            print(f"❌ Error processing post: {e}")
                            continue
                            
                except Exception as e:
                    print(f"❌ Error searching for keyword '{keyword}': {e}")
                    continue
                
                print(f"📊 Collected {posts_for_keyword} posts for keyword '{keyword}'")
                
                # Small delay between keywords
                await asyncio.sleep(2)
            
            print(f"\n🎉 Collection complete for {cluster_name}:")
            print(f"   📊 Total raw data records: {total_raw_data_saved}")
            print(f"   📝 Total processed posts: {total_collected}")
            
            return total_collected
            
        except Exception as e:
            print(f"❌ Error collecting for cluster {cluster_id}: {e}")
            import traceback
            traceback.print_exc()
            return 0


async def main():
    """Main function to collect Facebook data for DMK and ADMK clusters"""
    print("🚀 Starting Standalone Facebook Data Collection")
    print("⚠️  SAFE MODE: Preserves all existing database schemas")
    print(f"⏰ Start time: {datetime.now()}")
    
    collector = StandaloneFacebookCollector()
    
    try:
        await collector.initialize()
        
        # Show existing data count before collection
        existing_raw = await collector.db.raw_data.count_documents({})
        existing_posts = await collector.db.posts_table.count_documents({})
        existing_fb_raw = await collector.db.raw_data.count_documents({"platform": "Facebook"})
        existing_fb_posts = await collector.db.posts_table.count_documents({"platform": "Facebook"})
        
        print(f"\n📊 BEFORE COLLECTION:")
        print(f"   💾 Total raw_data: {existing_raw} (Facebook: {existing_fb_raw})")
        print(f"   📝 Total posts_table: {existing_posts} (Facebook: {existing_fb_posts})")
        
        # Define target clusters using actual ObjectIds from database
        clusters = [
            {"id": ObjectId("68d102c95b3f32b5abd27a86"), "name": "DMK"},
            {"id": ObjectId("68d102c95b3f32b5abd27a87"), "name": "ADMK"}
        ]
        
        total_posts = 0
        
        # Collect for each cluster
        for cluster in clusters:
            cluster_posts = await collector.collect_for_cluster(
                cluster_id=cluster["id"],
                max_posts=100
            )
            total_posts += cluster_posts
            
            # Delay between clusters
            await asyncio.sleep(5)
        
        # Show final statistics
        final_raw = await collector.db.raw_data.count_documents({})
        final_posts = await collector.db.posts_table.count_documents({})
        final_fb_raw = await collector.db.raw_data.count_documents({"platform": "Facebook"})
        final_fb_posts = await collector.db.posts_table.count_documents({"platform": "Facebook"})
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   📱 Platform: Facebook")
        print(f"   📊 Total posts collected: {total_posts}")
        print(f"   🏁 End time: {datetime.now()}")
        
        print(f"\n📊 AFTER COLLECTION:")
        print(f"   💾 Total raw_data: {final_raw} (Facebook: {final_fb_raw})")
        print(f"   📝 Total posts_table: {final_posts} (Facebook: {final_fb_posts})")
        
        print(f"\n🔢 DATA ADDED (NEW ENTRIES ONLY):")
        print(f"   💾 New raw_data entries: {final_raw - existing_raw}")
        print(f"   📝 New posts: {final_posts - existing_posts}")
        print(f"   📱 New Facebook raw entries: {final_fb_raw - existing_fb_raw}")
        print(f"   📱 New Facebook posts: {final_fb_posts - existing_fb_posts}")
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await collector.close()


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv('FACEBOOK_RAPIDAPI_KEY'):
        print("❌ FACEBOOK_RAPIDAPI_KEY environment variable not set")
        print("Please set it in backend/.env file")
        sys.exit(1)
    
    # Run the collection
    asyncio.run(main())