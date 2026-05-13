import traceback
import logging
from fastapi import FastAPI, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import json

# Load environment variables first
load_dotenv()

# Import and configure beautiful logging BEFORE other imports
from core.logging_config import setup_logging, get_logger

# Configure beautiful logging
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE"),
    use_colors=os.getenv("LOG_COLORS", "true").lower() == "true",
    use_emojis=os.getenv("LOG_EMOJIS", "true").lower() == "true"
)

# Get logger with beautiful formatting
logger = get_logger(__name__)

# Import existing services for backward compatibility
from services.research_service import ResearchService
from services.graph_service import GraphService
from services.social_media_service import SocialMediaService
from services.social_util import (
    post_to_facebook_page,
)
from services.social_posting_service import SocialPostingService
from services.content_service import ContentService
from social_test import get_facebook_posts, get_twitter_posts, filter_by_language

# Import new API structure
from core.config import settings
from core.database import get_database
from api.v1.api import api_router
from api.v1.automation import initialize_news_service
from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-tenant SaaS platform for social media content management"
)

# Initialize social posting service
social_posting_service = SocialPostingService()

@app.on_event("startup")
async def startup_event():
    """Initialize database schema and run cleanup on startup"""
    logger.info("🚀 Starting OmniPush backend...")

    # Check and apply news_item_id migration
    try:
        from core.database import db
        supabase = db.service_client

        # Check if news_item_id column exists
        logger.info("Checking database schema...")

        # Try to apply migration (will be ignored if column already exists)
        migration_sql = """
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS news_item_id UUID REFERENCES external_news_items(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_posts_news_item_id ON posts(news_item_id);
        """

        # Execute migration
        result = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()
        logger.info("✅ Database schema check completed")

    except Exception as e:
        logger.warning(f"⚠️ Database migration check failed: {e}")
        logger.info("Posts endpoint will work without news_item relationship")

    # Run cleanup of old temporary files
    try:
        from services.cleanup_service import cleanup_service

        logger.info("🧹 Running startup cleanup...")
        cleanup_results = cleanup_service.cleanup_all()

        totals = cleanup_results.get("totals", {})
        if totals.get("deleted", 0) > 0:
            logger.info(
                f"✅ Cleanup completed: {totals['deleted']} files removed, "
                f"{totals['bytes_freed'] / 1024 / 1024:.2f} MB freed"
            )
        else:
            logger.info("✅ Cleanup completed: No old files to remove")

    except Exception as e:
        logger.warning(f"⚠️ Startup cleanup failed: {e}")
        logger.info("Application will continue without cleanup")
    # Auto-create internal system account if configured
    try:
        internal_email = os.getenv("INTERNAL_EMAIL")
        internal_password = os.getenv("INTERNAL_PASSWORD")
        internal_tenant = os.getenv("INTERNAL_TENANT_NAME", "Smart Radar")
        if internal_email and internal_password:
            from core.database import db as _db
            from core.security import hash_password as _hp
            from uuid import uuid4 as _uuid4
            import re as _re
            _sc = _db.service_client
            existing = _sc.table('users').select('id').eq('email', internal_email).execute()
            if not existing.data:
                logger.info(f"Creating internal system account: {internal_email}")
                _tid = str(_uuid4())
                _slug = _re.sub(r'[^a-z0-9-]', '', internal_tenant.lower().replace(' ', '-')) or f"tenant-{_tid[:8]}"
                _sc.table('tenants').insert({
                    'id': _tid, 'name': internal_tenant, 'slug': _slug,
                    'subscription_tier': 'basic', 'subscription_status': 'active',
                    'created_at': __import__('datetime').datetime.utcnow().isoformat()
                }).execute()
                _sc.table('users').insert({
                    'id': str(_uuid4()), 'email': internal_email,
                    'first_name': 'Smart', 'last_name': 'Radar',
                    'password_hash': _hp(internal_password),
                    'tenant_id': _tid, 'role': 'admin', 'status': 'active',
                    'created_at': __import__('datetime').datetime.utcnow().isoformat()
                }).execute()
                logger.info("✅ Internal system account created")
            else:
                logger.info("✅ Internal system account already exists")
    except Exception as e:
        logger.warning(f"⚠️ Could not auto-create internal account: {e}")

    # Start cron service for scheduled post execution
    try:
        from core.database import db as _cron_db
        from services.cron_service import CronService, CronJob as _CronJob

        _cron = CronService(_cron_db.service_client)

        # Inject a system-level job that fires every minute to publish due posts.
        # This runs regardless of any tenant-configured cron jobs.
        _system_job = _CronJob(
            id="system-scheduled-posts",
            name="System: Publish Due Scheduled Posts",
            schedule="* * * * *",   # every minute
            task_type="scheduled_posts",
            parameters={},
            tenant_id=None,          # None = scan all tenants
            is_enabled=True,
        )
        _system_job.next_run = _cron._calculate_next_run(_system_job.schedule)
        _cron.active_jobs[_system_job.id] = _system_job

        await _cron.start()
        logger.info("✅ Cron service started (scheduled-post publisher active)")
    except Exception as e:
        logger.warning(f"⚠️ Cron service failed to start: {e}")

    logger.info("🎯 Backend startup completed")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount media files (serve uploaded media content)
