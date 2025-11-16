#!/usr/bin/env python3
"""
Continue processing remaining raw_data entries with better cursor handling
"""
import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Set MongoDB URL
MONGODB_URL = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

async def continue_processing():
    """Continue processing unprocessed raw data"""
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
    
    print("🚀 Continuing raw data processing...")
    
    # Count remaining unprocessed data
    unprocessed_count = await raw_collection.count_documents({'processing_status': {'$nin': ['PROCESSED', 'FAILED']}})
    print(f"📊 Remaining raw data entries: {unprocessed_count}")
    
    if unprocessed_count == 0:
        print("✅ All raw data has been processed!")
        await client.close()
        return
    
    # Process in smaller batches to avoid cursor timeout
    batch_size = 50
    processed_count = 0
    stored_count = 0
    error_count = 0
    tamil_count = 0
    
    while True:
        # Get a batch of unprocessed documents
        batch = await raw_collection.find({'processing_status': {'$nin': ['PROCESSED', 'FAILED']}}).limit(batch_size).to_list(None)
        
        if not batch:
            break
        
        print(f"📦 Processing batch of {len(batch)} items...")
        
        for raw_doc in batch:
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
                
                # Process with LLM service
                post = await llm_service.process_raw_data(raw_data)
                
                if post:
                    # Check if post already exists
                    existing = await posts_collection.find_one({
                        "platform": post.platform.value,
                        "platform_post_id": post.platform_post_id
                    })
                    
                    if not existing:
                        # Convert to dict and add timestamps
                        post_dict = post.model_dump()  # Use model_dump instead of dict()
                        post_dict["created_at"] = datetime.utcnow()
                        post_dict["updated_at"] = datetime.utcnow()
                        post_dict["fetched_at"] = raw_data.fetched_at
                        
                        # Store in posts_table
                        await posts_collection.insert_one(post_dict)
                        stored_count += 1
                        
                        # Check if Tamil content
                        if post.language and ("tamil" in post.language.lower() or "mixed" in post.language.lower()):
                            tamil_count += 1
                            print(f"🇮🇳 Tamil/Mixed post: {post.post_text[:80]}...")
                    
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
                    error_count += 1
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing raw data {raw_doc.get('_id', 'unknown')}: {e}")
                
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
                continue
        
        # Progress report after each batch
        print(f"📊 Batch complete: {processed_count} processed, {stored_count} stored, {tamil_count} Tamil/Mixed, {error_count} errors")
        
        # Check if we should continue
        remaining = await raw_collection.count_documents({'processing_status': {'$nin': ['PROCESSED', 'FAILED']}})
        if remaining == 0:
            break
        
        print(f"📊 Remaining: {remaining} entries")
        
        # Small delay to prevent overwhelming the system
        await asyncio.sleep(1)
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Final batch stats:")
    print(f"   Total processed this run: {processed_count}")
    print(f"   Posts stored this run: {stored_count}")
    print(f"   Tamil/Mixed posts this run: {tamil_count}")
    print(f"   Errors this run: {error_count}")
    
    # Final count verification
    final_posts = await posts_collection.count_documents({})
    tamil_posts = await posts_collection.count_documents({"language": {"$regex": "tamil|mixed", "$options": "i"}})
    total_processed = await raw_collection.count_documents({'processing_status': 'PROCESSED'})
    total_raw = await raw_collection.count_documents({})
    
    print(f"\n📊 Overall database status:")
    print(f"   Total posts: {final_posts}")
    print(f"   Tamil/Mixed posts: {tamil_posts}")
    print(f"   Raw data processed: {total_processed}/{total_raw} ({(total_processed/total_raw)*100:.1f}%)")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(continue_processing())