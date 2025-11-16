"""
News Collection Service with Google News RSS Integration
"""
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
import logging
import html
import re
from bson import ObjectId
from bs4 import BeautifulSoup

from app.core.database import get_database
from app.models.news_article import (
    NewsArticleCreate, 
    NewsArticleResponse, 
    NewsArticleIntelligence,
    NewsArticleUpdate
)
from app.services.cluster_service import ClusterService
from app.services.intelligence_service import IntelligenceService

logger = logging.getLogger(__name__)


class NewsService:
    """Service for collecting and managing news articles"""
    
    def __init__(self):
        self._db = None
        self._collection = None
        self.cluster_service = ClusterService()
        self.intelligence_service = IntelligenceService()
        self.google_news_base_url = "https://news.google.com/rss/search"
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            self._collection = self._db.news_articles
        return self._collection
    
    async def collect_news_for_all_clusters(self) -> Dict[str, int]:
        """Collect news for all active clusters"""
        try:
            # Get all active clusters
            clusters = await self.cluster_service.get_clusters()
            results = {"collected": 0, "errors": 0, "clusters_processed": 0}
            
            for cluster in clusters:
                try:
                    cluster_results = await self.collect_news_for_cluster(cluster.id)
                    results["collected"] += cluster_results["collected"]
                    results["clusters_processed"] += 1
                    logger.info(f"Collected {cluster_results['collected']} articles for cluster {cluster.name}")
                except Exception as e:
                    logger.error(f"Error collecting news for cluster {cluster.name}: {str(e)}")
                    results["errors"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error in collect_news_for_all_clusters: {str(e)}")
            raise
    
    async def collect_news_for_cluster(self, cluster_id: str) -> Dict[str, int]:
        """Collect news articles for a specific cluster with multi-perspective analysis"""
        try:
            # Get cluster details
            cluster = await self.cluster_service.get_cluster(cluster_id)
            if not cluster:
                raise ValueError(f"Cluster {cluster_id} not found")
            
            keywords = cluster.keywords
            if not keywords:
                logger.warning(f"No keywords found for cluster {cluster_id}")
                return {"collected": 0}
            
            # Get ALL clusters for multi-perspective analysis
            all_clusters = await self.cluster_service.get_clusters()
            all_clusters_dict = [
                {
                    "id": c.id,
                    "name": c.name,
                    "cluster_type": c.cluster_type,
                    "keywords": c.keywords
                }
                for c in all_clusters
            ]
            
            results = {"collected": 0}
            
            # Convert social media keywords to news-friendly keywords
            news_keywords = self._convert_to_news_keywords(keywords, cluster.name)
            
            # Collect news for each keyword
            for keyword in news_keywords:
                try:
                    articles = await self._fetch_google_news_for_keyword(keyword)
                    for article_data in articles:
                        # Check if article already exists
                        existing = await self.collection.find_one({"url": article_data["url"]})
                        if not existing:
                            # Analyze content against ALL clusters
                            text_for_analysis = f"{article_data['title']}. {article_data.get('summary', '')}"
                            matched_clusters = await self.intelligence_service.detect_matched_clusters(
                                text_for_analysis, 
                                all_clusters_dict
                            )
                            
                            # Determine perspective type
                            own_clusters = [c for c in matched_clusters if c.cluster_type == "own"]
                            competitor_clusters = [c for c in matched_clusters if c.cluster_type == "competitor"]
                            
                            if len(own_clusters) > 0 and len(competitor_clusters) > 0:
                                perspective_type = "multi-perspective"
                            elif len(own_clusters) > 0:
                                perspective_type = "own"
                            elif len(competitor_clusters) > 0:
                                perspective_type = "competitor"
                            else:
                                perspective_type = "single"
                            
                            # Perform appropriate intelligence analysis
                            if len(matched_clusters) > 1:
                                # Multi-perspective analysis
                                intelligence = await self.intelligence_service.analyze_multi_perspective_content(
                                    text_for_analysis,
                                    "news",
                                    matched_clusters
                                )
                            else:
                                # Single perspective analysis (existing logic)
                                intelligence = await self.intelligence_service.analyze_news_content(text_for_analysis)
                            
                            # Set up article data with multi-perspective fields
                            article_data["matched_clusters"] = [
                                {
                                    "cluster_id": mc.cluster_id,
                                    "cluster_name": mc.cluster_name,
                                    "cluster_type": mc.cluster_type,
                                    "keywords_matched": mc.keywords_matched
                                }
                                for mc in matched_clusters
                            ]
                            article_data["perspective_type"] = perspective_type
                            article_data["intelligence"] = intelligence
                            
                            # Legacy fields for backward compatibility
                            article_data["cluster_keywords"] = [keyword]
                            article_data["cluster_id"] = cluster_id
                            article_data["cluster_type"] = cluster.cluster_type
                            
                            # Create article
                            article = NewsArticleCreate(**article_data)
                            await self.create_article(article)
                            results["collected"] += 1
                        
                except Exception as e:
                    logger.error(f"Error collecting news for keyword '{keyword}': {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error collecting news for cluster {cluster_id}: {str(e)}")
            raise
    
    async def _fetch_google_news_for_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Fetch news articles from Google News RSS for a specific keyword"""
        try:
            # Build Google News RSS URL with geographic filtering and 24-hour time constraint
            query = f"({keyword}) AND (Tamil Nadu OR Chennai OR TN) when:1d"  # Geographic filtering added
            encoded_query = quote_plus(query)
            rss_url = f"{self.google_news_base_url}?q={encoded_query}&hl=en&gl=US&ceid=US:en"
            
            print(f"Fetching news from: {rss_url}")
            
            # Fetch RSS feed
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(rss_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        print(f"HTTP Response status: {response.status}")
                        if response.status != 200:
                            print(f"Failed to fetch RSS for keyword '{keyword}': HTTP {response.status}")
                            return []
                        
                        rss_content = await response.text()
                        print(f"RSS content length: {len(rss_content)}")
            except Exception as http_error:
                print(f"HTTP request failed for keyword '{keyword}': {str(http_error)}")
                return []
            
            # Parse RSS feed
            feed = feedparser.parse(rss_content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for keyword '{keyword}': {feed.bozo_exception}")
            
            articles = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'published') and entry.published:
                        try:
                            pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
                        except ValueError:
                            try:
                                pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S GMT")
                            except ValueError:
                                logger.warning(f"Could not parse date: {entry.published}")
                    
                    # Apply 24-hour filter (double-check even though URL has when:1d)
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    # Extract and sanitize article data
                    raw_summary = entry.get("summary", "")
                    clean_summary = self._sanitize_html_summary(raw_summary)
                    title = entry.get("title", "").strip()
                    
                    article_data = {
                        "platform": "web_news",  # Set platform for Google RSS feeds
                        "title": title,
                        "summary": clean_summary,  # Use sanitized summary
                        "url": entry.get("link", "").strip(),
                        "published_at": pub_date or datetime.now(),
                        "source": self._extract_source_from_entry(entry),
                        "author": entry.get("author", None),
                        "tags": self._extract_tags_from_entry(entry),
                        "category": self._categorize_article(title + " " + clean_summary),  # Use clean text for categorization
                        "readers_count": self._estimate_readers_count(entry)
                    }
                    
                    # Validate required fields
                    if article_data["title"] and article_data["url"]:
                        articles.append(article_data)
                
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {str(e)}")
                    continue
            
            print(f"Found {len(articles)} articles for keyword '{keyword}'")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching Google News for keyword '{keyword}': {str(e)}")
            return []
    
    def _sanitize_html_summary(self, html_summary: str) -> str:
        """Strips HTML and cleans the summary from a Google News RSS feed."""
        if not html_summary:
            return ""
        
        try:
            # Use BeautifulSoup to parse the HTML and get only the text
            soup = BeautifulSoup(html_summary, 'html.parser')
            clean_text = soup.get_text(separator=' ', strip=True)
            
            # Decode HTML entities (&amp;, &nbsp;, etc.)
            clean_text = html.unescape(clean_text)
            
            # The text often includes the source name at the end, let's remove it if present.
            # e.g., "Article Title... - TheCommuneMag"
            # This part can be made more robust, but it's a good start.
            parts = clean_text.rsplit('-', 1)
            if len(parts) > 1:
                # Heuristically assume the last part is the source name
                clean_text = parts[0].strip()
            
            # Clean up extra whitespace and normalize
            clean_text = ' '.join(clean_text.split())
            
            return clean_text
            
        except Exception as e:
            logger.error(f"Error sanitizing HTML summary: {str(e)}")
            # Fallback: return the original text without HTML tags using simple regex
            text = re.sub('<[^<]+?>', '', html_summary)
            return html.unescape(text).strip()
    
    def _convert_to_news_keywords(self, keywords: List[str], cluster_name: str) -> List[str]:
        """Convert social media hashtag keywords to news-friendly search terms"""
        news_keywords = []
        
        # Add the cluster name itself as a keyword
        news_keywords.append(cluster_name)
        
        # Define mapping of hashtags/Tamil text to news keywords
        keyword_mapping = {
            # DMK related
            "#DMK": "DMK Tamil Nadu",
            "#திமுக": "DMK Tamil Nadu",
            "#DravidianModel": "DMK Dravidian Model",
            "#திராவிடமாடல்": "DMK Dravidian Model",
            
            # TVK related  
            "#TVK": "TVK Tamil Nadu",
            "#தமிழகவெற்றிக்கழகம்": "TVK Tamil Nadu",
            "#TVK4TN": "TVK Tamil Nadu",
            "#தமிழகவெற்றிக்கழகம்4தமிழ்நாடு": "TVK Tamil Nadu"
        }
        
        for keyword in keywords:
            # Remove spaces and process each hashtag separately
            hashtags = keyword.split()
            for hashtag in hashtags:
                if hashtag in keyword_mapping:
                    mapped_keyword = keyword_mapping[hashtag]
                    if mapped_keyword not in news_keywords:
                        news_keywords.append(mapped_keyword)
                else:
                    # Clean hashtag symbol and use as is (for unknown hashtags)
                    clean_keyword = hashtag.replace("#", "").strip()
                    if clean_keyword and len(clean_keyword) > 2:
                        news_keywords.append(clean_keyword)
        
        # Add some general Tamil Nadu political keywords
        general_keywords = [
            f"{cluster_name} Tamil Nadu politics",
            f"{cluster_name} Tamil Nadu news"
        ]
        news_keywords.extend(general_keywords)
        
        # Remove duplicates and return
        return list(set(news_keywords))
    
    def _extract_source_from_entry(self, entry) -> str:
        """Extract news source from RSS entry"""
        # Try different methods to get source
        if hasattr(entry, 'source') and entry.source:
            return entry.source.get('title', 'Unknown Source')
        
        # Extract from link domain
        url = entry.get('link', '')
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                # Remove www. prefix
                if domain.startswith('www.'):
                    domain = domain[4:]
                return domain.title()
            except:
                pass
        
        return "Unknown Source"
    
    def _extract_tags_from_entry(self, entry) -> List[str]:
        """Extract tags/categories from RSS entry"""
        tags = []
        
        # Extract from tags if available
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term') and tag.term:
                    tags.append(tag.term)
        
        # Extract from categories
        if hasattr(entry, 'category') and entry.category:
            tags.append(entry.category)
        
        return tags[:5]  # Limit to 5 tags
    
    def _categorize_article(self, content: str) -> str:
        """Categorize article based on content"""
        content_lower = content.lower()
        
        # Define category keywords
        categories = {
            "Politics": ["election", "government", "policy", "minister", "parliament", "political"],
            "Economy": ["economic", "business", "financial", "market", "trade", "industry"],
            "Environment": ["environment", "climate", "pollution", "green", "sustainable"],
            "Social": ["social", "community", "education", "health", "welfare"],
            "Technology": ["technology", "digital", "tech", "innovation", "startup"],
            "Infrastructure": ["infrastructure", "development", "construction", "transport"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category
        
        return "General"
    
    def _estimate_readers_count(self, entry) -> Optional[int]:
        """Estimate readers count based on source popularity"""
        source = self._extract_source_from_entry(entry).lower()
        
        # Rough estimates based on typical news source reach
        popular_sources = {
            "bbc": 50000,
            "cnn": 45000,
            "reuters": 40000,
            "times": 35000,
            "guardian": 30000,
            "post": 25000,
            "news": 20000
        }
        
        for source_key, count in popular_sources.items():
            if source_key in source:
                return count
        
        return 15000  # Default estimate
    
    async def create_article(self, article: NewsArticleCreate) -> NewsArticleResponse:
        """Create a new news article"""
        article_dict = article.dict()
        article_dict["collected_at"] = datetime.now()
        article_dict["_id"] = ObjectId()
        
        result = await self.collection.insert_one(article_dict)
        
        # Return the created article
        created_article = await self.collection.find_one({"_id": result.inserted_id})
        created_article["id"] = str(created_article["_id"])
        return NewsArticleResponse(**created_article)
    
    async def get_articles(
        self,
        cluster_type: Optional[str] = None,
        cluster_id: Optional[str] = None,
        category: Optional[str] = None,
        impact_level: Optional[str] = None,
        hours_back: int = 24,
        skip: int = 0,
        limit: int = 100
    ) -> List[NewsArticleResponse]:
        """Get news articles with filters"""
        try:
            # Build filter query
            filter_query = {}
            
            # Time filter - only show articles from last X hours
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            filter_query["published_at"] = {"$gte": cutoff_time}
            
            if cluster_type:
                filter_query["cluster_type"] = cluster_type
            
            if cluster_id:
                filter_query["cluster_id"] = cluster_id
            
            if category:
                filter_query["category"] = category
            
            if impact_level:
                filter_query["intelligence.impact_level"] = impact_level
            
            # Execute query
            cursor = self.collection.find(filter_query).sort("published_at", -1).skip(skip).limit(limit)
            articles = await cursor.to_list(length=limit)
            
            # Convert to response format
            response_articles = []
            for article in articles:
                article["id"] = str(article["_id"])
                
                # Provide defaults for missing fields
                article.setdefault("platform", "web_news")
                article.setdefault("cluster_keywords", [])
                article.setdefault("tags", [])
                article.setdefault("collected_at", article.get("published_at", datetime.now()))
                
                response_articles.append(NewsArticleResponse(**article))
            
            return response_articles
            
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            raise
    
    async def get_article(self, article_id: str) -> Optional[NewsArticleResponse]:
        """Get a single article by ID"""
        try:
            article = await self.collection.find_one({"_id": ObjectId(article_id)})
            if article:
                article["id"] = str(article["_id"])
                
                # Provide defaults for missing fields
                article.setdefault("platform", "web_news")
                article.setdefault("cluster_keywords", [])
                article.setdefault("tags", [])
                article.setdefault("collected_at", article.get("published_at", datetime.now()))
                
                return NewsArticleResponse(**article)
            return None
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {str(e)}")
            return None
    
    async def update_article(self, article_id: str, update_data: NewsArticleUpdate) -> Optional[NewsArticleResponse]:
        """Update an article"""
        try:
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            if not update_dict:
                return await self.get_article(article_id)
            
            result = await self.collection.update_one(
                {"_id": ObjectId(article_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count > 0:
                return await self.get_article(article_id)
            
            return None
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {str(e)}")
            return None
    
    async def delete_article(self, article_id: str) -> bool:
        """Delete an article"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(article_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting article {article_id}: {str(e)}")
            return False
    
    async def get_threat_articles(self, hours_back: int = 24) -> List[NewsArticleResponse]:
        """Get articles that are marked as threats"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            filter_query = {
                "published_at": {"$gte": cutoff_time},
                "intelligence.is_threat": True
            }
            
            cursor = self.collection.find(filter_query).sort("published_at", -1)
            articles = await cursor.to_list(length=None)
            
            response_articles = []
            for article in articles:
                article["id"] = str(article["_id"])
                
                # Provide defaults for missing fields
                article.setdefault("platform", "web_news")
                article.setdefault("cluster_keywords", [])
                article.setdefault("tags", [])
                article.setdefault("collected_at", article.get("published_at", datetime.now()))
                
                response_articles.append(NewsArticleResponse(**article))
            
            return response_articles
            
        except Exception as e:
            logger.error(f"Error fetching threat articles: {str(e)}")
            raise