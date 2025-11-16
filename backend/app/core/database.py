"""
Database connection and configuration
"""
import os
import asyncio
import weakref
import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict
import threading

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
                    cls._instance._clients = {}  # Dict to store clients per event loop
                    cls._instance._databases = {}  # Dict to store databases per event loop
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not hasattr(self, '_initialized'):
            self._clients: Dict[int, AsyncIOMotorClient] = {}
            self._databases: Dict[int, object] = {}
            self._initialized = True
    
    def get_client_for_loop(self):
        """Get or create a Motor client for the current event loop"""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # No event loop running, use a default key
            loop_id = 0
        
        if loop_id not in self._clients:
            mongodb_url = os.getenv("MONGODB_URL")

            # Create a new client for this event loop
            # For MongoDB Atlas, use TLS but verify certificates
            self._clients[loop_id] = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=50,
                minPoolSize=5,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=10000,
                socketTimeoutMS=20000,
                connectTimeoutMS=10000,
                retryWrites=True,
                retryReads=True,
                tls=True,
                tlsAllowInvalidCertificates=False,
            )
            
            # Create database instance for this event loop
            if "smart_radar" in mongodb_url:
                self._databases[loop_id] = self._clients[loop_id].smart_radar
            else:
                # Always use smart_radar as the database name
                self._databases[loop_id] = self._clients[loop_id].smart_radar
        
        return self._clients[loop_id], self._databases[loop_id]

db = Database()

async def connect_to_mongo():
    """Create database connection with proper per-loop connection pooling"""
    # This function now just ensures we have a client for this event loop
    client, database = db.get_client_for_loop()
    print("Connected to MongoDB with per-loop connection pooling")
    return database

async def close_mongo_connection():
    """Close database connections for all event loops"""
    for client in db._clients.values():
        if client:
            client.close()
    db._clients.clear()
    db._databases.clear()
    print("Disconnected from MongoDB")

def get_database():
    """Get database instance for the current event loop"""
    try:
        client, database = db.get_client_for_loop()
        if database is None:
            # If we don't have a database name in the URL, use default
            mongodb_url = os.getenv("MONGODB_URL")
            if "smart_radar" not in mongodb_url:
                # Force a default database name
                database = client.smart_radar
        return database
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get database for current event loop: {e}")
        # Return a fallback database connection instead of None
        try:
            mongodb_url = os.getenv("MONGODB_URL")
            client = AsyncIOMotorClient(mongodb_url)
            return client.smart_radar
        except Exception as fallback_error:
            logger.error(f"Fallback database connection also failed: {fallback_error}")
            return None