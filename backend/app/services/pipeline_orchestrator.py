"""
Pipeline orchestrator for coordinating data collection, processing, and storage
Manages the complete flow from API collection to database storage
"""
import asyncio
import os
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

from app.collectors import XCollector, FacebookCollector, YouTubeCollector
from app.collectors.google_news_collector import GoogleNewsCollector
from app.services.llm_processing_service import LLMProcessingService
from app.services.posts_table_service import PostsTableService
from app.services.raw_data_service import RawDataService
from app.services.social_post_service import SocialPostService
from app.services.cluster_service import ClusterService
from app.models.posts_table import PostCreate, Platform
from app.models.raw_data import RawDataCreate, ProcessingStatus
from app.models.cluster import DashboardType

class PipelineOrchestrator:
    """Orchestrates the complete data collection and processing pipeline"""
    
    def __init__(self):
        """Initialize pipeline components"""
        # Collectors
        self.x_collector = XCollector()
        self.facebook_collector = FacebookCollector()
        self.youtube_collector = YouTubeCollector()
        self.google_news_collector = GoogleNewsCollector()
        
        # Services
        self.llm_service = LLMProcessingService()
        self.posts_service = PostsTableService()
        self.raw_data_service = RawDataService()
        self.social_post_service = SocialPostService()  # For backward compatibility
        self.cluster_service = ClusterService()
        
        # Collector mapping
        self.collectors = {
            "x": self.x_collector,
            "facebook": self.facebook_collector,
            "youtube": self.youtube_collector,
            "google_news": self.google_news_collector
        }
    
    async def collect_and_process_cluster(
        self,
        cluster_id: str,
        save_to_social_posts: bool = True,
        save_to_posts_table: bool = True
    ) -> Dict[str, Any]:
        """
        Collect and process data for a specific cluster
        
        Args:
            cluster_id: Cluster ID to process
            save_to_social_posts: Save to social_posts collection (backward compatibility)
            save_to_posts_table: Save to new posts_table
            
        Returns:
            Summary of collection results
        """
        print(f"\n{'='*60}")
        print(f"Starting data collection for cluster: {cluster_id}")
        print(f"{'='*60}")
        
        # Get cluster configuration
        cluster = await self.cluster_service.get_cluster(cluster_id)
        if not cluster:
            return {"error": f"Cluster {cluster_id} not found"}
        
        print(f"Cluster: {cluster.name}")
        print(f"Type: {cluster.cluster_type} / Dashboard: {cluster.dashboard_type if hasattr(cluster, 'dashboard_type') else 'N/A'}")
        print(f"Keywords: {cluster.keywords}")
        
        results = {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "platforms": {},
            "total_posts_collected": 0,
            "total_posts_processed": 0,
            "errors": []
        }
        
        # Get platform configuration
        platform_config = getattr(cluster, 'platform_config', None)

        # Collect from all platforms IN PARALLEL for speed
        async def collect_platform(platform_name, collector):
            """Collect from a single platform"""
            print(f"\n--- Collecting from {platform_name.upper()} ---")

            # Get platform-specific config
            if platform_config:
                config = getattr(platform_config, platform_name, None)
                if config:
                    if not config.enabled:
                        print(f"⏸️ Skipping {platform_name} (disabled in configuration)")
                        return None
                    else:
                        print(f"✅ {platform_name} enabled")
                else:
                    # Platform not configured, use default config
                    from app.models.cluster import PlatformConfig
                    config = PlatformConfig()
                    print(f"✅ {platform_name} using default config (not configured)")
            else:
                # No platform config at all, use default
                from app.models.cluster import PlatformConfig
                config = PlatformConfig()
                print(f"✅ {platform_name} using default config (no platform_config)")

            platform_success = False

            try:
                print(f"🔄 Starting {platform_name} collection...")
                
                # Collect raw data
                async with collector:
                    raw_entries = await collector.collect_for_cluster(
                        cluster_id=cluster_id,
                        keywords=cluster.keywords,
                        platform_config=config,
                        save_raw=True
                    )
                
                print(f"📥 Collected {len(raw_entries)} raw entries from {platform_name}")
                
                # Save raw data
                if raw_entries:
                    saved_raw = await self.raw_data_service.bulk_create(raw_entries)
                    print(f"💾 Saved {len(saved_raw)} raw data entries")
                else:
                    print(f"⚠️ No raw data collected from {platform_name}")
                
                # Process and save posts
                platform_posts = 0
                platform_processed = 0
                
                for raw_entry in raw_entries:
                    try:
                        # Parse post from raw data
                        post = collector.parse_post(raw_entry.raw_json, cluster_id)

                        if post:
                            # Get all active clusters for multi-entity analysis
                            active_clusters = await self.cluster_service.get_clusters(is_active=True)
                            cluster_data = [
                                {
                                    "id": c.id,
                                    "name": c.name,
                                    "keywords": c.keywords,
                                    "cluster_type": c.cluster_type
                                }
                                for c in active_clusters
                            ]

                            # Perform multi-entity sentiment analysis
                            entity_analysis = await self.llm_service.analyze_post_multi_entity(
                                post_text=post.post_text,
                                platform=post.platform.value,
                                author=post.author_username,
                                active_clusters=cluster_data
                            )

                            # Extract entity data
                            entity_sentiments = entity_analysis.get("entity_sentiments", {})
                            comparative = entity_analysis.get("comparative_analysis", {})
                            detected_entities = entity_analysis.get("detected_entities", [])
                            overall = entity_analysis.get("overall_analysis", {})

                            # Store ALL entity sentiments in post
                            post.entity_sentiments = entity_sentiments
                            post.comparative_analysis = comparative

                            # Determine primary cluster name (the cluster that collected this post)
                            primary_cluster_name = None
                            for c in cluster_data:
                                if c["id"] == cluster_id:
                                    primary_cluster_name = c["name"]
                                    break

                            # Calculate overall sentiment from PRIMARY cluster's entity sentiment
                            if primary_cluster_name and primary_cluster_name in entity_sentiments:
                                # Use PRIMARY entity's sentiment as overall sentiment
                                primary_sentiment = entity_sentiments[primary_cluster_name]
                                post.sentiment_score = primary_sentiment.get("score", 0.0)
                                post.sentiment_label = self._determine_label_from_score(primary_sentiment.get("score", 0.0))
                                print(f"   📊 Primary entity: {primary_cluster_name} (score: {post.sentiment_score:.2f})")
                            else:
                                # Fallback: average all entity sentiments
                                if entity_sentiments:
                                    avg_score = sum(e.get("score", 0.0) for e in entity_sentiments.values()) / len(entity_sentiments)
                                    post.sentiment_score = avg_score
                                    post.sentiment_label = self._determine_label_from_score(avg_score)
                                else:
                                    post.sentiment_score = 0.0
                                    post.sentiment_label = SentimentLabel.NEUTRAL

                            # Set threat data from overall analysis
                            post.is_threat = overall.get("overall_threat_score", 0.0) > 0.5
                            post.threat_level = overall.get("overall_threat_level", "None")
                            post.threat_score = overall.get("overall_threat_score", 0.0)
                            post.language = overall.get("language", "Unknown")
                            post.key_narratives = overall.get("key_themes", [])
                            post.llm_analysis = entity_analysis  # Store full multi-entity analysis

                            # Log detected entities
                            if detected_entities:
                                print(f"   🎯 Detected entities: {', '.join(detected_entities)}")

                            # Only process Tamil, English, and Tanglish posts - DELETE others
                            allowed_languages = ['en', 'english', 'tamil', 'tanglish', 'mixed', 'unknown']
                            if post.language and post.language.lower() not in allowed_languages:
                                print(f"🗑️  Deleting {post.language} post: {post.post_text[:50]}...")
                                # Delete from raw_data if it was saved
                                try:
                                    await self.raw_data_service.delete_by_id(raw_entry.id)
                                    print(f"   ✓ Deleted raw_data entry: {raw_entry.id}")
                                except Exception as e:
                                    print(f"   ⚠️ Could not delete raw_data: {e}")
                                continue

                            # Save to posts_table
                            if save_to_posts_table:
                                saved_post = await self.posts_service.create_post(post)
                                if saved_post:
                                    platform_posts += 1
                                    platform_processed += 1
                                    print(f"✓ Saved {platform_name} post: {saved_post.id} - {post.post_text[:50]}...")

                            # Also save to social_posts for backward compatibility
                            if save_to_social_posts:
                                await self._save_to_social_posts(post, cluster)
                            
                    except Exception as e:
                        print(f"❌ Error processing {platform_name} post: {e}")
                        results["errors"].append(f"{platform_name} post processing: {str(e)}")
                        continue
                
                results["platforms"][platform_name] = {
                    "raw_collected": len(raw_entries),
                    "posts_saved": platform_posts,
                    "posts_processed": platform_processed
                }
                
                results["total_posts_collected"] += platform_posts
                results["total_posts_processed"] += platform_processed
                
                platform_success = True
                print(f"✅ {platform_name} collection completed: {platform_posts} posts, {platform_processed} processed")
                return results["platforms"][platform_name]

            except Exception as e:
                print(f"❌ Error collecting from {platform_name}: {e}")
                import traceback
                traceback.print_exc()
                error_result = {
                    "error": str(e),
                    "raw_collected": 0,
                    "posts_saved": 0,
                    "posts_processed": 0
                }
                results["errors"].append(f"{platform_name} collection: {str(e)}")
                return error_result

        # Execute all platform collections IN PARALLEL
        print("\n🚀 Starting PARALLEL collection from all platforms...")
        platform_tasks = [
            collect_platform(platform_name, collector)
            for platform_name, collector in self.collectors.items()
        ]

        # Wait for all platforms to complete
        platform_results = await asyncio.gather(*platform_tasks, return_exceptions=True)

        # Process results
        for platform_name, platform_result in zip(self.collectors.keys(), platform_results):
            if isinstance(platform_result, Exception):
                print(f"⚠️ {platform_name} failed with exception: {platform_result}")
                results["errors"].append(f"{platform_name}: {str(platform_result)}")
                results["platforms"][platform_name] = {
                    "error": str(platform_result),
                    "raw_collected": 0,
                    "posts_saved": 0,
                    "posts_processed": 0
                }
            elif platform_result:
                results["platforms"][platform_name] = platform_result
                results["total_posts_collected"] += platform_result.get("raw_collected", 0)
                results["total_posts_processed"] += platform_result.get("posts_processed", 0)
                print(f"📊 {platform_name} statistics updated")
            else:
                print(f"⏭️ {platform_name} skipped (disabled)")
        
        print(f"\n{'='*60}")
        print(f"Collection complete for cluster: {cluster.name}")
        print(f"Total posts collected: {results['total_posts_collected']}")
        print(f"Total posts processed: {results['total_posts_processed']}")
        print(f"{'='*60}\n")
        
        return results

    def _determine_label_from_score(self, score: float):
        """Determine sentiment label from score"""
        from app.models.posts_table import SentimentLabel

        if score >= 0.3:
            return SentimentLabel.POSITIVE
        elif score <= -0.3:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel.NEUTRAL

    async def _save_to_social_posts(self, post: PostCreate, cluster):
        """
        Save post to social_posts collection for backward compatibility
        
        Args:
            post: Post data
            cluster: Cluster object
        """
        try:
            from app.models.social_post import SocialPostCreate
            
            # Convert to social_post format
            social_post = SocialPostCreate(
                cluster_id=post.cluster_id,
                platform=post.platform.value,
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
                sentiment=post.sentiment_label.value if post.sentiment_label else "neutral",
                cluster_type=cluster.cluster_type
            )
            
            # Save using social post service
            await self.social_post_service.create_post(social_post)
            
        except Exception as e:
            print(f"Error saving to social_posts: {e}")
    
    async def collect_all_active_clusters(self) -> Dict[str, Any]:
        """
        Collect data for all active clusters

        Returns:
            Summary of all collection results
        """
        logger.info("="*80)
        logger.info("🎯 STARTING COLLECTION FOR ALL ACTIVE CLUSTERS")
        logger.info("="*80)

        # Get all active clusters
        clusters = await self.cluster_service.get_clusters(is_active=True)

        if not clusters:
            logger.warning("❌ No active clusters found")
            return {"message": "No active clusters found"}

        logger.info(f"📋 Found {len(clusters)} active clusters:")
        for i, cluster in enumerate(clusters, 1):
            logger.info(f"   {i}. {cluster.name} (ID: {cluster.id}, Type: {cluster.cluster_type})")
            logger.info(f"      Keywords: {cluster.keywords}")

        all_results = {
            "clusters_processed": 0,
            "total_posts_collected": 0,
            "total_posts_processed": 0,
            "cluster_results": [],
            "errors": []
        }

        # Process each cluster
        for i, cluster in enumerate(clusters, 1):
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"🔄 Processing cluster {i}/{len(clusters)}: {cluster.name} (ID: {cluster.id})")
                logger.info(f"{'='*80}")

                result = await self.collect_and_process_cluster(
                    cluster_id=cluster.id,
                    save_to_social_posts=True,
                    save_to_posts_table=True
                )

                all_results["cluster_results"].append(result)
                all_results["clusters_processed"] += 1

                logger.info(f"✅ Cluster '{cluster.name}' processed successfully")
                logger.info(f"   Posts collected: {result.get('total_posts_collected', 0)}")
                logger.info(f"   Posts processed: {result.get('total_posts_processed', 0)}")
                all_results["total_posts_collected"] += result.get("total_posts_collected", 0)
                all_results["total_posts_processed"] += result.get("total_posts_processed", 0)

            except Exception as e:
                logger.error(f"❌ Error processing cluster {cluster.name}: {e}")
                import traceback
                logger.debug(f"   Traceback: {traceback.format_exc()}")
                all_results["errors"].append(f"{cluster.name}: {str(e)}")

        logger.info("\n" + "="*80)
        logger.info("📊 COLLECTION SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Clusters processed: {all_results['clusters_processed']}")
        logger.info(f"📝 Total posts collected: {all_results['total_posts_collected']}")
        logger.info(f"💾 Total posts processed: {all_results['total_posts_processed']}")
        if all_results["errors"]:
            logger.error(f"❌ Errors: {len(all_results['errors'])}")
            for error in all_results["errors"]:
                logger.error(f"   - {error}")
        logger.info("="*80 + "\n")

        return all_results
    
    async def process_pending_raw_data(self, limit: int = 100) -> Dict[str, Any]:
        """
        Process pending raw data entries
        
        Args:
            limit: Maximum number of entries to process
            
        Returns:
            Processing summary
        """
        print(f"\nProcessing up to {limit} pending raw data entries...")
        
        # Get pending entries
        pending = await self.raw_data_service.get_pending_entries(limit)
        
        if not pending:
            print("No pending entries found")
            return {"message": "No pending entries to process"}
        
        print(f"Found {len(pending)} pending entries")
        
        results = {
            "entries_processed": 0,
            "posts_created": 0,
            "errors": []
        }
        
        # Process in batches for better performance (parallel LLM calls)
        batch_size = 50  # Process 50 entries at once in parallel
        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(pending) + batch_size - 1)//batch_size} ({len(batch)} entries)")

            # Process batch IN PARALLEL for speed
            batch_posts = []
            batch_entries = []

            # Create parallel tasks for all entries in batch
            tasks = [self.llm_service.process_raw_data(entry) for entry in batch]

            # Process all entries in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful results
            for entry, result in zip(batch, batch_results):
                try:
                    if isinstance(result, Exception):
                        # LLM processing failed
                        print(f"Error processing entry {entry.id}: {result}")
                        results["errors"].append(str(result))
                        # Mark as failed
                        await self.raw_data_service.mark_as_processed(
                            entry.id,
                            posts_extracted=0,
                            error=str(result)
                        )
                    elif result:
                        # Success
                        batch_posts.append(result)
                        batch_entries.append(entry)
                    else:
                        # No post extracted
                        await self.raw_data_service.mark_as_processed(
                            entry.id,
                            posts_extracted=0,
                            error="No post extracted"
                        )
                except Exception as e:
                    print(f"Error handling result for entry {entry.id}: {e}")
                    results["errors"].append(str(e))
            
            # Save batch to database
            if batch_posts:
                try:
                    saved_posts = await self.posts_service.bulk_create_posts(batch_posts)
                    results["posts_created"] += len(saved_posts)
                    
                    # Mark corresponding raw entries as processed
                    for entry in batch_entries:
                        await self.raw_data_service.mark_as_processed(
                            entry.id,
                            posts_extracted=1
                        )
                        
                except Exception as e:
                    print(f"Error saving batch: {e}")
                    results["errors"].append(str(e))
            
            results["entries_processed"] += len(batch)
            
            # Add small delay between batches to avoid overwhelming the system
            if i + batch_size < len(pending):
                await asyncio.sleep(0.5)
        
        print(f"Processing complete: {results['posts_created']} posts created")
        
        return results
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """
        Get current status of data collection
        
        Returns:
            Status information
        """
        # Get statistics from services
        raw_stats = await self.raw_data_service.get_statistics()
        posts_stats = await self.posts_service.get_aggregate_stats()
        
        # Get cluster info
        clusters = await self.cluster_service.get_clusters()
        active_clusters = [c for c in clusters if c.is_active]
        
        status = {
            "clusters": {
                "total": len(clusters),
                "active": len(active_clusters)
            },
            "raw_data": {
                "total_records": raw_stats.total_records,
                "by_platform": raw_stats.records_by_platform,
                "by_status": raw_stats.records_by_status,
                "pending_processing": raw_stats.pending_processing_count,
                "failed_processing": raw_stats.failed_processing_count,
                "size_mb": raw_stats.total_size_mb
            },
            "posts": {
                "total": posts_stats.total_posts,
                "by_platform": posts_stats.posts_by_platform,
                "by_sentiment": posts_stats.posts_by_sentiment,
                "threats": posts_stats.threat_posts,
                "engagement": posts_stats.total_engagement
            }
        }
        
        return status