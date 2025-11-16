#!/usr/bin/env python3
"""
Fast raw data processor with optimizations:
- Parallel LLM processing
- Smaller batches to avoid cursor timeouts
- Better error handling
- Skip LLM for basic posts when needed
"""
import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

# Set MongoDB URL
MONGODB_URL = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

async def fast_process_raw_data():
    """Fast process raw data with optimizations"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.smart_radar
    raw_collection = db.raw_data
    posts_collection = db.posts_table
    
    # Import services
    import sys
    sys.path.append('/Users/Samrt radar Final /backend')
    from app.services.llm_processing_service import LLMProcessingService
    from app.models.raw_data import RawDataInDB
    
    llm_service = LLMProcessingService()
    
    print("🚀 Starting FAST raw data processing...")
    
    # Count remaining unprocessed data
    unprocessed_count = await raw_collection.count_documents({'processing_status': {'$nin': ['PROCESSED', 'FAILED']}})
    print(f"📊 Remaining raw data entries: {unprocessed_count}")
    
    if unprocessed_count == 0:
        print("✅ All raw data has been processed!")
        await client.close()
        return
    
    # Use smaller batches to prevent cursor timeout
    batch_size = 25  # Smaller batches
    processed_count = 0
    stored_count = 0
    error_count = 0
    tamil_count = 0
    start_time = time.time()
    
    while True:
        batch_start_time = time.time()
        
        # Get a fresh batch each time
        batch = await raw_collection.find({
            'processing_status': {'$nin': ['PROCESSED', 'FAILED']}
        }).limit(batch_size).to_list(None)
        
        if not batch:
            break
        
        print(f"📦 Processing batch of {len(batch)} items...")
        
        # Process batch with parallel LLM calls
        tasks = []
        for raw_doc in batch:
            task = process_single_raw_data(
                raw_doc, llm_service, raw_collection, posts_collection
            )
            tasks.append(task)
        
        # Execute up to 5 items in parallel
        semaphore = asyncio.Semaphore(5)
        
        async def process_with_semaphore(task):
            async with semaphore:
                return await task
        
        # Process in parallel
        results = await asyncio.gather(
            *[process_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Count results
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                print(f"❌ Batch error: {result}")
            elif result:
                processed_count += 1
                if result.get('stored'):
                    stored_count += 1
                if result.get('is_tamil'):
                    tamil_count += 1
        
        batch_duration = time.time() - batch_start_time
        rate = len(batch) / batch_duration if batch_duration > 0 else 0
        
        print(f"📊 Batch complete in {batch_duration:.1f}s ({rate:.1f} items/sec)")
        print(f"   Total: {processed_count} processed, {stored_count} stored, {tamil_count} Tamil, {error_count} errors")
        
        # Check if we should continue
        remaining = await raw_collection.count_documents({
            'processing_status': {'$nin': ['PROCESSED', 'FAILED']}
        })
        if remaining == 0:
            break
        
        print(f"📊 Remaining: {remaining} entries")
        
        # Small delay between batches
        await asyncio.sleep(0.5)
    
    total_duration = time.time() - start_time
    overall_rate = processed_count / total_duration if total_duration > 0 else 0
    
    print(f"\n✅ Fast processing complete!")
    print(f"📊 Performance stats:")
    print(f"   Total processed: {processed_count} in {total_duration:.1f}s")
    print(f"   Average rate: {overall_rate:.1f} items/second")
    print(f"   Posts stored: {stored_count}")
    print(f"   Tamil posts: {tamil_count}")
    print(f"   Errors: {error_count}")
    
    await client.close()

async def process_single_raw_data(raw_doc, llm_service, raw_collection, posts_collection):
    """Process a single raw data entry with optimizations"""
    try:
        # Convert to RawDataInDB model
        raw_data = RawDataInDB(
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
        
        # Set timeout for LLM processing
        try:
            post = await asyncio.wait_for(
                llm_service.process_raw_data(raw_data),
                timeout=15.0  # 15 second timeout
            )
        except asyncio.TimeoutError:
            print(f"⏰ LLM timeout for {raw_doc.get('_id', 'unknown')}, using basic fallback")
            post = None
        
        result = {'stored': False, 'is_tamil': False}
        
        if post:
            # Check if post already exists
            existing = await posts_collection.find_one({
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
                await posts_collection.insert_one(post_dict)
                result['stored'] = True
                
                # Check if Tamil content
                if post.language and ("Tamil" in post.language or "tamil" in post.language.lower() or "mixed" in post.language.lower()):
                    result['is_tamil'] = True
            
            # Mark raw data as processed
            await raw_collection.update_one(
                {"_id": raw_doc["_id"]},
                {"$set": {
                    "processing_status": "PROCESSED",
                    "processed_at": datetime.utcnow(),
                    "posts_extracted": 1
                }}
            )
        else:
            # Mark as failed
            await raw_collection.update_one(
                {"_id": raw_doc["_id"]},
                {"$set": {
                    "processing_status": "FAILED",
                    "processed_at": datetime.utcnow()
                }}
            )
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing {raw_doc.get('_id', 'unknown')}: {e}")
        
        # Mark as failed
        try:
            await raw_collection.update_one(
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

if __name__ == "__main__":
    asyncio.run(fast_process_raw_data())