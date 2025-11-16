#!/usr/bin/env python3
"""
Debug script to examine the actual data structure in MongoDB
"""
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from pprint import pprint

async def debug_data_structure():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client.smart_radar
    
    print("🔍 Examining monitored_content data structure...")
    
    # Get a sample document
    sample_doc = await db.monitored_content.find_one({})
    
    if sample_doc:
        print("\n📄 Complete sample document structure:")
        # Convert ObjectId to string for JSON serialization
        if '_id' in sample_doc:
            sample_doc['_id'] = str(sample_doc['_id'])
        
        print(json.dumps(sample_doc, indent=2, default=str))
        
        print(f"\n🔑 Document keys: {list(sample_doc.keys())}")
        
        # Check intelligence field specifically
        if 'intelligence' in sample_doc:
            print(f"\n🧠 Intelligence field exists: {type(sample_doc['intelligence'])}")
            print(f"Intelligence content: {sample_doc['intelligence']}")
        else:
            print("\n❌ No 'intelligence' field found!")
            
        # Check for alternative intelligence field names
        intelligence_fields = [k for k in sample_doc.keys() if 'intel' in k.lower()]
        if intelligence_fields:
            print(f"\n🔍 Found intelligence-related fields: {intelligence_fields}")
            for field in intelligence_fields:
                print(f"  {field}: {sample_doc[field]}")
    
    else:
        print("❌ No documents found in monitored_content collection")
    
    # Check a few more documents to see if the pattern is consistent
    print(f"\n📊 Checking multiple documents...")
    cursor = db.monitored_content.find({}).limit(5)
    count = 0
    intelligence_count = 0
    
    async for doc in cursor:
        count += 1
        has_intelligence = 'intelligence' in doc
        if has_intelligence:
            intelligence_count += 1
        print(f"Document {count}: Intelligence field present = {has_intelligence}")
        if has_intelligence:
            print(f"  Intelligence type: {type(doc['intelligence'])}")
    
    print(f"\n📈 Summary: {intelligence_count}/{count} documents have intelligence field")
    
    try:
        client.close()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(debug_data_structure())