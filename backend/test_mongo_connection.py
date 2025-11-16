"""
Quick test script to verify MongoDB Atlas connection
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        # MongoDB URL from environment
        mongodb_url = os.getenv("MONGODB_URL")

        if not mongodb_url:
            print("❌ MONGODB_URL not found in .env file")
            return

        print("Testing MongoDB Atlas connection...")
        print(f"URL: {mongodb_url[:60]}...")

        # Create client with Atlas-specific settings
        client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=10000,
            tls=True,
            tlsAllowInvalidCertificates=False,
        )

        # Try to get server info
        print("Attempting to connect...")
        db = client.smart_radar
        collections = await db.list_collection_names()
        print(f"✅ Connection successful!")
        print(f"Collections: {collections}")

        # Get server info
        server_info = await client.server_info()
        print(f"MongoDB version: {server_info.get('version')}")

        client.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