import os
media_dir = os.path.join(os.getcwd(), "media")
if not os.path.exists(media_dir):
    os.makedirs(media_dir)
app.mount("/media", StaticFiles(directory="media"), name="media")

# Include API v1 routes
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Initialize services for backward compatibility
research_service = ResearchService()
graph_service = GraphService()
social_media_service = SocialMediaService()
content_service = ContentService()

# Initialize new services
initialize_news_service()


@app.get("/")
async def root():
    return {
        "message": f"{settings.app_name} API is running",
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = get_database()
        db_healthy = await db.health_check()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": "2025-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Legacy endpoints for backward compatibility
@app.post("/research")
async def research_query(
    city: str = Form(None),
    query: str = Form(None)
):
    # Support both legacy city parameter and new query parameter
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        research_data = await research_service.research_query(research_query_text)
        return JSONResponse(content=research_data)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/about")
async def research_about(
    city: str = Form(None),
    query: str = Form(None)
):
    """Get basic understanding of the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        about = await research_service._get_understanding(research_query_text)
        return JSONResponse(content={"about": about})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/history")
async def research_history(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get historical information about the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        history = await research_service._get_history(research_query_text, understanding)
        return JSONResponse(content={"history": history})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/current-affairs")
async def research_current_affairs(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get current affairs about the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        current_affairs = await research_service._get_current_affairs(research_query_text, understanding)
        return JSONResponse(content={"current_affairs": current_affairs})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/competitors")
async def research_competitors(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get competitors analysis for the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        competitors = await research_service._get_competitors(research_query_text, understanding)
        return JSONResponse(content={"competitors": competitors})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/challenges")
async def research_challenges(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get challenges analysis for the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        challenges = await research_service._get_challenges(research_query_text, understanding)
        return JSONResponse(content={"challenges": challenges})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/plus-points")
async def research_plus_points(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get plus points analysis for the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        plus_points = await research_service._get_plus_points(research_query_text, understanding)
        return JSONResponse(content={"plus_points": plus_points})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/negative-points")
async def research_negative_points(
    city: str = Form(None),
    query: str = Form(None),
    understanding: str = Form(None)
):
    """Get negative points analysis for the query"""
    research_query_text = query if query else city
    if not research_query_text:
        raise HTTPException(status_code=400, detail="Either 'city' or 'query' parameter is required")
    
    try:
        negative_points = await research_service._get_negative_points(research_query_text, understanding)
        return JSONResponse(content={"negative_points": negative_points})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-graph")
async def generate_graph(
    city: str = Form(...),
    openai_analysis: str | None = Form(None),
    perplexity_research: str | None = Form(None),
):
    try:
        if (openai_analysis and openai_analysis.strip()) or (
            perplexity_research and perplexity_research.strip()
        ):
            research_data = {
                "city": city,
                "openai_analysis": openai_analysis or "",
                "perplexity_research": perplexity_research or "",
            }
        else:
            research_data = await research_service.research_city(city)

        graph_data = await graph_service.generate_knowledge_graph(city, research_data)
        return JSONResponse(content=graph_data)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-handles")
async def generate_handles(
    city: str = Form(...),
    openai_analysis: str | None = Form(None),
    perplexity_research: str | None = Form(None),
):
    try:
        if (openai_analysis and openai_analysis.strip()) or (
            perplexity_research and perplexity_research.strip()
        ):
            research_data = {
                "city": city,
                "openai_analysis": openai_analysis or "",
                "perplexity_research": perplexity_research or "",
            }
        else:
            research_data = await research_service.research_city(city)

        handles = await social_media_service.generate_social_handles(city, research_data)
        return JSONResponse(content=handles)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-post")
async def generate_post(content: str = Form(...)):
    try:
        html_content = await content_service.generate_html_content(content)
        return JSONResponse(content={"html": html_content})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-content")
async def generate_content(content: str = Form(...)):
    try:
        improved = await content_service.generate_text_content(content)
        return JSONResponse(content={"content": improved})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-screenshot")
async def generate_screenshot(
    content: str = Form(...),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    try:
        screenshot_info = await content_service.generate_screenshot(content, ctx.tenant_id)
        return JSONResponse(content=screenshot_info)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-to-social")
async def post_to_social(
    content: str = Form(...),
    screenshot: str | None = Form(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    try:
        screenshot_info = None
        if screenshot:
            try:
                screenshot_info = json.loads(screenshot)
            except Exception:
                screenshot_info = None
        if not screenshot_info:
            screenshot_info = await content_service.generate_screenshot(content, ctx.tenant_id)

        results = []
        try:
            with open("config/social_handles.json", "r") as f:
                handles_config = json.load(f)
            default_facebook_pages = [
                h for h in handles_config.get("handles", []) if h.get("platform") == "facebook"
            ]
        except Exception:
            default_facebook_pages = []

        for handle in default_facebook_pages:
            post_result = await social_media_service.post_to_facebook(
                handle.get("page_id", ""), screenshot_info["path"], content
            )
            post_result["platform"] = "facebook"
            post_result["target"] = handle.get("name") or handle.get("page_id")
            results.append(post_result)

        return JSONResponse(content={"results": results, "screenshot": screenshot_info})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/screenshots")
async def get_screenshots():
    try:
        screenshots_dir = os.path.join("static", "screenshots")
        if not os.path.exists(screenshots_dir):
            return JSONResponse(content=[])

        screenshots = []
        for filename in os.listdir(screenshots_dir):
            if filename.endswith((".png", ".jpg", ".jpeg")):
                file_path = os.path.join(screenshots_dir, filename)
                stat = os.stat(file_path)

                screenshots.append(
                    {
                        "filename": filename,
                        "path": file_path,
                        "url": f"/static/screenshots/{filename}",
                        "size": stat.st_size,
                        "created": stat.st_mtime,
                    }
                )

        screenshots.sort(key=lambda x: x["created"], reverse=True)
        return JSONResponse(content=screenshots)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/screenshots/{filename}")
async def delete_screenshot(filename: str):
    try:
        file_path = os.path.join("static", "screenshots", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse(content={"message": "Screenshot deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="Screenshot not found")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/screenshots")
async def delete_all_screenshots():
    try:
        screenshots_dir = os.path.join("static", "screenshots")
        if os.path.exists(screenshots_dir):
            for filename in os.listdir(screenshots_dir):
                file_path = os.path.join(screenshots_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        return JSONResponse(content={"message": "All screenshots deleted successfully"})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-social-posts")
async def generate_social_posts(
    city: str = Form(...),
    openai_analysis: str | None = Form(None),
    perplexity_research: str | None = Form(None),
):
    try:
        research_data = {
            "city": city,
            "openai_analysis": openai_analysis or "",
            "perplexity_research": perplexity_research or "",
        }
        
        posts = await content_service.generate_social_media_posts(city, research_data)
        return JSONResponse(content=posts)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-fixed")
async def post_fixed(
    content: str = Form(...),
    image: str = Form(...),
):
    try:
        # Use new social posting service for WhatsApp
        wa_response = social_posting_service.post_to_whatsapp(
            group_id="120363422585569875@g.us",
            message=content,
            media_url=image,
        )

        # Convert to legacy format for compatibility
        wa = {
            "success": not wa_response.error,
            "error": wa_response.error,
            "id": wa_response.post_id,
            "message": wa_response.message
        }

        fb = post_to_facebook_page(
            page_id="61579232464240",
            message=content,
            image_urls=[image],
            user_access_token=os.getenv("FB_LONG_LIVED_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN", ""),
        )

        return JSONResponse(content={"whatsapp": wa, "facebook": fb})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-live-news")
async def get_live_news(
    city: str,
    languages: str = "english,tamil",
    twitter_next_token: str = None,
    facebook_cursor: str = None
):
    """
    Get live news from social media platforms, filtered by language.

    Parameters:
    - city: City name to search for
    - languages: Comma-separated list of languages (default: "english,tamil")
                 Supported: english, tamil
    - twitter_next_token: Pagination token for Twitter (next page) - Twitter v2 style
    - facebook_cursor: Cursor for Facebook pagination (next page) - Cursor-based pagination
    """
    try:
        from datetime import datetime, timezone

        # Parse allowed languages from query parameter
        allowed_languages = [lang.strip().lower() for lang in languages.split(',')]

        # Get social media posts with pagination
        # Smart query construction: only add 'tamilnadu' for city-like queries
        query = city.strip()

        # For city queries in India, add tamilnadu context
        if not query:
            return JSONResponse(content={
            "city": city,
            "languages": allowed_languages,
            "facebook_posts": {},
            "twitter_posts": {},
            "pagination": {},
            "fetched_at": datetime.now(timezone.utc).isoformat()
        })

        query = query + ' tamilnadu'

        # Fetch Facebook posts using cursor-based pagination
        facebook_data = get_facebook_posts(query, cursor=facebook_cursor)

        # Fetch tweets using Twitter v2 pagination pattern
        # Fetch more tweets in initial request if no token provided
        max_results = 20
        twitter_data = get_twitter_posts(query, pagination_token=twitter_next_token, max_results=max_results)

        # Combine real and mock data
        # all_facebook = facebook_data #+ mock_news
        # all_twitter = twitter_data #+ mock_twitter

        # Filter by language
        # Facebook posts filtering
        if facebook_data and 'data' in facebook_data and 'items' in facebook_data['data']:
            # Extract posts from Facebook API response structure
            facebook_posts = []
            for item in facebook_data['data']['items']:
                if 'basic_info' in item and 'post_text' in item['basic_info']:
                    # Transform to filter-compatible format
                    facebook_posts.append({
                        'message': item['basic_info']['post_text'],
                        'original_item': item
                    })

            # Filter by language
            filtered_facebook = filter_by_language(facebook_posts, allowed_languages)

            # Extract original items back
            facebook_data['data']['items'] = [post['original_item'] for post in filtered_facebook]
            facebook_data['data']['total_results'] = len(facebook_data['data']['items'])

        # Twitter posts filtering
        # Twitter API returns nested structure, need to extract tweets from timeline
        if twitter_data and 'result' in twitter_data:
            timeline = twitter_data['result'].get('timeline', {})
            instructions = timeline.get('instructions', [])

            filtered_instructions = []
            for instruction in instructions:
                if instruction.get('type') == 'TimelineAddEntries':
                    entries = instruction.get('entries', [])
                    filtered_entries = []

                    for entry in entries:
                        # Extract tweet text from nested structure
                        try:
                            item_content = entry.get('content', {}).get('itemContent', {})
                            tweet_results = item_content.get('tweet_results', {})
                            tweet = tweet_results.get('result', {})
                            legacy = tweet.get('legacy', {})

                            if legacy:
                                full_text = legacy.get('full_text', '')
                                # Use filter_by_language with a single-item list
                                if filter_by_language([legacy], allowed_languages):
                                    filtered_entries.append(entry)
                        except (KeyError, AttributeError):
                            # If structure is different or incomplete, skip this entry
                            logger.exception(f"Failed to extract tweet text from entry: {entry}")
                            continue

                    # Update instruction with filtered entries
                    filtered_instruction = instruction.copy()
                    filtered_instruction['entries'] = filtered_entries
                    filtered_instructions.append(filtered_instruction)
                else:
                    # Keep non-entry instructions as is
                    filtered_instructions.append(instruction)

            # Update timeline with filtered instructions
            twitter_data['result']['timeline']['instructions'] = filtered_instructions
        
        # Extract pagination metadata using Twitter v2 pattern
        # Only indicate has_more if we actually got entries in this response
        twitter_has_entries = any(
            i.get('type') == 'TimelineAddEntries' and len(i.get('entries', [])) > 0
            for i in twitter_data.get('result', {}).get('timeline', {}).get('instructions', [])
        )
        facebook_has_entries = bool(facebook_data.get('data', {}).get('items'))

        # Extract next_token from normalized response
        twitter_next_token_value = twitter_data.get('meta', {}).get('next_token') if twitter_has_entries else None

        # Extract Facebook cursor from response
        facebook_next_cursor = facebook_data.get('pagination', {}).get('next_cursor') if facebook_has_entries else None

        pagination_info = {
            "twitter": {
                "next_token": twitter_next_token_value,  # Twitter v2 style
                "has_more": twitter_has_entries and bool(twitter_next_token_value)
            },
            "facebook": {
                "next_cursor": facebook_next_cursor,  # Cursor-based pagination
                "has_more": facebook_has_entries and bool(facebook_next_cursor)
            }
        }

        logger.info(f"Pagination info - Twitter: has_entries={twitter_has_entries}, next_token={'exists' if twitter_next_token_value else 'none'}, Facebook: has_entries={facebook_has_entries}")

        return JSONResponse(content={
            "city": city,
            "languages": allowed_languages,
            "facebook_posts": facebook_data,
            "twitter_posts": twitter_data,
            "pagination": pagination_info,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)