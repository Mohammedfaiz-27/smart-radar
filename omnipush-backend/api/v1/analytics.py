from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import logging
import random
from collections import defaultdict

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.analytics import (
    GetPostAnalyticsResponse,
    GetDashboardResponse,
    GetInsightsResponse,
    DateRange,
    PostMetrics,
    PlatformMetrics,
    DashboardOverview,
    PlatformPerformance,
    TopPerformingPost,
    EngagementTrend,
    Insight,
    InsightType,
    Demographics,
    EngagementPatterns,
    AudienceInsights
)
from models.content import Platform

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics & reporting"])


def get_date_range_dates(date_range: DateRange) -> tuple[datetime, datetime]:
    """Convert date range enum to actual start and end dates"""
    end_date = datetime.utcnow()
    
    if date_range == DateRange.LAST_7_DAYS:
        start_date = end_date - timedelta(days=7)
    elif date_range == DateRange.LAST_30_DAYS:
        start_date = end_date - timedelta(days=30)
    elif date_range == DateRange.LAST_90_DAYS:
        start_date = end_date - timedelta(days=90)
    elif date_range == DateRange.THIS_MONTH:
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_range == DateRange.LAST_MONTH:
        # First day of last month
        first_this_month = end_date.replace(day=1)
        start_date = (first_this_month - timedelta(days=1)).replace(day=1)
        # Last day of last month
        end_date = first_this_month - timedelta(seconds=1)
    else:
        # Default to last 30 days
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date


