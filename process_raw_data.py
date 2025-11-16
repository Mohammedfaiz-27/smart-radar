#!/usr/bin/env python3
"""
Process all raw_data entries and convert them to posts_table entries
"""
import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Set MongoDB URL
MONGODB_URL = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

async def process_all_raw_data():
    """Process all raw data entries"""
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
    
    print("🚀 Starting bulk raw data processing...")
    
    # Count total raw data
    total_raw = await raw_collection.count_documents({})
    print(f"📊 Total raw data entries: {total_raw}")
    
    # Process in batches
    batch_size = 50
    processed_count = 0
    stored_count = 0
    error_count = 0
    
    async for raw_doc in raw_collection.find({}):
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
                    post_dict = post.dict()
                    post_dict["created_at"] = datetime.utcnow()
                    post_dict["updated_at"] = datetime.utcnow()
                    post_dict["fetched_at"] = raw_data.fetched_at
                    
                    # Store in posts_table
                    await posts_collection.insert_one(post_dict)
                    stored_count += 1
                    
                    # Check if Tamil content
                    if post.language and "tamil" in post.language.lower():
                        print(f"🇮🇳 Tamil post processed: {post.post_text[:100]}...")
                
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
            
            # Progress report
            if processed_count % 100 == 0:
                print(f"📊 Progress: {processed_count}/{total_raw} processed, {stored_count} stored, {error_count} errors")
            
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
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Final stats:")
    print(f"   Total processed: {processed_count}")
    print(f"   Posts stored: {stored_count}")
    print(f"   Errors: {error_count}")
    
    # Final count verification
    final_posts = await posts_collection.count_documents({})
    tamil_posts = await posts_collection.count_documents({"language": {"$regex": "tamil", "$options": "i"}})
    
    print(f"\n📊 Database status:")
    print(f"   Total posts: {final_posts}")
    print(f"   Tamil posts: {tamil_posts}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(process_all_raw_data())