#!/usr/bin/env python3
"""Check indexes on posts_table"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    # Get indexes
    indexes = await db.posts_table.list_indexes().to_list(length=100)

    print("Indexes on posts_table:")
    for idx in indexes:
        print(f"\n  Name: {idx.get('name')}")
        print(f"  Keys: {idx.get('key')}")
        if idx.get('default_language'):
            print(f"  Default language: {idx.get('default_language')}")
        if idx.get('language_override'):
            print(f"  Language override: {idx.get('language_override')}")

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
