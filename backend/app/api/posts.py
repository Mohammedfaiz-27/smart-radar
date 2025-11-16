"""
Social posts API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.models.social_post import SocialPostCreate, SocialPostResponse
from app.services.social_post_service import SocialPostService
from app.services.posts_table_service import PostsTableService
from app.services.cluster_service import ClusterService
from app.models.posts_table import PostsQueryParams, Platform, SentimentLabel

router = APIRouter()
post_service = SocialPostService()
posts_table_service = PostsTableService()
cluster_service = ClusterService()

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response model"""
    posts_today: int
    positive_posts: int
    negative_posts: int
    opportunities: int

@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats():
    """Get dashboard statistics for widgets"""
    # Get aggregated stats from posts_table
    stats = await posts_table_service.get_aggregate_stats()
    
    # Calculate dashboard metrics
    positive_posts = stats.posts_by_sentiment.get("Positive", 0)
    negative_posts = stats.posts_by_sentiment.get("Negative", 0)
    
    # Count competitor negative posts as opportunities
    opportunities = 0
    clusters = await cluster_service.get_clusters(cluster_type="competitor")
    for cluster in clusters:
        cluster_stats = await posts_table_service.get_aggregate_stats(cluster_id=cluster.id)
        opportunities += cluster_stats.posts_by_sentiment.get("Negative", 0)
    
    return DashboardStatsResponse(
        posts_today=stats.total_posts,
        positive_posts=positive_posts,
        negative_posts=negative_posts,
        opportunities=opportunities
    )

@router.get("/dashboard-stats/positive", response_model=List[dict])
async def get_positive_posts(limit: int = Query(100, ge=1, le=1000)):
    """Get own positive posts for widget popup"""
    # Use the same logic as dashboard stats but return the actual posts
    from app.core.database import get_database
    
    db = get_database()
    collection = db.monitored_content
    
    # Find posts with positive sentiment for own clusters
    pipeline = [
        {"$match": {"content_type": "social_post"}},
        {"$match": {"matched_clusters.cluster_type": "own"}},
        {"$match": {"intelligence.entity_sentiments": {"$exists": True}}},
        {"$limit": 200}  # Get more posts to filter from
    ]
    
    cursor = collection.aggregate(pipeline)
    posts = await cursor.to_list(length=200)
    
    # Filter for positive sentiment posts
    positive_posts = []
    for post in posts:
        if post.get("intelligence", {}).get("entity_sentiments"):
            for entity, sentiment in post["intelligence"]["entity_sentiments"].items():
                if isinstance(sentiment, dict) and sentiment.get("label") == "Positive":
                    # Format the post
                    post_dict = {
                        "id": str(post["_id"]),
                        "content_type": post.get("content_type", "social_post"),
                        "platform": post.get("platform", "X"),
                        "content": post.get("content", ""),
                        "title": post.get("title", ""),
                        "author": post.get("author", ""),
                        "url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "post_url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "published_at": post.get("published_at"),
                        "posted_at": post.get("published_at"),
                        "cluster_type": "own",
                        "sentiment": "positive",
                        "has_been_responded_to": False,
                        "intelligence": post.get("intelligence", {}),
                        "matched_clusters": post.get("matched_clusters", [])
                    }
                    
                    # Add engagement metrics
                    if post.get("social_metrics"):
                        metrics = post["social_metrics"]
                        post_dict["engagement_metrics"] = {
                            "likes": metrics.get("likes", 0),
                            "shares": metrics.get("shares", 0),
                            "comments": metrics.get("comments", 0),
                            "views": metrics.get("views", 0),
                            "retweets": metrics.get("shares", 0),
                            "replies": metrics.get("comments", 0),
                            "impressions": metrics.get("views", 0)
                        }
                    else:
                        post_dict["engagement_metrics"] = {
                            "likes": 0, "shares": 0, "comments": 0, 
                            "views": 0, "retweets": 0, "replies": 0, "impressions": 0
                        }
                    
                    positive_posts.append(post_dict)
                    break  # Count each post only once
    
    return positive_posts[:limit]

