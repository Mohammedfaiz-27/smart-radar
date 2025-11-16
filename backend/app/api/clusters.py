"""
Cluster management API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.models.cluster import ClusterCreate, ClusterUpdate, ClusterResponse
from app.services.cluster_service import ClusterService
from app.services.posts_table_service import PostsTableService
from app.models.posts_table import PostsQueryParams, Platform, SentimentLabel

router = APIRouter()
cluster_service = ClusterService()
posts_table_service = PostsTableService()

@router.post("/", response_model=ClusterResponse, status_code=201)
@router.post("", response_model=ClusterResponse, status_code=201)
async def create_cluster(cluster: ClusterCreate):
    """Create a new cluster and trigger initial data collection"""
    try:
        # Create the cluster
        created_cluster = await cluster_service.create_cluster(cluster)

        # Trigger initial data collection for the new cluster in the background
        # Only if cluster is active
        if created_cluster.is_active:
            import asyncio
            from app.services.pipeline_orchestrator import PipelineOrchestrator

            async def collect_new_cluster():
                """Background task to collect data for newly created cluster"""
                try:
                    await asyncio.sleep(2)  # Small delay to ensure cluster is fully created
                    orchestrator = PipelineOrchestrator()
                    result = await orchestrator.collect_and_process_cluster(
                        cluster_id=created_cluster.id,
                        save_to_social_posts=True,
                        save_to_posts_table=True
                    )
                    print(f"✅ Initial collection for new cluster '{created_cluster.name}': {result.get('total_posts_collected', 0)} posts")
                except Exception as e:
                    print(f"⚠️ Error in initial collection for cluster '{created_cluster.name}': {e}")

            # Launch background task
            asyncio.create_task(collect_new_cluster())

        return created_cluster
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[ClusterResponse])
@router.get("", response_model=List[ClusterResponse])
async def get_clusters(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all clusters with optional filters"""
    return await cluster_service.get_clusters(
        cluster_type=cluster_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )

@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: str):
    """Get cluster by ID"""
    cluster = await cluster_service.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.put("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(cluster_id: str, cluster_update: ClusterUpdate):
    """Update cluster by ID"""
    cluster = await cluster_service.update_cluster(cluster_id, cluster_update)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.delete("/{cluster_id}", status_code=204)
async def delete_cluster(cluster_id: str):
    """Delete cluster by ID"""
    success = await cluster_service.delete_cluster(cluster_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cluster not found")

@router.get("/{cluster_id}/posts", response_model=List[dict])
async def get_cluster_posts(
    cluster_id: str,
    platform: Optional[str] = Query(None, regex="^(X|Facebook|YouTube|web_news)$", description="Platform: X, Facebook, YouTube, or web_news"),
    is_threat: Optional[bool] = None,
    sentiment_label: Optional[str] = Query(None, regex="^(Positive|Negative|Neutral)$", description="Sentiment label"),
    skip: int = Query(0, ge=0),
    limit: int = Query(2000, ge=1, le=5000)
):
    """Get all posts for a specific cluster - includes web news from news_articles when platform=web_news"""
    
    # Verify cluster exists
    cluster = await cluster_service.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # If requesting web_news, fetch from news_articles collection
    if platform == "web_news":
        from app.core.database import get_database
        
        db = get_database()
        news_collection = db.news_articles
        
        # Build query for news_articles
        news_query = {
            "matched_clusters.cluster_id": cluster_id
        }
        
        # Add sentiment filter if specified
        if sentiment_label:
            # Map sentiment labels for news (stored in intelligence.entity_sentiments)
            if sentiment_label == "Positive":
                news_query["intelligence.threat_level"] = {"$in": ["low"]}
            elif sentiment_label == "Negative":
                news_query["intelligence.threat_level"] = {"$in": ["high", "critical"]}
            # For Neutral, no additional filter needed
        
        # Add threat filter if specified
        if is_threat is not None:
            if is_threat:
                news_query["intelligence.threat_level"] = {"$in": ["high", "critical"]}
            else:
                news_query["intelligence.threat_level"] = {"$in": ["low", "medium"]}
        
        # Execute query on news_articles
        cursor = news_collection.find(news_query).sort("published_at", -1).skip(skip).limit(limit)
        news_articles = await cursor.to_list(length=limit)
        
        # Convert news articles to posts format
        posts = []
        for article in news_articles:
            # Extract sentiment from intelligence - improved mapping for web news
            threat_level = article.get("intelligence", {}).get("threat_level", "low")
            
            # Analyze title and content for better sentiment detection
            title = article.get("title", "").lower()
            content = article.get("summary", "").lower()
            text_content = f"{title} {content}"
            
            # More balanced sentiment mapping for news articles
            if threat_level == "low":
                # For low threat, analyze content for actual sentiment
                negative_words = ["crisis", "concern", "problem", "issue", "controversy", "scandal", "allegation", "protest", "opposition", "criticism", "attack", "failure", "decline", "loss", "damage"]
                positive_words = ["success", "achievement", "progress", "improvement", "victory", "celebration", "launch", "inauguration", "development", "growth", "benefit", "support", "praise", "award"]
                
                negative_count = sum(1 for word in negative_words if word in text_content)
                positive_count = sum(1 for word in positive_words if word in text_content)
                
                if negative_count > positive_count:
                    sentiment = "negative"
                elif positive_count > negative_count:
                    sentiment = "positive"
                else:
                    sentiment = "neutral"
            else:
                # Use original mapping for higher threat levels
                sentiment_map = {
                    "medium": "neutral", 
                    "high": "negative",
                    "critical": "negative"
                }
                sentiment = sentiment_map.get(threat_level, "neutral")
            
            post_dict = {
                "id": str(article["_id"]),
                "platform": "web_news",
                "platform_content_id": str(article["_id"]),
                "title": article.get("title", "")[:50] + "..." if len(article.get("title", "")) > 50 else article.get("title", ""),
                "content": article.get("content", "") or article.get("summary", ""),
                "author": article.get("source", "Unknown Source"),  # Use source as author for news
                "url": article.get("url", ""),
                "post_url": article.get("url", ""),
                "published_at": article.get("published_at"),
                "posted_at": article.get("published_at"),
                "collected_at": article.get("collected_at"),
                "cluster_id": cluster_id,
                "cluster_type": cluster.cluster_type,
                "sentiment": sentiment,
                "has_been_responded_to": False,  # News articles don't have response tracking
                
                # No engagement metrics for news
                "engagement_metrics": {
                    "likes": 0,
                    "shares": 0,
                    "comments": 0,
                    "views": 0,
                    "retweets": 0,
                    "replies": 0,
                    "impressions": 0
                },
                
                # Use news intelligence data
                "intelligence": article.get("intelligence", {}),
                
                # Matched clusters info
                "matched_clusters": article.get("matched_clusters", [])
            }
            
            posts.append(post_dict)
        
        return posts
    
    # For social media platforms, use existing logic
    # Build query parameters
    params = PostsQueryParams(
        cluster_id=cluster_id,
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
            "cluster_type": cluster.cluster_type,
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
                "cluster_type": cluster.cluster_type,
                "cluster_name": cluster.name
            }]
        }
        
        posts.append(post_dict)
    
    return posts