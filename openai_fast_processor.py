#!/usr/bin/env python3
"""
Ultra-Fast OpenAI Parallel Processor
Processes all raw data and posts using OpenAI API with aggressive parallelization
Target: Process all data within 10 minutes
"""
import asyncio
import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Set MongoDB URL
MONGODB_URL = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Add backend to path
sys.path.append('/Users/Samrt radar Final /backend')

class UltraFastProcessor:
    """Ultra-fast parallel processor using OpenAI"""
    
    def __init__(self, workers: int = 20, batch_size: int = 50):
        self.workers = workers
        self.batch_size = batch_size
        self.processed_count = 0
        self.stored_count = 0
        self.error_count = 0
        self.tamil_count = 0
        self.start_time = time.time()
        
        # Import services
        from app.services.openai_processing_service import OpenAIProcessingService
        from app.models.raw_data import RawDataInDB
        
        self.openai_service = OpenAIProcessingService()
        self.RawDataInDB = RawDataInDB
        
    async def process_all_data(self):
        """Process all raw data and posts in parallel"""
        print("🚀 Starting Ultra-Fast OpenAI Processing...")
        
        # Setup database connection
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client.smart_radar
        self.raw_collection = self.db.raw_data
        self.posts_collection = self.db.posts_table
        
        # Get counts
        total_raw = await self.raw_collection.count_documents({})
        pending_raw = await self.raw_collection.count_documents({
            'processing_status': {'$nin': ['PROCESSED', 'FAILED']}
        })
        posts_total = await self.posts_collection.count_documents({})
        posts_without_intel = await self.posts_collection.count_documents({
            'intelligence': {'$exists': False}
        })
        
        print(f"📊 Processing Status:")
        print(f"   Raw data: {pending_raw:,} pending / {total_raw:,} total")
        print(f"   Posts: {posts_without_intel:,} need intelligence / {posts_total:,} total")
        print(f"   Workers: {self.workers}")
        print(f"   Batch size: {self.batch_size}")
        
        # Create semaphore for controlling concurrency
        semaphore = asyncio.Semaphore(self.workers)
        
        # Start parallel processing
        tasks = []
        
        # Task 1: Process raw data
        if pending_raw > 0:
            tasks.append(self.process_raw_data_parallel(semaphore))
        
        # Task 2: Process posts intelligence
        if posts_without_intel > 0:
            tasks.append(self.process_posts_intelligence_parallel(semaphore))
        
        if not tasks:
            print("✅ No data to process!")
            await self.client.close()
            return
        
        # Execute all tasks in parallel
        await asyncio.gather(*tasks)
        
        # Final statistics
        await self.print_final_stats()
        await self.client.close()
    
    async def process_raw_data_parallel(self, semaphore: asyncio.Semaphore):
        """Process raw data with parallel workers"""
        print("📦 Starting raw data processing...")
        
        while True:
            # Get batch of unprocessed raw data (including FAILED ones for retry)
            batch = await self.raw_collection.find({
                'processing_status': {'$nin': ['PROCESSED']}
            }).limit(self.batch_size).to_list(None)
            
            if not batch:
                print("✅ Raw data processing complete!")
                break
            
            print(f"📦 Processing raw data batch of {len(batch)} items...")
            
            # Process batch in parallel
            tasks = []
            for raw_doc in batch:
                task = self.process_single_raw_data(raw_doc, semaphore)
                tasks.append(task)
            
            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            batch_stored = 0
            batch_errors = 0
            batch_tamil = 0
            
            for result in results:
                if isinstance(result, Exception):
                    batch_errors += 1
                    self.error_count += 1
                elif result:
                    self.processed_count += 1
                    if result.get('stored'):
                        batch_stored += 1
                        self.stored_count += 1
                    if result.get('is_tamil'):
                        batch_tamil += 1
                        self.tamil_count += 1
            
            elapsed = time.time() - self.start_time
            rate = self.processed_count / elapsed if elapsed > 0 else 0
            
            print(f"📊 Raw batch: {batch_stored} stored, {batch_tamil} Tamil, {batch_errors} errors (Rate: {rate:.1f}/sec)")
    
    async def process_posts_intelligence_parallel(self, semaphore: asyncio.Semaphore):
        """Process posts intelligence with parallel workers"""
        print("🧠 Starting posts intelligence processing...")
        
        while True:
            # Get batch of posts without intelligence
            batch = await self.posts_collection.find({
                'intelligence': {'$exists': False}
            }).limit(self.batch_size).to_list(None)
            
            if not batch:
                print("✅ Posts intelligence processing complete!")
                break
            
            print(f"🧠 Processing intelligence batch of {len(batch)} posts...")
            
            # Process batch in parallel
            tasks = []
            for post_doc in batch:
                task = self.process_single_post_intelligence(post_doc, semaphore)
                tasks.append(task)
            
            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            batch_updated = sum(1 for r in results if r and not isinstance(r, Exception))
            batch_errors = sum(1 for r in results if isinstance(r, Exception))
            
            elapsed = time.time() - self.start_time
            rate = self.processed_count / elapsed if elapsed > 0 else 0
            
            print(f"📊 Intelligence batch: {batch_updated} updated, {batch_errors} errors (Rate: {rate:.1f}/sec)")
    
    async def process_single_raw_data(self, raw_doc: Dict[str, Any], semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        """Process a single raw data entry"""
        async with semaphore:
            try:
                # Convert to RawDataInDB model
                raw_data = self.RawDataInDB(
                    id=str(raw_doc["_id"]),
                    platform=raw_doc["platform"],
                    cluster_id=raw_doc["cluster_id"],
                    keyword=raw_doc["keyword"],
                    raw_json=raw_doc["raw_json"],
                    api_endpoint=raw_doc.get("api_endpoint", ""),
                    api_params=raw_doc.get("api_params", {}),
                    processing_status=raw_doc.get("processing_status", "PENDING"),
                    response_size_bytes=raw_doc.get("response_size_bytes", 0),
                    posts_extracted=raw_doc.get("posts_extracted", 0),
                    fetched_at=raw_doc.get("fetched_at", datetime.utcnow()),
                    processed_at=raw_doc.get("processed_at")
                )
                
                # Process with OpenAI service
                post = await self.openai_service.process_raw_data(raw_data)
                
                result = {'stored': False, 'is_tamil': False}
                
                if post:
                    # Check if post already exists
                    existing = await self.posts_collection.find_one({
                        "platform": post.platform.value,
                        "platform_post_id": post.platform_post_id
                    })
                    
                    if not existing:
                        # Convert to dict and add timestamps
                        post_dict = post.model_dump()
                        post_dict["created_at"] = datetime.utcnow()
                        post_dict["updated_at"] = datetime.utcnow()
                        post_dict["fetched_at"] = raw_data.fetched_at
                        
                        # Store in posts_table
                        await self.posts_collection.insert_one(post_dict)
                        result['stored'] = True
                        
                        # Check if Tamil content
                        if post.language and ("Tamil" in post.language or "tamil" in post.language.lower() or "mixed" in post.language.lower()):
                            result['is_tamil'] = True
                    
                    # Mark raw data as processed
                    await self.raw_collection.update_one(
                        {"_id": raw_doc["_id"]},
                        {"$set": {
                            "processing_status": "PROCESSED",
                            "processed_at": datetime.utcnow(),
                            "posts_extracted": 1
                        }}
                    )
                else:
                    # Mark as failed
                    await self.raw_collection.update_one(
                        {"_id": raw_doc["_id"]},
                        {"$set": {
                            "processing_status": "FAILED",
                            "processed_at": datetime.utcnow()
                        }}
                    )
                
                return result
                
            except Exception as e:
                print(f"❌ Error processing raw data {raw_doc.get('_id')}: {e}")
                
                # Mark as failed
                try:
                    await self.raw_collection.update_one(
                        {"_id": raw_doc["_id"]},
                        {"$set": {
                            "processing_status": "FAILED",
                            "processed_at": datetime.utcnow(),
                            "error_message": str(e)
                        }}
                    )
                except:
                    pass
                
                raise e
    
    async def process_single_post_intelligence(self, post_doc: Dict[str, Any], semaphore: asyncio.Semaphore) -> bool:
        """Process intelligence for a single post"""
        async with semaphore:
            try:
                # Get intelligence from OpenAI
                intelligence = await self.openai_service.process_post_intelligence(post_doc)
                
                if intelligence:
                    # Update post with intelligence
                    await self.posts_collection.update_one(
                        {"_id": post_doc["_id"]},
                        {"$set": {
                            "intelligence": intelligence,
                            "updated_at": datetime.utcnow()
                        }}
                    )
                    return True
                else:
                    return False
                    
            except Exception as e:
                print(f"❌ Error processing post intelligence {post_doc.get('_id')}: {e}")
                return False
    
    async def print_final_stats(self):
        """Print final processing statistics"""
        total_duration = time.time() - self.start_time
        overall_rate = self.processed_count / total_duration if total_duration > 0 else 0
        
        # Get final counts
        final_posts = await self.posts_collection.count_documents({})
        tamil_posts = await self.posts_collection.count_documents({
            "language": {"$regex": "tamil|Tamil|mixed", "$options": "i"}
        })
        posts_with_intel = await self.posts_collection.count_documents({
            "intelligence": {"$exists": True}
        })
        raw_processed = await self.raw_collection.count_documents({
            'processing_status': 'PROCESSED'
        })
        raw_total = await self.raw_collection.count_documents({})
        
        print(f"\n🎉 Ultra-Fast Processing Complete!")
        print(f"⏱️  Processing Time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"⚡ Processing Rate: {overall_rate:.1f} items/second")
        print(f"📊 Items Processed: {self.processed_count:,}")
        print(f"💾 Posts Stored: {self.stored_count:,}")
        print(f"🇮🇳 Tamil Posts: {self.tamil_count:,}")
        print(f"❌ Errors: {self.error_count:,}")
        
        print(f"\n📊 Final Database Status:")
        print(f"   Total posts: {final_posts:,}")
        print(f"   Tamil posts: {tamil_posts:,}")
        print(f"   Posts with intelligence: {posts_with_intel:,}")
        print(f"   Raw data processed: {raw_processed:,}/{raw_total:,} ({(raw_processed/raw_total)*100:.1f}%)")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Ultra-Fast OpenAI Processor")
    parser.add_argument("--workers", type=int, default=20, help="Number of parallel workers")
    parser.add_argument("--batch", type=int, default=50, help="Batch size")
    
    args = parser.parse_args()
    
    processor = UltraFastProcessor(workers=args.workers, batch_size=args.batch)
    await processor.process_all_data()

if __name__ == "__main__":
    # Check if OpenAI key is configured
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-openai_api_key_here":
        print("❌ ERROR: OPENAI_API_KEY not configured!")
        print("Please set a valid OpenAI API key in the .env file")
        sys.exit(1)
    
    asyncio.run(main())