@router.get("/dashboard-stats/negative", response_model=List[dict])
async def get_negative_posts(limit: int = Query(100, ge=1, le=1000)):
    """Get own negative posts for widget popup"""
    # Use the same logic as dashboard stats but return the actual posts
    from app.core.database import get_database
    
    db = get_database()
    collection = db.monitored_content
    
    # Find posts with negative sentiment for own clusters
    pipeline = [
        {"$match": {"content_type": "social_post"}},
        {"$match": {"matched_clusters.cluster_type": "own"}},
        {"$match": {"intelligence.entity_sentiments": {"$exists": True}}},
        {"$limit": 200}  # Get more posts to filter from
    ]
    
    cursor = collection.aggregate(pipeline)
    posts = await cursor.to_list(length=200)
    
    # Filter for negative sentiment posts
    negative_posts = []
    for post in posts:
        if post.get("intelligence", {}).get("entity_sentiments"):
            for entity, sentiment in post["intelligence"]["entity_sentiments"].items():
                if isinstance(sentiment, dict) and sentiment.get("label") == "Negative":
                    # Format the post
                    post_dict = {
                        "id": str(post["_id"]),
                        "content_type": post.get("content_type", "social_post"),
                        "platform": post.get("platform", "X"),
                        "content": post.get("content", ""),
                        "title": post.get("title", ""),
                        "author": post.get("author", ""),
                        "url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "post_url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "published_at": post.get("published_at"),
                        "posted_at": post.get("published_at"),
                        "cluster_type": "own",
                        "sentiment": "negative",
                        "has_been_responded_to": False,
                        "intelligence": post.get("intelligence", {}),
                        "matched_clusters": post.get("matched_clusters", [])
                    }
                    
                    # Add engagement metrics
                    if post.get("social_metrics"):
                        metrics = post["social_metrics"]
                        post_dict["engagement_metrics"] = {
                            "likes": metrics.get("likes", 0),
                            "shares": metrics.get("shares", 0),
                            "comments": metrics.get("comments", 0),
                            "views": metrics.get("views", 0),
                            "retweets": metrics.get("shares", 0),
                            "replies": metrics.get("comments", 0),
                            "impressions": metrics.get("views", 0)
                        }
                    else:
                        post_dict["engagement_metrics"] = {
                            "likes": 0, "shares": 0, "comments": 0,
                            "views": 0, "retweets": 0, "replies": 0, "impressions": 0
                        }
                    
                    negative_posts.append(post_dict)
                    break  # Count each post only once
    
    return negative_posts[:limit]

@router.get("/dashboard-stats/opportunities", response_model=List[dict])
async def get_opportunity_posts(limit: int = Query(100, ge=1, le=1000)):
    """Get competitor negative posts for opportunities widget popup"""
    # Use the same logic as dashboard stats but return the actual posts
    from app.core.database import get_database
    
    db = get_database()
    collection = db.monitored_content
    
    # Find posts with negative sentiment for competitor clusters
    pipeline = [
        {"$match": {"content_type": "social_post"}},
        {"$match": {"matched_clusters.cluster_type": "competitor"}},
        {"$match": {"intelligence.entity_sentiments": {"$exists": True}}},
        {"$limit": 200}  # Get more posts to filter from
    ]
    
    cursor = collection.aggregate(pipeline)
    posts = await cursor.to_list(length=200)
    
    # Filter for negative sentiment posts (opportunities)
    opportunity_posts = []
    for post in posts:
        if post.get("intelligence", {}).get("entity_sentiments"):
            for entity, sentiment in post["intelligence"]["entity_sentiments"].items():
                if isinstance(sentiment, dict) and sentiment.get("label") == "Negative":
                    # Format the post
                    post_dict = {
                        "id": str(post["_id"]),
                        "content_type": post.get("content_type", "social_post"),
                        "platform": post.get("platform", "X"),
                        "content": post.get("content", ""),
                        "title": post.get("title", ""),
                        "author": post.get("author", ""),
                        "url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "post_url": post.get("url", "") or f"https://example.com/post/{str(post.get('_id', ''))}",
                        "published_at": post.get("published_at"),
                        "posted_at": post.get("published_at"),
                        "cluster_type": "competitor",
                        "sentiment": "negative",
                        "has_been_responded_to": False,
                        "intelligence": post.get("intelligence", {}),
                        "matched_clusters": post.get("matched_clusters", [])
                    }
                    
                    # Add engagement metrics
                    if post.get("social_metrics"):
                        metrics = post["social_metrics"]
                        post_dict["engagement_metrics"] = {
                            "likes": metrics.get("likes", 0),
                            "shares": metrics.get("shares", 0),
                            "comments": metrics.get("comments", 0),
                            "views": metrics.get("views", 0),
                            "retweets": metrics.get("shares", 0),
                            "replies": metrics.get("comments", 0),
                            "impressions": metrics.get("views", 0)
                        }
                    else:
                        post_dict["engagement_metrics"] = {
                            "likes": 0, "shares": 0, "comments": 0,
                            "views": 0, "retweets": 0, "replies": 0, "impressions": 0
                        }
                    
                    opportunity_posts.append(post_dict)
                    break  # Count each post only once
    
    return opportunity_posts[:limit]

