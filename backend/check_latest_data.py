#!/usr/bin/env python3
"""
Check the latest collected data for intelligence processing
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

async def check_latest_data():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client.smart_radar
    
    # Check latest monitored_content documents (within last 5 minutes)
    recent_time = datetime.utcnow() - timedelta(minutes=5)
    
    print(f"🔍 Checking monitored_content documents from the last 5 minutes...")
    
    # Get recent documents, sorted by creation time
    recent_docs = []
    async for doc in db.monitored_content.find(
        {"collected_at": {"$gte": recent_time}}
    ).sort("collected_at", -1).limit(5):
        recent_docs.append(doc)
    
    print(f"\n📊 Found {len(recent_docs)} recent documents")
    
    if recent_docs:
        print(f"\n📄 Latest document structure:")
        latest_doc = recent_docs[0]
        
        # Show key info
        print(f"  - Title: {latest_doc.get('title', 'N/A')}")
        print(f"  - Platform: {latest_doc.get('platform', 'N/A')}")
        print(f"  - Processing Status: {latest_doc.get('processing_status', 'N/A')}")
        print(f"  - Has Intelligence: {'intelligence' in latest_doc}")
        print(f"  - Collected At: {latest_doc.get('collected_at', 'N/A')}")
        print(f"  - Last Updated: {latest_doc.get('last_updated', 'N/A')}")
        
        if 'intelligence' in latest_doc:
            print(f"  - Intelligence Keys: {list(latest_doc['intelligence'].keys())}")
            print(f"  - Threat Level: {latest_doc['intelligence'].get('threat_level', 'N/A')}")
        
        # Check processing status distribution
        status_counts = {}
        for doc in recent_docs:
            status = doc.get('processing_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n📈 Processing Status Distribution:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
    
    else:
        print("❌ No recent documents found")
    
    try:
        client.close()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(check_latest_data())