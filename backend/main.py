"""
SMART RADAR MVP - Main Application Entry Point
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.logging_config import setup_logging
from app.api.clusters import router as clusters_router
from app.api.posts import router as posts_router
from app.api.responses import router as responses_router
from app.api.data_collection import router as data_collection_router
from app.api.collection_config import router as collection_config_router
from app.api.tasks import router as tasks_router
from app.api.sentiment import router as sentiment_router
from app.api.threat_campaigns import router as threat_campaigns_router
from app.api.news import router as news_router
from app.api.migration import router as migration_router
from app.api.content import router as content_router
from app.api.smart_post import router as smart_post_router
from app.api.research import router as research_router
from app.api.narratives import router as narratives_router
from app.services.websocket_manager import WebSocketManager

# Load environment variables (override any existing env vars)
load_dotenv(override=True)

# Initialize logging
debug_mode = os.getenv("DEBUG", "false").lower() == "true"
log_level = "DEBUG" if debug_mode else "INFO"
setup_logging("fastapi_app", log_level)

logger = logging.getLogger(__name__)
logger.info("🚀 Starting SMART RADAR API Server")

# Initialize FastAPI app
app = FastAPI(
    title="SMART RADAR API",
    description="Real-time social media intelligence platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
websocket_manager = WebSocketManager()

# Database events
@app.on_event("startup")
async def startup_db_client():
    logger.info("🔌 Connecting to Supabase PostgreSQL")
    try:
        await connect_to_mongo()
        logger.info("✅ Supabase connection established")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        logger.warning("⚠️  Server starting without database — DB operations will fail until connection is available")
        return

    from app.services.startup_collection import trigger_startup_collection
    try:
        await trigger_startup_collection()
    except Exception as e:
        logger.error(f"❌ Error during startup collection: {e}")

    from app.services.smart_post_service import SmartPostService
    try:
        await SmartPostService().ensure_tables()
        logger.info("✅ Smart Post tables ready")
    except Exception as e:
        logger.error(f"❌ Smart Post table migration failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("🔌 Closing MongoDB connection")
    await close_mongo_connection()
    logger.info("✅ MongoDB connection closed")

# API Routes
app.include_router(clusters_router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(posts_router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(responses_router, prefix="/api/v1/responses", tags=["responses"])
app.include_router(data_collection_router, prefix="/api/v1/collection", tags=["data-collection"])
app.include_router(collection_config_router, prefix="/api/v1/collection-config", tags=["collection-config"])
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(sentiment_router, prefix="/api/v1", tags=["sentiment"])
app.include_router(threat_campaigns_router, prefix="/api/v1/threat-campaigns", tags=["threat-campaigns"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])
app.include_router(migration_router, tags=["migration"])
app.include_router(content_router, prefix="/api/v1/content", tags=["content"])
app.include_router(smart_post_router, prefix="/v1", tags=["smart-post"])
app.include_router(research_router, prefix="/api/v1/research", tags=["research"])
app.include_router(narratives_router, prefix="/api/v1/narratives", tags=["narratives"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "smart-radar-api"}

# Database connection check
@app.get("/health/db")
async def db_health_check():
    try:
        from app.core.database import get_database
        pool = get_database()
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            clusters = await conn.fetchval("SELECT COUNT(*) FROM clusters")
            posts = await conn.fetchval("SELECT COUNT(*) FROM posts_table")
        return {
            "status": "connected",
            "database": "Supabase PostgreSQL",
            "postgres_version": version.split(" ")[1] if version else "unknown",
            "tables": {
                "clusters": clusters,
                "posts": posts
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )