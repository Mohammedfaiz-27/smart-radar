#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

async def process_all_pending():
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    pending_count = db.raw_data.count_documents({"processing_status": "pending"})
    print(f"📊 Total pending entries: {pending_count}")
    
    # Process in batches of 50
    batch_size = 50
    total_processed = 0
    
    while pending_count > 0:
        print(f"\n🔄 Processing batch of {batch_size} entries...")
        
        # Import and run the processing
        import subprocess
        import sys
        
        result = subprocess.run([
            sys.executable, "process_backlog.py", str(batch_size)
        ], capture_output=True, text=True, cwd="/Users/Samrt radar Final /backend")
        
        if result.returncode == 0:
            print("✅ Batch completed successfully")
        else:
            print(f"❌ Batch failed: {result.stderr}")
            break
            
        # Check remaining
        new_pending = db.raw_data.count_documents({"processing_status": "pending"})
        processed_in_batch = pending_count - new_pending
        total_processed += processed_in_batch
        pending_count = new_pending
        
        print(f"📈 Progress: {processed_in_batch} processed, {pending_count} remaining")
        
        if pending_count == 0:
            print(f"\n🎉 All {total_processed} entries processed successfully!")
            break
            
        # Small delay between batches
        await asyncio.sleep(10)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(process_all_pending())