async def fetch_platform_analytics(
    post_id: str,
    platform: Platform,
    tenant_id: str
) -> PlatformMetrics:
    """
    Fetch analytics data from platform APIs
    In production, this would integrate with actual platform analytics APIs
    """
    # Mock data for demonstration
    # In production, you would make API calls to:
    # - Facebook Graph API for Facebook/Instagram insights
    # - Twitter API v2 for Twitter analytics
    # - LinkedIn API for LinkedIn analytics
    # etc.
    
    # Generate realistic mock data
    reach = random.randint(1000, 50000)
    engagement = random.randint(50, reach // 10)
    likes = random.randint(20, engagement // 2)
    comments = random.randint(5, engagement // 5)
    clicks = random.randint(10, engagement // 3)
    shares = random.randint(0, engagement // 8) if platform != Platform.INSTAGRAM else None
    
    return PlatformMetrics(
        platform=platform,
        reach=reach,
        engagement=engagement,
        likes=likes,
        shares=shares,
        comments=comments,
        clicks=clicks
    )


async def calculate_post_analytics(
    post_id: str,
    tenant_id: str,
    ctx: TenantContext
) -> tuple[PostMetrics, List[PlatformMetrics]]:
    """Calculate overall metrics and platform breakdown for a post"""
    
    # Get post details to know which platforms it was published to
    post_response = ctx.table('posts').select('channels, status').eq(
        'tenant_id', ctx.tenant_id
    ).eq('id', post_id).maybe_single().execute()
    
    if not post_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    post = post_response.data
    
    # Check if post was published
    if post['status'] != 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post was not published - no analytics available"
        )
    
    # Fetch analytics from each platform
    platform_metrics = []
    total_reach = 0
    total_engagement = 0
    total_clicks = 0
    
    for channel in post['channels']:
        platform = Platform(channel['platform'])
        metrics = await fetch_platform_analytics(post_id, platform, tenant_id)
        platform_metrics.append(metrics)
        
        total_reach += metrics.reach
        total_engagement += metrics.engagement
        total_clicks += metrics.clicks
    
    # Calculate overall engagement rate
    engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
    
    overall_metrics = PostMetrics(
        total_reach=total_reach,
        total_engagement=total_engagement,
        engagement_rate=round(engagement_rate, 2),
        clicks=total_clicks
    )
    
    return overall_metrics, platform_metrics


@router.get("/posts/{post_id}", response_model=GetPostAnalyticsResponse)
async def get_post_performance(
    post_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get performance analytics for a specific post"""
    try:
        overall_metrics, platform_breakdown = await calculate_post_analytics(
            post_id, current_user.tenant_id, ctx
        )
        
        return GetPostAnalyticsResponse(
            post_id=post_id,
            overall_metrics=overall_metrics,
            platform_breakdown=platform_breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get post analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve post analytics"
        )


@router.get("/dashboard", response_model=GetDashboardResponse)
async def get_dashboard_analytics(
    date_range: DateRange = Query(DateRange.LAST_30_DAYS),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get dashboard analytics overview"""
    try:
        start_date, end_date = get_date_range_dates(date_range)
        
        # Get published posts in date range
        posts_response = ctx.table('posts').select(
            'id, title, channels, published_at'
        ).eq('tenant_id', ctx.tenant_id).eq('status', 'published').gte(
            'published_at', start_date.isoformat()
        ).lte('published_at', end_date.isoformat()).execute()
        
        published_posts = posts_response.data or []
        
        # Aggregate platform data
        platform_stats = defaultdict(lambda: {
            'posts': 0,
            'total_reach': 0,
            'total_engagement': 0
        })
        
        top_posts = []
        total_reach = 0
        total_engagement = 0
        
        # Calculate metrics for each post
        for post in published_posts:
            # Generate mock metrics for each platform
            post_reach = 0
            post_engagement = 0
            
            for channel in post['channels']:
                platform = channel['platform']
                platform_stats[platform]['posts'] += 1
                
                # Generate mock metrics
                reach = random.randint(500, 10000)
                engagement = random.randint(25, reach // 10)
                
                platform_stats[platform]['total_reach'] += reach
                platform_stats[platform]['total_engagement'] += engagement
                
                post_reach += reach
                post_engagement += engagement
            
            total_reach += post_reach
            total_engagement += post_engagement
            
            # Add to top posts (we'll sort later)
            top_posts.append(TopPerformingPost(
                post_id=post['id'],
                title=post['title'],
                engagement=post_engagement,
                reach=post_reach
            ))
        
        # Calculate overall metrics
        avg_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
        
        overview = DashboardOverview(
            total_posts=len(published_posts),
            total_reach=total_reach,
            total_engagement=total_engagement,
            avg_engagement_rate=round(avg_engagement_rate, 2)
        )
        
        # Build platform performance list
        platform_performance = []
        for platform_name, stats in platform_stats.items():
            engagement_rate = (stats['total_engagement'] / stats['total_reach'] * 100) if stats['total_reach'] > 0 else 0
            platform_performance.append(PlatformPerformance(
                platform=Platform(platform_name),
                posts=stats['posts'],
                reach=stats['total_reach'],
                engagement=stats['total_engagement'],
                engagement_rate=round(engagement_rate, 2)
            ))
        
        # Sort top posts by engagement and limit to top 10
        top_posts.sort(key=lambda x: x.engagement, reverse=True)
        top_posts = top_posts[:10]
        
        # Generate engagement trends (mock data)
        engagement_trends = []
        current_date = start_date.date()
        end_date_date = end_date.date()
        
        while current_date <= end_date_date:
            # Mock daily engagement
            daily_engagement = random.randint(100, 1000)
            engagement_trends.append(EngagementTrend(
                date=current_date,
                engagement=daily_engagement
            ))
            current_date += timedelta(days=1)
        
        return GetDashboardResponse(
            overview=overview,
            platform_performance=platform_performance,
            top_performing_posts=top_posts,
            engagement_trends=engagement_trends
        )
        
    except Exception as e:
        logger.exception(f"Failed to get dashboard analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard analytics"
        )


@router.get("/insights", response_model=GetInsightsResponse)
async def get_insights_and_recommendations(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get AI-powered insights and recommendations"""
    try:
        # In production, this would analyze actual data to generate insights
        # For demo, we'll return realistic mock insights
        
        insights = [
            Insight(
                type=InsightType.BEST_POSTING_TIME,
                platform=Platform.INSTAGRAM,
                recommendation="Posts perform 40% better when published at 2 PM on weekdays",
                confidence=0.85
            ),
            Insight(
                type=InsightType.CONTENT_TYPE,
                recommendation="Video posts generate 60% more engagement than image posts",
                confidence=0.92
            ),
            Insight(
                type=InsightType.AUDIENCE_GROWTH,
                platform=Platform.FACEBOOK,
                recommendation="Your Facebook audience is growing 15% faster on weekends",
                confidence=0.78
            ),
            Insight(
                type=InsightType.ENGAGEMENT_PATTERN,
                recommendation="Posts with questions in captions receive 35% more comments",
                confidence=0.88
            )
        ]
        
        # Mock audience insights
        demographics = Demographics(
            age_groups={
                "18-24": 0.25,
                "25-34": 0.35,
                "35-44": 0.30,
                "45+": 0.10
            },
            top_locations=["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
        )
        
        engagement_patterns = EngagementPatterns(
            best_days=["Tuesday", "Wednesday", "Thursday"],
            best_hours=[14, 15, 19, 20]  # 2 PM, 3 PM, 7 PM, 8 PM
        )
        
        audience_insights = AudienceInsights(
            demographics=demographics,
            engagement_patterns=engagement_patterns
        )
        
        return GetInsightsResponse(
            insights=insights,
            audience_insights=audience_insights
        )
        
    except Exception as e:
        logger.exception(f"Failed to get insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve insights"
        )


@router.get("/export")
async def export_analytics_data(
    date_range: DateRange = Query(DateRange.LAST_30_DAYS),
    format: str = Query("csv", regex="^(csv|json|xlsx)$"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Export analytics data in various formats"""
    try:
        start_date, end_date = get_date_range_dates(date_range)
        
        # Get posts data
        posts_response = ctx.table('posts').select(
            'id, title, channels, status, published_at, created_at'
        ).gte('created_at', start_date.isoformat()).lte(
            'created_at', end_date.isoformat()
        ).execute()
        
        posts_data = []
        for post in posts_response.data or []:
            # Generate mock analytics for export
            reach = random.randint(1000, 10000)
            engagement = random.randint(50, reach // 10)
            
            posts_data.append({
                "post_id": post['id'],
                "title": post['title'],
                "status": post['status'],
                "platforms": [ch['platform'] for ch in post['channels']],
                "published_at": post.get('published_at'),
                "reach": reach,
                "engagement": engagement,
                "engagement_rate": round(engagement / reach * 100, 2) if reach > 0 else 0
            })
        
        if format == "json":
            from fastapi.responses import JSONResponse
            return JSONResponse(content={
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "posts": posts_data
            })
        
        elif format == "csv":
            import csv
            import io
            from fastapi.responses import StreamingResponse
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'post_id', 'title', 'status', 'platforms', 'published_at',
                'reach', 'engagement', 'engagement_rate'
            ])
            
            writer.writeheader()
            for post in posts_data:
                # Convert platforms list to string for CSV
                post['platforms'] = ', '.join(post['platforms'])
                writer.writerow(post)
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=analytics_{date_range.value}.csv"}
            )
        
        else:
            # For xlsx format, you would use openpyxl or xlsxwriter
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="XLSX export not implemented in demo"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to export analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export analytics data"
        )


@router.get("/compare")
async def compare_periods(
    current_period: DateRange = Query(DateRange.LAST_30_DAYS),
    comparison_period: DateRange = Query(DateRange.LAST_30_DAYS),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Compare analytics between two time periods"""
    try:
        # Get date ranges
        current_start, current_end = get_date_range_dates(current_period)
        
        # For comparison period, offset by the same duration
        period_duration = current_end - current_start
        comparison_end = current_start - timedelta(seconds=1)
        comparison_start = comparison_end - period_duration
        
        # Get posts for both periods
        current_posts = ctx.table('posts').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('status', 'published').gte('published_at', current_start.isoformat()).lte(
            'published_at', current_end.isoformat()
        ).execute().data or []
        
        comparison_posts = ctx.table('posts').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('status', 'published').gte('published_at', comparison_start.isoformat()).lte(
            'published_at', comparison_end.isoformat()
        ).execute().data or []
        
        # Calculate metrics for both periods
        def calculate_period_metrics(posts):
            total_posts = len(posts)
            total_reach = sum(random.randint(1000, 10000) for _ in posts)
            total_engagement = sum(random.randint(50, 500) for _ in posts)
            avg_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
            
            return {
                "posts": total_posts,
                "reach": total_reach,
                "engagement": total_engagement,
                "engagement_rate": round(avg_engagement_rate, 2)
            }
        
        current_metrics = calculate_period_metrics(current_posts)
        comparison_metrics = calculate_period_metrics(comparison_posts)
        
        # Calculate percentage changes
        def calculate_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round((current - previous) / previous * 100, 2)
        
        changes = {
            "posts": calculate_change(current_metrics["posts"], comparison_metrics["posts"]),
            "reach": calculate_change(current_metrics["reach"], comparison_metrics["reach"]),
            "engagement": calculate_change(current_metrics["engagement"], comparison_metrics["engagement"]),
            "engagement_rate": calculate_change(current_metrics["engagement_rate"], comparison_metrics["engagement_rate"])
        }
        
        return {
            "current_period": {
                "start": current_start.isoformat(),
                "end": current_end.isoformat(),
                "metrics": current_metrics
            },
            "comparison_period": {
                "start": comparison_start.isoformat(),
                "end": comparison_end.isoformat(),
                "metrics": comparison_metrics
            },
            "changes": changes
        }
        
    except Exception as e:
        logger.exception(f"Failed to compare periods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare analytics periods"
        )