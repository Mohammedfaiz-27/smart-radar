"""
SMART RADAR v25.0 - Unified Intelligence Platform
Core Intelligence Module with unified monitored_content collection
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="SMART RADAR API", version="25.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.clusters import router as clusters_router
from app.api.posts import router as posts_router
from app.api.news import router as news_router
from app.api.sentiment import router as sentiment_router
from app.api.content import router as content_router
from app.api.live_collection import router as live_collection_router

# Include unified content API (v25.0)
app.include_router(content_router, prefix="/api/v1/content", tags=["unified-content"])

# Live data collection API (v25.0)
app.include_router(live_collection_router, prefix="/api/v1/live-collection", tags=["live-collection"])

# Legacy API endpoints (for backwards compatibility)
app.include_router(clusters_router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(posts_router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(news_router, prefix="/api/v1/news", tags=["news"])
app.include_router(sentiment_router, prefix="/api/v1", tags=["sentiment"])

# Database startup
from app.core.database import connect_to_mongo, close_mongo_connection

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("✅ SMART RADAR API Started")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("👋 SMART RADAR API Stopped")

@app.get("/")
async def root():
    return {
        "message": "SMART RADAR API v25.0 - Unified Intelligence Platform", 
        "status": "running",
        "core_module": "unified_monitored_content",
        "intelligence_version": "v24.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "25.0",
        "features": {
            "unified_content_api": "/api/v1/content",
            "migration_endpoints": "/api/v1/content/migrate",
            "master_intelligence": "v24.0",
            "legacy_compatibility": True
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Basic WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)