#!/usr/bin/env python3
"""
Monitor LLM processing progress in real-time
"""
import asyncio
import time
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

def get_progress():
    """Get current processing progress"""
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Check raw_data collection
    total_raw = db.raw_data.count_documents({})
    pending_raw = db.raw_data.count_documents({'processing_status': 'pending'})
    processing_raw = db.raw_data.count_documents({'processing_status': 'processing'})
    completed_raw = db.raw_data.count_documents({'processing_status': 'completed'})
    
    # Check posts_table
    total_posts = db.posts_table.count_documents({})
    
    client.close()
    
    return {
        'total_raw': total_raw,
        'pending_raw': pending_raw,
        'processing_raw': processing_raw,
        'completed_raw': completed_raw,
        'total_posts': total_posts,
        'progress_percentage': round((completed_raw / total_raw * 100), 2) if total_raw > 0 else 0
    }

def format_time(seconds):
    """Format seconds into human readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def estimate_completion(initial_pending, current_pending, elapsed_time):
    """Estimate time to completion"""
    if elapsed_time <= 0 or current_pending <= 0:
        return "Unknown"
    
    processed = initial_pending - current_pending
    if processed <= 0:
        return "Unknown"
    
    rate = processed / elapsed_time  # items per second
    remaining_time = current_pending / rate
    
    return format_time(remaining_time)

if __name__ == "__main__":
    print("🚀 LLM Processing Monitor")
    print("=" * 60)
    
    start_time = time.time()
    initial_progress = get_progress()
    initial_pending = initial_progress['pending_raw']
    
    print(f"📊 Initial Status:")
    print(f"  Total raw data: {initial_progress['total_raw']}")
    print(f"  Pending: {initial_progress['pending_raw']}")
    print(f"  Processing: {initial_progress['processing_raw']}")
    print(f"  Completed: {initial_progress['completed_raw']}")
    print(f"  Posts created: {initial_progress['total_posts']}")
    print("=" * 60)
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            progress = get_progress()
            processed_since_start = initial_pending - progress['pending_raw']
            
            # Calculate processing rate
            if elapsed > 0 and processed_since_start > 0:
                rate_per_sec = processed_since_start / elapsed
                rate_per_min = rate_per_sec * 60
                eta = estimate_completion(initial_pending, progress['pending_raw'], elapsed)
            else:
                rate_per_sec = 0
                rate_per_min = 0
                eta = "Calculating..."
            
            # Clear screen and show updated progress
            print(f"\r🔄 LLM Processing Progress - {datetime.now().strftime('%H:%M:%S')}")
            print(f"📈 Progress: {progress['progress_percentage']}% complete")
            print(f"📊 Status:")
            print(f"  ✅ Completed: {progress['completed_raw']}")
            print(f"  🔄 Processing: {progress['processing_raw']}")
            print(f"  ⏳ Pending: {progress['pending_raw']}")
            print(f"  📄 Posts Created: {progress['total_posts']}")
            print(f"🚀 Performance:")
            print(f"  🏃 Rate: {rate_per_min:.1f} items/min ({rate_per_sec:.2f} items/sec)")
            print(f"  ⏱️  Elapsed: {format_time(elapsed)}")
            print(f"  🎯 ETA: {eta}")
            print("=" * 60)
            
            # Exit if completed
            if progress['pending_raw'] == 0:
                print("\n🎉 All processing completed!")
                print(f"✅ Total processed: {progress['completed_raw']}")
                print(f"📊 Total posts created: {progress['total_posts']}")
                print(f"⏱️  Total time: {format_time(elapsed)}")
                break
            
            # Wait 10 seconds before next update
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
        print(f"📈 Final progress: {progress['progress_percentage']}%")
        print(f"⏱️  Runtime: {format_time(elapsed)}")