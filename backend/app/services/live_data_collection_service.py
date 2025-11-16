"""
Live Data Collection Service for SMART RADAR v25.0
Collects real-time data from all platforms and populates unified monitored_content collection
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from bson import ObjectId

from app.core.database import get_database
from app.models.monitored_content import (
    MonitoredContent,
    ContentType,
    Platform,
    SocialMetrics,
    NewsMetrics,
    IntelligenceV24,
    EntitySentiment
)
from app.services.unified_intelligence_service import UnifiedIntelligenceService
from app.services.unified_content_service import UnifiedContentService

class LiveDataCollectionService:
    """
    Live data collection service for all platforms
    Simulates real-time social media and news collection with v24.0 intelligence
    """
    
    def __init__(self):
        self._db = None
        self._clusters = []
        self._intelligence_service = UnifiedIntelligenceService()
        self._content_service = UnifiedContentService()
        self._is_collecting = False
    
    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db
    
    async def start_live_collection(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Start live data collection from all platforms"""
        if self._is_collecting:
            return {"status": "already_running", "message": "Live collection is already active"}
        
        print("🚀 Starting SMART RADAR v25.0 Live Data Collection...")
        
        # Load clusters
        await self._load_clusters()
        
        if not self._clusters:
            return {"status": "error", "message": "No active clusters found"}
        
        self._is_collecting = True
        
        # Start collection tasks
        collection_stats = {
            "start_time": datetime.utcnow(),
            "duration_minutes": duration_minutes,
            "platforms": ["X", "Facebook", "YouTube", "news_site"],
            "clusters": len(self._clusters),
            "collected_content": 0,
            "processed_intelligence": 0
        }
        
        try:
            # Run collection for specified duration
            end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
            
            while datetime.utcnow() < end_time and self._is_collecting:
                # Collect from all platforms
                batch_stats = await self._collect_batch()
                collection_stats["collected_content"] += batch_stats["collected"]
                collection_stats["processed_intelligence"] += batch_stats["processed"]
                
                print(f"📊 Batch collected: {batch_stats['collected']} items, processed: {batch_stats['processed']} intelligence")
                
                # Wait before next batch (simulate real-time collection)
                await asyncio.sleep(30)  # Collect every 30 seconds
            
            collection_stats["end_time"] = datetime.utcnow()
            collection_stats["status"] = "completed"
            
        except Exception as e:
            collection_stats["status"] = "error"
            collection_stats["error"] = str(e)
            print(f"❌ Collection error: {e}")
        finally:
            self._is_collecting = False
        
        return collection_stats
    
    async def stop_collection(self) -> Dict[str, str]:
        """Stop ongoing live collection"""
        if not self._is_collecting:
            return {"status": "not_running", "message": "No active collection to stop"}
        
        self._is_collecting = False
        print("⏹️ Live data collection stopped")
        return {"status": "stopped", "message": "Live collection stopped successfully"}
    
    async def collect_single_batch(self) -> Dict[str, Any]:
        """Collect a single batch of data immediately"""
        await self._load_clusters()
        return await self._collect_batch()
    
    async def _load_clusters(self):
        """Load active clusters from database"""
        clusters_collection = self.db.clusters
        self._clusters = []
        
        async for cluster_doc in clusters_collection.find({"is_active": True}):
            self._clusters.append(cluster_doc)
        
        print(f"📋 Loaded {len(self._clusters)} active clusters")
    
    async def _collect_batch(self) -> Dict[str, int]:
        """Collect a batch of content from all platforms"""
        batch_stats = {"collected": 0, "processed": 0}
        
        platforms = [Platform.X, Platform.FACEBOOK, Platform.YOUTUBE, Platform.NEWS_SITE]
        
        for platform in platforms:
            for cluster in self._clusters:
                try:
                    # Simulate content collection based on platform
                    content_items = await self._simulate_platform_content(platform, cluster)
                    
                    for content_item in content_items:
                        # Create content in unified collection
                        content_id = await self._content_service.create_content(content_item, auto_analyze=True)
                        
                        batch_stats["collected"] += 1
                        batch_stats["processed"] += 1
                        
                        print(f"✅ Collected from {platform.value}: {content_item.title[:50]}...")
                
                except Exception as e:
                    print(f"⚠️ Error collecting from {platform.value} for cluster {cluster.get('name')}: {e}")
                    continue
        
        return batch_stats
    
    async def _simulate_platform_content(self, platform: Platform, cluster: Dict[str, Any]) -> List:
        """Simulate realistic content from different platforms"""
        content_items = []
        
        # Random chance of finding content (simulate real social media activity)
        if random.random() > 0.7:  # 30% chance of finding content
            return content_items
        
        cluster_name = cluster.get("name", "")
        cluster_type = cluster.get("cluster_type", "")
        keywords = cluster.get("keywords", [])
        
        if platform == Platform.X:
            content_items.extend(await self._simulate_x_content(cluster_name, cluster_type, keywords))
        elif platform == Platform.FACEBOOK:
            content_items.extend(await self._simulate_facebook_content(cluster_name, cluster_type, keywords))
        elif platform == Platform.YOUTUBE:
            content_items.extend(await self._simulate_youtube_content(cluster_name, cluster_type, keywords))
        elif platform == Platform.NEWS_SITE:
            content_items.extend(await self._simulate_news_content(cluster_name, cluster_type, keywords))
        
        return content_items
    
    async def _simulate_x_content(self, cluster_name: str, cluster_type: str, keywords: List[str]):
        """Simulate X (Twitter) content"""
        from app.models.monitored_content import MonitoredContentCreate
        
        # Sample X content templates
        templates = [
            f"Latest update from {cluster_name}: New policy announcement regarding Tamil Nadu development",
            f"{cluster_name} addresses concerns about infrastructure improvements in the state",
            f"Breaking: {cluster_name} responds to opposition criticism with strong statement",
            f"Public rally by {cluster_name} draws massive crowds in Chennai",
            f"{cluster_name} launches new initiative for youth empowerment in Tamil Nadu"
        ]
        
        content_text = random.choice(templates)
        
        # Add relevant keywords
        if keywords:
            selected_keyword = random.choice(keywords)
            content_text += f" #{selected_keyword.replace(' ', '')}"
        
        return [MonitoredContentCreate(
            content_type=ContentType.SOCIAL_POST,
            platform=Platform.X,
            platform_content_id=f"x_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}",
            title=content_text[:100] + "..." if len(content_text) > 100 else content_text,
            content=content_text,
            author=f"@{cluster_name}Official",
            url=f"https://x.com/{cluster_name}Official/status/{random.randint(1000000, 9999999)}",
            published_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
            social_metrics=SocialMetrics(
                likes=random.randint(50, 500),
                shares=random.randint(10, 100),
                comments=random.randint(5, 50),
                views=random.randint(500, 5000),
                engagement_rate=random.uniform(0.01, 0.1),
                follower_count=random.randint(10000, 100000)
            )
        )]
    
    async def _simulate_facebook_content(self, cluster_name: str, cluster_type: str, keywords: List[str]):
        """Simulate Facebook content"""
        from app.models.monitored_content import MonitoredContentCreate
        
        templates = [
            f"{cluster_name} page update: Community outreach program launched in rural areas",
            f"Photo album: {cluster_name} visits local communities to discuss development projects",
            f"{cluster_name} shares vision for Tamil Nadu's future growth and prosperity",
            f"Live session: {cluster_name} answers public questions about government policies",
            f"Event announcement: {cluster_name} to address supporters at public meeting"
        ]
        
        content_text = random.choice(templates)
        
        return [MonitoredContentCreate(
            content_type=ContentType.SOCIAL_POST,
            platform=Platform.FACEBOOK,
            platform_content_id=f"fb_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}",
            title=content_text[:100] + "..." if len(content_text) > 100 else content_text,
            content=content_text,
            author=f"{cluster_name} Official Page",
            url=f"https://facebook.com/{cluster_name}/posts/{random.randint(1000000, 9999999)}",
            published_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 120)),
            social_metrics=SocialMetrics(
                likes=random.randint(100, 1000),
                shares=random.randint(20, 200),
                comments=random.randint(10, 100),
                views=random.randint(1000, 10000),
                engagement_rate=random.uniform(0.02, 0.15),
                follower_count=random.randint(50000, 500000)
            )
        )]
    
    async def _simulate_youtube_content(self, cluster_name: str, cluster_type: str, keywords: List[str]):
        """Simulate YouTube content"""
        from app.models.monitored_content import MonitoredContentCreate
        
        templates = [
            f"{cluster_name} Official Speech: Vision for Tamil Nadu Development",
            f"Exclusive Interview: {cluster_name} discusses key policy initiatives",
            f"Press Conference: {cluster_name} addresses media on recent developments",
            f"Rally Highlights: {cluster_name} connects with supporters across the state",
            f"Documentary: {cluster_name}'s journey in Tamil Nadu politics"
        ]
        
        content_text = random.choice(templates)
        description = f"Official video from {cluster_name}. {content_text} - Full coverage of important political developments in Tamil Nadu."
        
        return [MonitoredContentCreate(
            content_type=ContentType.SOCIAL_POST,
            platform=Platform.YOUTUBE,
            platform_content_id=f"yt_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}",
            title=content_text,
            content=description,
            author=f"{cluster_name} Official Channel",
            url=f"https://youtube.com/watch?v={random.choice('abcdefghijklmnopqrstuvwxyz')}{random.randint(100000, 999999)}",
            published_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
            social_metrics=SocialMetrics(
                likes=random.randint(200, 2000),
                shares=random.randint(50, 500),
                comments=random.randint(20, 200),
                views=random.randint(5000, 50000),
                engagement_rate=random.uniform(0.03, 0.2),
                follower_count=random.randint(100000, 1000000)
            )
        )]
    
    async def _simulate_news_content(self, cluster_name: str, cluster_type: str, keywords: List[str]):
        """Simulate news article content"""
        from app.models.monitored_content import MonitoredContentCreate
        
        templates = [
            f"{cluster_name} Announces Major Infrastructure Development Plan for Tamil Nadu",
            f"Political Analysis: {cluster_name}'s Impact on State Governance",
            f"Breaking News: {cluster_name} Responds to Opposition Allegations",
            f"Tamil Nadu Politics: {cluster_name} Gains Support from Rural Communities",
            f"Policy Update: {cluster_name} Introduces New Reforms for Economic Growth"
        ]
        
        title = random.choice(templates)
        content = f"""
        {title}
        
        In a significant development in Tamil Nadu politics, {cluster_name} has made important announcements regarding the state's future direction. 
        
        The recent statements from {cluster_name} indicate a clear strategy for addressing key challenges facing the state, including economic development, infrastructure improvements, and social welfare initiatives.
        
        Political analysts suggest that these developments could have far-reaching implications for the upcoming political landscape in Tamil Nadu. The response from various stakeholders has been mixed, with supporters praising the initiatives while critics raise questions about implementation.
        
        This development comes at a crucial time when Tamil Nadu is facing multiple challenges and opportunities. The role of {cluster_name} in shaping the state's future continues to be a subject of intense public interest and political debate.
        
        Further updates are expected as the situation develops.
        """
        
        return [MonitoredContentCreate(
            content_type=ContentType.NEWS_ARTICLE,
            platform=Platform.NEWS_SITE,
            platform_content_id=f"news_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}",
            title=title,
            content=content.strip(),
            author="Political Correspondent",
            url=f"https://tamilnadunews.com/politics/{cluster_name.lower()}-{random.randint(100000, 999999)}",
            published_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)),
            news_metrics=NewsMetrics(
                word_count=len(content.split()),
                reading_time_minutes=max(1, len(content.split()) // 200),
                source_credibility=random.uniform(0.6, 0.9),
                article_category="Politics",
                journalist_name="Political Correspondent"
            )
        )]
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status"""
        return {
            "is_collecting": self._is_collecting,
            "clusters_loaded": len(self._clusters),
            "timestamp": datetime.utcnow().isoformat()
        }