#!/usr/bin/env python3
"""
Fetch data from working platforms (X and YouTube)
"""
import asyncio
import os
from dotenv import load_dotenv
from app.collectors import XCollector, YouTubeCollector
from app.services.posts_table_service import PostsTableService
from app.services.social_post_service import SocialPostService
from app.services.cluster_service import ClusterService
from app.core.database import connect_to_mongo, close_mongo_connection
from app.models.cluster import PlatformConfig
from app.models.social_post import SocialPostCreate
from app.models.common import IntelligenceV19, ClusterMatch

load_dotenv()

async def fetch_from_working_platforms(cluster_id: str = None):
    """Fetch data from X and YouTube only"""
    try:
        await connect_to_mongo()
        print("✓ Connected to MongoDB")
        
        # Initialize services
        cluster_service = ClusterService()
        posts_service = PostsTableService()
        social_post_service = SocialPostService()
        
        # Get cluster
        if cluster_id:
            cluster = await cluster_service.get_cluster(cluster_id)
            if not cluster:
                print(f"Cluster {cluster_id} not found")
                return
            clusters = [cluster]
        else:
            clusters = await cluster_service.get_clusters(is_active=True)
            if not clusters:
                print("No active clusters found")
                return
        
        print(f"Processing {len(clusters)} cluster(s)")
        
        total_collected = 0
        
        for cluster in clusters:
            print(f"\n{'='*60}")
            print(f"Cluster: {cluster.name}")
            print(f"Keywords: {cluster.keywords}")
            print(f"{'='*60}")
            
            # Default platform config
            config = PlatformConfig(max_results=10)  # Limit for testing
            
            # Collect from X
            print("\n--- X (Twitter) ---")
            x_collector = XCollector()
            x_posts = 0
            
            async with x_collector:
                for keyword in cluster.keywords[:2]:  # Limit keywords for testing
                    print(f"  Searching for: {keyword}")
                    try:
                        count = 0
                        async for raw_post in x_collector.search(keyword, config, max_results=5):
                            try:
                                # Parse post
                                post = x_collector.parse_post(raw_post, cluster.id)
                                
                                # Save to posts_table
                                saved = await posts_service.create_post(post)
                                if saved:
                                    x_posts += 1
                                    count += 1
                                    print(f"    ✓ Saved: {post.post_text[:50]}...")
                                    
                                    # Also save to social_posts for backward compatibility
                                    intelligence = IntelligenceV19(
                                        relational_summary=f"Post about {keyword}",
                                        entity_sentiments={},
                                        threat_level="low"
                                    )
                                    
                                    cluster_match = ClusterMatch(
                                        cluster_id=str(cluster.id),
                                        cluster_name=cluster.name,
                                        cluster_type=cluster.cluster_type,
                                        keywords_matched=[keyword]
                                    )
                                    
                                    social_post = SocialPostCreate(
                                        platform="X",
                                        author=post.author_username,
                                        content=post.post_text,
                                        post_url=post.post_url,
                                        posted_at=post.posted_at,
                                        engagement_metrics={
                                            "likes": post.likes,
                                            "comments": post.comments,
                                            "shares": post.shares,
                                            "views": post.views
                                        },
                                        intelligence=intelligence,
                                        matched_clusters=[cluster_match]
                                    )
                                    try:
                                        await social_post_service.create_post(social_post)
                                    except Exception as e:
                                        print(f"    Error saving to social_posts: {e}")
                                    
                            except Exception as e:
                                print(f"    Error processing post: {e}")
                                
                        print(f"    Collected {count} posts for '{keyword}'")
                        
                    except Exception as e:
                        print(f"    Error searching X: {e}")
            
            print(f"  Total X posts: {x_posts}")
            
            # Collect from YouTube
            print("\n--- YouTube ---")
            youtube_collector = YouTubeCollector()
            youtube_posts = 0
            
            async with youtube_collector:
                for keyword in cluster.keywords[:2]:  # Limit keywords for testing
                    print(f"  Searching for: {keyword}")
                    try:
                        count = 0
                        async for raw_video in youtube_collector.search(keyword, config, max_results=3):
                            try:
                                # Parse video
                                post = youtube_collector.parse_post(raw_video, cluster.id)
                                
                                # Save to posts_table
                                saved = await posts_service.create_post(post)
                                if saved:
                                    youtube_posts += 1
                                    count += 1
                                    print(f"    ✓ Saved: {post.post_text[:50]}...")
                                    
                                    # Also save to social_posts
                                    intelligence = IntelligenceV19(
                                        relational_summary=f"Video about {keyword}",
                                        entity_sentiments={},
                                        threat_level="low"
                                    )
                                    
                                    cluster_match = ClusterMatch(
                                        cluster_id=str(cluster.id),
                                        cluster_name=cluster.name,
                                        cluster_type=cluster.cluster_type,
                                        keywords_matched=[keyword]
                                    )
                                    
                                    social_post = SocialPostCreate(
                                        platform="YouTube",
                                        author=post.author_username,
                                        content=post.post_text,
                                        post_url=post.post_url,
                                        posted_at=post.posted_at,
                                        engagement_metrics={
                                            "likes": post.likes,
                                            "comments": post.comments,
                                            "shares": post.shares,
                                            "views": post.views
                                        },
                                        intelligence=intelligence,
                                        matched_clusters=[cluster_match]
                                    )
                                    try:
                                        await social_post_service.create_post(social_post)
                                    except Exception as e:
                                        print(f"    Error saving to social_posts: {e}")
                                    
                            except Exception as e:
                                print(f"    Error processing video: {e}")
                                
                        print(f"    Collected {count} videos for '{keyword}'")
                        
                    except Exception as e:
                        print(f"    Error searching YouTube: {e}")
            
            print(f"  Total YouTube posts: {youtube_posts}")
            
            cluster_total = x_posts + youtube_posts
            print(f"\n✓ Cluster total: {cluster_total} posts")
            total_collected += cluster_total
        
        print(f"\n{'='*60}")
        print(f"COLLECTION COMPLETE")
        print(f"Total posts collected: {total_collected}")
        print(f"{'='*60}")
        
        return total_collected
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0
        
    finally:
        await close_mongo_connection()
        print("\n✓ Disconnected from MongoDB")

async def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description='Fetch from working platforms')
    parser.add_argument('--cluster-id', help='Specific cluster ID')
    args = parser.parse_args()
    
    await fetch_from_working_platforms(args.cluster_id)

if __name__ == "__main__":
    asyncio.run(main())