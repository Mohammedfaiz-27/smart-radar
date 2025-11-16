#!/usr/bin/env python3
"""
Standalone RSS News Collector for DMK and ADMK Clusters
Safely collects news from Google News RSS feeds without disturbing existing services
Stores in news_articles collection using existing schema
"""
import asyncio
import feedparser
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import quote_plus
import hashlib
from bs4 import BeautifulSoup
import aiohttp
import json

# Set environment variables
os.environ["MONGODB_URL"] = "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Add backend to path
sys.path.append('/Users/Samrt radar Final /backend')

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


class StandaloneNewsCollector:
    """Standalone news collector that preserves all existing data and services"""
    
    def __init__(self):
        self.mongodb_url = os.getenv('MONGODB_URL', 'mongodb://admin:password@localhost:27017/smart_radar?authSource=admin')
        self.client = None
        self.db = None
        self.google_news_base_url = "https://news.google.com/rss/search"
        
        # Headers to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    async def initialize(self):
        """Initialize database connection"""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client['smart_radar']
        print("✅ Connected to MongoDB")
        
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✅ Database connection closed")
    
    async def get_cluster_info(self, cluster_id: ObjectId) -> Dict[str, Any]:
        """Get cluster information from database"""
        cluster = await self.db.clusters.find_one({"_id": cluster_id})
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        return cluster
    
    def create_basic_intelligence(self):
        """Create basic intelligence structure for news articles"""
        return {
            "relational_summary": "Pending analysis",
            "entity_sentiments": {},
            "threat_level": "low",
            "impact_level": "medium",
            "confidence_score": 0.8
        }
    
    def create_cluster_match(self, cluster: Dict[str, Any], matched_keywords: List[str]):
        """Create cluster match information"""
        return {
            "cluster_id": str(cluster["_id"]),
            "cluster_name": cluster.get("name", "Unknown"),
            "cluster_type": cluster.get("cluster_type", "unknown"),
            "keywords_matched": matched_keywords
        }
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract text"""
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            return html_content
    
    def generate_unique_id(self, url: str) -> str:
        """Generate unique ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    async def fetch_rss_for_keywords(self, keywords: List[str], cluster_name: str) -> List[Dict[str, Any]]:
        """Fetch RSS feed for given keywords"""
        articles = []
        
        # Create query from keywords with geographic and time constraints
        keyword_query = " OR ".join([f'"{keyword}"' for keyword in keywords[:5]])  # Limit to 5 keywords
        query = f"({keyword_query}) AND (Tamil Nadu OR Chennai OR TN) when:1d"
        
        encoded_query = quote_plus(query)
        rss_url = f"{self.google_news_base_url}?q={encoded_query}&hl=en&gl=IN&ceid=IN:en"
        
        print(f"🔍 Fetching news for {cluster_name} from: {rss_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        print(f"❌ HTTP {response.status} for {cluster_name}")
                        return articles
                    
                    rss_content = await response.text()
                    print(f"📄 RSS content length: {len(rss_content)} for {cluster_name}")
            
            # Parse RSS feed
            feed = feedparser.parse(rss_content)
            
            if feed.bozo:
                print(f"⚠️  RSS parsing warning for {cluster_name}: {feed.bozo_exception}")
            
            print(f"📰 Found {len(feed.entries)} articles for {cluster_name}")
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    published_at = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            import time
                            published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        except Exception:
                            pass
                    
                    # Clean summary
                    summary = ""
                    if hasattr(entry, 'summary'):
                        summary = self.clean_html_content(entry.summary)
                    
                    # Extract source
                    source = "Unknown Source"
                    if hasattr(entry, 'source') and entry.source:
                        source = entry.source.get('title', 'Unknown Source')
                    elif hasattr(entry, 'tags') and entry.tags:
                        source = entry.tags[0].get('term', 'Unknown Source')
                    
                    article_data = {
                        "title": entry.title,
                        "summary": summary,
                        "content": summary,  # Use summary as content for RSS feeds
                        "source": source,
                        "author": getattr(entry, 'author', None),
                        "url": entry.link,
                        "published_at": published_at,
                        "unique_id": self.generate_unique_id(entry.link)
                    }
                    
                    articles.append(article_data)
                    
                except Exception as e:
                    print(f"❌ Error parsing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error fetching RSS for {cluster_name}: {e}")
        
        return articles
    
    async def save_news_article(self, article_data: Dict[str, Any], cluster: Dict[str, Any]) -> str:
        """Save news article to news_articles collection using existing schema"""
        
        # Check if article already exists
        existing = await self.db.news_articles.find_one({"url": article_data["url"]})
        if existing:
            print(f"⏭️  Article already exists: {article_data['title'][:50]}...")
            return None
        
        # Create matched clusters information
        matched_clusters = [self.create_cluster_match(cluster, cluster.get("keywords", []))]
        
        # Create news article document using existing schema
        news_article = {
            "platform": "web_news",
            "title": article_data["title"],
            "summary": article_data["summary"],
            "content": article_data["content"],
            "source": article_data["source"],
            "author": article_data.get("author"),
            "url": article_data["url"],
            "published_at": article_data["published_at"],
            "collected_at": datetime.utcnow(),
            "matched_clusters": matched_clusters,
            "intelligence": self.create_basic_intelligence(),
            "category": "politics",
            "language": "English",
            "perspective_type": "single",
            "tags": [],
            "readers_count": None
        }
        
        result = await self.db.news_articles.insert_one(news_article)
        print(f"💾 Saved: {article_data['title'][:60]}...")
        return str(result.inserted_id)
    
    async def collect_for_cluster(self, cluster_id: ObjectId):
        """Collect news for a specific cluster"""
        try:
            # Get cluster information
            cluster = await self.get_cluster_info(cluster_id)
            cluster_name = cluster.get('name', 'Unknown')
            keywords = cluster.get('keywords', [])
            
            print(f"\n🎯 Collecting news for {cluster_name} cluster")
            print(f"📋 Keywords: {keywords}")
            
            if not keywords:
                print(f"⚠️  No keywords found for {cluster_name}")
                return 0
            
            # Fetch articles from RSS
            articles = await self.fetch_rss_for_keywords(keywords, cluster_name)
            
            collected_count = 0
            for article_data in articles:
                try:
                    article_id = await self.save_news_article(article_data, cluster)
                    if article_id:
                        collected_count += 1
                except Exception as e:
                    print(f"❌ Error saving article: {e}")
                    continue
            
            print(f"🎉 Collected {collected_count} new articles for {cluster_name}")
            return collected_count
            
        except Exception as e:
            print(f"❌ Error collecting for cluster {cluster_id}: {e}")
            return 0


async def main():
    """Main function to collect news for DMK and ADMK clusters"""
    print("🚀 Starting Standalone RSS News Collection")
    print("⚠️  SAFE MODE: Only ADDS new news, preserves all existing data")
    print(f"⏰ Start time: {datetime.now()}")
    
    collector = StandaloneNewsCollector()
    
    try:
        await collector.initialize()
        
        # Show existing data count before collection
        existing_articles = await collector.db.news_articles.count_documents({})
        existing_web_news = await collector.db.news_articles.count_documents({"platform": "web_news"})
        
        print(f"\n📊 BEFORE COLLECTION:")
        print(f"   📰 Total news articles: {existing_articles}")
        print(f"   🌐 Web news articles: {existing_web_news}")
        
        # Define target clusters using actual ObjectIds
        clusters = [
            {"id": ObjectId("68d102c95b3f32b5abd27a86"), "name": "DMK"},
            {"id": ObjectId("68d102c95b3f32b5abd27a87"), "name": "ADMK"}
        ]
        
        total_collected = 0
        
        # Collect for each cluster
        for cluster in clusters:
            cluster_collected = await collector.collect_for_cluster(cluster["id"])
            total_collected += cluster_collected
            
            # Delay between clusters
            await asyncio.sleep(3)
        
        # Show final statistics
        final_articles = await collector.db.news_articles.count_documents({})
        final_web_news = await collector.db.news_articles.count_documents({"platform": "web_news"})
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   📰 Total articles collected: {total_collected}")
        print(f"   🏁 End time: {datetime.now()}")
        
        print(f"\n📊 AFTER COLLECTION:")
        print(f"   📰 Total news articles: {final_articles}")
        print(f"   🌐 Web news articles: {final_web_news}")
        
        print(f"\n🔢 NEW DATA ADDED:")
        print(f"   📰 New articles: {final_articles - existing_articles}")
        print(f"   🌐 New web news: {final_web_news - existing_web_news}")
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await collector.close()


if __name__ == "__main__":
    # Run the collection
    asyncio.run(main())