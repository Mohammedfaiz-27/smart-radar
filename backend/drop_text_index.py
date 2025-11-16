#!/usr/bin/env python3
"""Drop the problematic text index"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    print("Dropping text index: post_text_text")
    result = await db.posts_table.drop_index("post_text_text")
    print(f"✓ Dropped: {result}")

    # List remaining indexes
    indexes = await db.posts_table.list_indexes().to_list(length=100)
    print(f"\nRemaining indexes:")
    for idx in indexes:
        print(f"  - {idx.get('name')}")

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
