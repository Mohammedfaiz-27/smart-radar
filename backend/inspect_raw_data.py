#!/usr/bin/env python3
"""Inspect raw_data structure"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    # Get a sample raw_data entry
    sample = await db.raw_data.find_one({"processing_status": "pending"})

    if sample:
        print("Sample raw_data entry structure:")
        print(f"Keys: {list(sample.keys())}")
        print(f"\nPlatform: {sample.get('platform')}")
        print(f"Cluster ID: {sample.get('cluster_id')}")
        print(f"Keyword: {sample.get('keyword')}")
        print(f"Processing Status: {sample.get('processing_status')}")
        print(f"\nraw_json keys: {list(sample.get('raw_json', {}).keys()) if sample.get('raw_json') else 'No raw_json'}")

        if sample.get('raw_json'):
            print(f"\nraw_json content preview:")
            print(json.dumps(sample.get('raw_json'), indent=2)[:500])

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
