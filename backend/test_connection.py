#!/usr/bin/env python3
"""Test MongoDB Atlas connection with specified endpoint"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"

    try:
        client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000
        )

        # Ping the database
        await client.admin.command('ping')
        print('✓ Connected to MongoDB Atlas successfully')
        print(f'✓ Connection endpoint: smart-radar.tbapili.mongodb.net')

        # List databases
        db_list = await client.list_database_names()
        print(f'✓ Available databases: {db_list}')

        # Check smart_radar database
        db = client.smart_radar
        collections = await db.list_collection_names()
        print(f'✓ Collections in smart_radar: {collections}')

        client.close()
        return True
    except Exception as e:
        print(f'✗ Connection failed: {e}')
        return False

if __name__ == '__main__':
    asyncio.run(test_connection())