@router.post("/", response_model=SocialPostResponse, status_code=201)
async def create_post(post: SocialPostCreate):
    """Create a new social post"""
    try:
        return await post_service.create_post(post)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
@router.get("", response_model=List[dict])
async def get_posts(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    cluster_id: Optional[str] = None,
    platform: Optional[str] = Query(None, regex="^(X|Facebook|YouTube)$", description="Platform: X, Facebook, or YouTube"),
    is_threat: Optional[bool] = None,
    sentiment_label: Optional[str] = Query(None, regex="^(Positive|Negative|Neutral)$", description="Sentiment label"),
    skip: int = Query(0, ge=0),
    limit: int = Query(2000, ge=1, le=5000)
):
    """Get all posts from posts_table - Enhanced for cluster-based filtering"""
    
    # If cluster_type is provided but not cluster_id, get all clusters of that type
    if cluster_type and not cluster_id:
        clusters = await cluster_service.get_clusters(cluster_type=cluster_type)
        cluster_ids = [cluster.id for cluster in clusters]
    elif cluster_id:
        cluster_ids = [cluster_id]
    else:
        cluster_ids = None
    
    # Build query parameters
    params = PostsQueryParams(
        cluster_id=cluster_ids[0] if cluster_ids and len(cluster_ids) == 1 else None,
        platform=Platform(platform) if platform else None,
        sentiment_label=SentimentLabel(sentiment_label) if sentiment_label else None,
        is_threat=is_threat,
        skip=skip,
        limit=limit
    )
    
    # Get posts from posts_table
    posts_responses = await posts_table_service.query_posts(params)
    
    # Convert to legacy format for frontend compatibility
    posts = []
    for post in posts_responses:
        # Get cluster info to determine cluster_type
        cluster = None
        if post.cluster_id:
            cluster = await cluster_service.get_cluster(post.cluster_id)
        
        post_dict = {
            "id": post.id,
            "platform": post.platform,
            "platform_content_id": post.platform_post_id,
            "title": post.post_text[:50] + "..." if len(post.post_text) > 50 else post.post_text,
            "content": post.post_text,
            "author": post.author_username,
            "url": post.post_url,
            "post_url": post.post_url,
            "published_at": post.posted_at,
            "posted_at": post.posted_at,
            "collected_at": post.fetched_at,
            "cluster_id": post.cluster_id,
            "cluster_type": cluster.cluster_type if cluster else "own",
            "sentiment": post.sentiment_label.lower() if post.sentiment_label else "neutral",
            "has_been_responded_to": post.has_been_responded_to,
            
            # Engagement metrics
            "engagement_metrics": {
                "likes": post.likes,
                "shares": post.shares,
                "comments": post.comments,
                "views": post.views,
                "retweets": post.shares,  # Map shares to retweets for X
                "replies": post.comments,  # Map comments to replies
                "impressions": post.views  # Map views to impressions
            },
            
            # Intelligence data (simplified for posts_table)
            "intelligence": {
                "threat_level": "high" if post.is_threat else "low",
                "entity_sentiments": {
                    "main": {
                        "label": post.sentiment_label or "Neutral",
                        "score": post.sentiment_score,
                        "confidence": 0.8
                    }
                }
            },
            
            # Matched clusters info (for compatibility)
            "matched_clusters": [{
                "cluster_id": post.cluster_id,
                "cluster_type": cluster.cluster_type if cluster else "own",
                "cluster_name": cluster.name if cluster else "Unknown"
            }] if post.cluster_id else []
        }
        
        # Filter by cluster_type if multiple cluster_ids or general cluster_type filter
        if cluster_type and post_dict["cluster_type"] == cluster_type:
            posts.append(post_dict)
        elif not cluster_type:
            posts.append(post_dict)
    
    return posts

