"""
Quick test script to verify MongoDB Atlas connection
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    try:
        # MongoDB URL from environment
        mongodb_url = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

        print("Testing MongoDB Atlas connection...")
        print(f"URL: {mongodb_url[:50]}...")

        # Create client
        client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
        )

        # Try to get server info
        print("Attempting to connect...")
        db = client.smart_radar
        collections = await db.list_collection_names()
        print(f"✅ Connection successful!")
        print(f"Collections: {collections}")

        client.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