@router.get("/threats", response_model=List[dict])
async def get_threat_posts(
    cluster_type: Optional[str] = Query("own", regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get threat posts from posts_table - defaults to own organization threats"""
    # Query for threat posts
    params = PostsQueryParams(
        is_threat=True,
        limit=limit
    )
    
    threat_posts = await posts_table_service.query_posts(params)
    
    # Convert to legacy format
    posts = []
    for post in threat_posts:
        # Get cluster info to determine cluster_type
        cluster = None
        if post.cluster_id:
            cluster = await cluster_service.get_cluster(post.cluster_id)
        
        # Filter by cluster_type if specified
        if cluster_type and cluster and cluster.cluster_type != cluster_type:
            continue
        
        post_dict = {
            "id": post.id,
            "platform": post.platform,
            "content": post.post_text,
            "title": post.post_text[:50] + "..." if len(post.post_text) > 50 else post.post_text,
            "author": post.author_username,
            "url": post.post_url,
            "posted_at": post.posted_at,
            "cluster_type": cluster.cluster_type if cluster else "own",
            "sentiment": post.sentiment_label.lower() if post.sentiment_label else "neutral",
            "intelligence": {
                "threat_level": "high" if post.is_threat else "low",
                "entity_sentiments": {
                    "main": {
                        "label": post.sentiment_label or "Neutral",
                        "score": post.sentiment_score,
                        "confidence": 0.8
                    }
                }
            },
            "engagement_metrics": {
                "likes": post.likes,
                "shares": post.shares,
                "comments": post.comments,
                "views": post.views
            }
        }
        posts.append(post_dict)
    
    return posts

@router.get("/print-magazines", response_model=List[dict])
async def get_print_magazines(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    cluster_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get print magazine articles filtered by cluster keywords"""
    from app.core.database import get_database
    from app.services.cluster_service import ClusterService
    
    db = get_database()
    collection = db.print_magazines
    cluster_service = ClusterService()
    
    # Build query
    query = {}
    
    # If cluster_id is provided, filter by that specific cluster's keywords
    if cluster_id:
        cluster = await cluster_service.get_cluster(cluster_id)
        if cluster:
            cluster_keywords = [k.lower().strip().replace('#', '') for k in cluster.keywords]
            cluster_name = cluster.name.strip()
            
            # Handle name variations (AIADMK vs ADMK)
            if "AIADMK" in cluster_name.upper():
                # Match both ADMK and AIADMK variations
                query["matched_clusters.cluster_name"] = {"$in": ["ADMK", "AIADMK", cluster_name]}
            elif "DMK" in cluster_name.upper():
                query["matched_clusters.cluster_name"] = {"$in": ["DMK", cluster_name]}
            else:
                query["matched_clusters.cluster_name"] = cluster_name
    elif cluster_type:
        # Fallback to cluster_type filtering
        query["matched_clusters.cluster_type"] = cluster_type
    
    # Find print magazines
    cursor = collection.find(query).sort("published_at", -1).limit(limit)
    magazines = await cursor.to_list(length=limit)
    
    # Format response
    formatted_magazines = []
    for mag in magazines:
        formatted_mag = {
            "id": str(mag["_id"]),
            "platform": mag.get("platform", "Print Magazine"),
            "content": mag.get("content", {}),
            "author": mag.get("author", {}),
            "matched_clusters": mag.get("matched_clusters", []),
            "intelligence": mag.get("intelligence", {}),
            "published_at": mag.get("published_at"),
            "collected_at": mag.get("collected_at"),
            "raw_data": mag.get("raw_data", {}),
            # Add fields to match posts structure
            "sentiment": mag.get("intelligence", {}).get("entity_sentiments", {}).get("DMK", {}).get("label", "Neutral") if mag.get("matched_clusters", [{}])[0].get("cluster_name") == "DMK" else mag.get("intelligence", {}).get("entity_sentiments", {}).get("ADMK", {}).get("label", "Neutral"),
            "threat_level": mag.get("intelligence", {}).get("threat_level", "Low"),
            "threat_campaign_topic": mag.get("intelligence", {}).get("threat_campaign_topic", ""),
            "cluster_type": mag.get("matched_clusters", [{}])[0].get("cluster_type", "unknown") if mag.get("matched_clusters") else "unknown",
            "cluster_name": mag.get("matched_clusters", [{}])[0].get("cluster_name", "Unknown") if mag.get("matched_clusters") else "Unknown"
        }
        formatted_magazines.append(formatted_mag)
    
    return formatted_magazines

@router.get("/print-daily", response_model=List[dict])
async def get_print_daily(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    cluster_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get print daily articles filtered by cluster keywords"""
    from app.core.database import get_database
    from app.services.cluster_service import ClusterService
    
    db = get_database()
    collection = db.print_daily
    cluster_service = ClusterService()
    
    # Build query
    query = {}
    
    # If cluster_id is provided, filter by that specific cluster's keywords
    if cluster_id:
        cluster = await cluster_service.get_cluster(cluster_id)
        if cluster:
            cluster_keywords = [k.lower().strip().replace('#', '') for k in cluster.keywords]
            cluster_name = cluster.name.strip()
            
            # Handle name variations (AIADMK vs ADMK)
            if "AIADMK" in cluster_name.upper():
                # Match both ADMK and AIADMK variations
                query["matched_clusters.cluster_name"] = {"$in": ["ADMK", "AIADMK", cluster_name]}
            elif "DMK" in cluster_name.upper():
                query["matched_clusters.cluster_name"] = {"$in": ["DMK", cluster_name]}
            else:
                query["matched_clusters.cluster_name"] = cluster_name
    elif cluster_type:
        # Fallback to cluster_type filtering
        query["matched_clusters.cluster_type"] = cluster_type
    
    # Find print daily articles
    cursor = collection.find(query).sort("published_at", -1).limit(limit)
    daily_articles = await cursor.to_list(length=limit)
    
    # Format response
    formatted_articles = []
    for article in daily_articles:
        formatted_article = {
            "id": str(article["_id"]),
            "platform": article.get("platform", "Print Daily"),
            "publisher": article.get("publisher", "Unknown"),
            "content": article.get("content", {}),
            "author": article.get("author", {}),
            "matched_clusters": article.get("matched_clusters", []),
            "intelligence": article.get("intelligence", {}),
            "published_at": article.get("published_at"),
            "collected_at": article.get("collected_at"),
            "raw_data": article.get("raw_data", {}),
            # Add fields to match posts structure
            "sentiment": article.get("intelligence", {}).get("entity_sentiments", {}).get("DMK", {}).get("label", "Neutral") if article.get("matched_clusters", [{}])[0].get("cluster_name") == "DMK" else article.get("intelligence", {}).get("entity_sentiments", {}).get("ADMK", {}).get("label", "Neutral"),
            "threat_level": article.get("intelligence", {}).get("threat_level", "Low"),
            "threat_campaign_topic": article.get("intelligence", {}).get("threat_campaign_topic", ""),
            "cluster_type": article.get("matched_clusters", [{}])[0].get("cluster_type", "unknown") if article.get("matched_clusters") else "unknown",
            "cluster_name": article.get("matched_clusters", [{}])[0].get("cluster_name", "Unknown") if article.get("matched_clusters") else "Unknown"
        }
        formatted_articles.append(formatted_article)
    
    return formatted_articles

@router.get("/{post_id}", response_model=SocialPostResponse)
async def get_post(post_id: str):
    """Get post by ID"""
    post = await post_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.patch("/{post_id}/respond", status_code=204)
async def mark_post_as_responded(post_id: str):
    """Mark post as responded to"""
    success = await post_service.mark_as_responded(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")

# Platform-specific endpoints
@router.get("/platforms/X", response_model=List[SocialPostResponse])
async def get_x_posts(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get X (Twitter) posts specifically"""
    return await post_service.get_x_posts(cluster_type=cluster_type, limit=limit)

@router.get("/platforms/Facebook", response_model=List[SocialPostResponse])
async def get_facebook_posts(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get Facebook posts specifically"""
    return await post_service.get_facebook_posts(cluster_type=cluster_type, limit=limit)

@router.get("/platforms/YouTube", response_model=List[SocialPostResponse])
async def get_youtube_posts(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get YouTube posts specifically"""
    return await post_service.get_youtube_posts(cluster_type=cluster_type, limit=limit)

# v19.0 Entity-Centric endpoints
@router.get("/entity/{entity_name}/sentiment/{sentiment_label}", response_model=List[SocialPostResponse])
async def get_posts_by_entity_sentiment(
    entity_name: str,
    sentiment_label: str,
    platform: Optional[str] = Query(None, regex="^(X|Facebook|YouTube)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get posts where a specific entity has a specific sentiment (v19.0)"""
    return await post_service.get_posts_by_entity_sentiment(
        entity_name=entity_name,
        sentiment_label=sentiment_label,
        platform=platform,
        limit=limit
    )

@router.get("/high-engagement/{platform}", response_model=List[SocialPostResponse])
async def get_high_engagement_posts(
    platform: str,
    engagement_threshold: int = Query(100, ge=1),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get posts with high engagement metrics by platform"""
    return await post_service.get_high_engagement_posts(
        platform=platform,
        engagement_threshold=engagement_threshold,
        limit=limit
    )

@router.post("/fix-cluster-types")
async def fix_cluster_types():
    """Fix incorrect cluster types in existing posts"""
    try:
        fixed_count = await post_service.fix_cluster_types()
        return {"fixed_count": fixed_count, "status": "completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

