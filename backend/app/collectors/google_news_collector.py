"""
Google News RSS feed collector for keyword-based news collection
Fetches news articles from Google News RSS feeds based on cluster keywords
"""
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator
from urllib.parse import quote_plus, urlencode
import hashlib
import re

from .base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform, SentimentLabel
from app.models.cluster import PlatformConfig


class GoogleNewsCollector(BaseCollector):
    """Collector for Google News RSS feeds"""
    
    def __init__(self, api_key: str = None, api_host: str = None):
        """Initialize Google News collector (no API key required for RSS)"""
        super().__init__(api_key, api_host)
        self.base_url = "https://news.google.com/rss"
        self.rate_limit_delay = 2.0  # Be respectful to Google's servers
        
    def get_platform(self) -> Platform:
        """Return the platform this collector handles"""
        return Platform.GOOGLE_NEWS
    
    def get_api_endpoint(self) -> str:
        """Return the API endpoint being used"""
        return self.base_url
    
    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search Google News RSS for articles matching the keyword
        
        Args:
            keyword: Search term
            config: Platform configuration
            max_results: Maximum number of results to fetch
            
        Yields:
            Parsed news articles from RSS feed
        """
        try:
            # Check if keyword contains Tamil characters
            has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in keyword)
            self.logger.debug(f"🔍 Google News search for keyword: '{keyword}' (Tamil: {has_tamil})")
            
            # Build RSS search URL
            search_params = {
                'q': keyword,
                'hl': config.language or 'en',  # Language
                'gl': config.location or 'IN',   # Location (India for Tamil news)
                'ceid': f"{config.location or 'IN'}:{config.language or 'en'}"
            }
            
            # Construct full URL
            search_url = f"{self.base_url}/search?{urlencode(search_params)}"
            
            self.logger.info(f"🔍 Fetching Google News RSS: {search_url}")
            self.logger.debug(f"   Search params: {search_params}")
            
            # Make request to RSS feed
            response_text = await self._fetch_rss(search_url)
            if not response_text:
                self.logger.warning(f"🚫 No RSS content received for '{keyword}'")
                return
            
            # Parse RSS XML
            articles = self._parse_rss_feed(response_text, keyword, max_results)
            
            self.logger.info(f"📰 Yielding {len(articles)} articles for '{keyword}'")
            
            # Yield each article
            for i, article in enumerate(articles):
                self.logger.debug(f"📄 Yielding article {i+1}/{len(articles)}: {article.get('title', 'No title')[:50]}...")
                yield article
                
        except Exception as e:
            self.logger.error(f"❌ Error searching Google News for '{keyword}': {e}")
            import traceback
            self.logger.debug(f"   Traceback: {traceback.format_exc()}")
    
    async def _fetch_rss(self, url: str) -> Optional[str]:
        """Fetch RSS feed content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    self.logger.debug(f"✅ RSS fetch successful: {len(content)} bytes")
                    return content
                else:
                    self.logger.error(f"❌ RSS fetch failed with status {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Error fetching RSS: {e}")
            return None
    
    def _parse_rss_feed(self, rss_content: str, keyword: str, max_results: int) -> List[Dict[str, Any]]:
        """Parse RSS XML content into structured data"""
        articles = []
        
        try:
            # Parse XML
            root = ET.fromstring(rss_content)
            
            # Find all items (articles)
            items = root.findall('.//item')
            
            self.logger.debug(f"📰 Found {len(items)} articles in RSS feed")
            
            for i, item in enumerate(items[:max_results]):
                try:
                    # Extract article data
                    article = self._extract_article_data(item, keyword)
                    if article:
                        articles.append(article)
                        
                except Exception as e:
                    self.logger.error(f"❌ Error parsing article {i+1}: {e}")
                    continue
            
            self.logger.info(f"✅ Successfully parsed {len(articles)} articles")
            
        except ET.ParseError as e:
            self.logger.error(f"❌ XML parsing error: {e}")
        except Exception as e:
            self.logger.error(f"❌ RSS parsing error: {e}")
            
        return articles
    
    def _extract_article_data(self, item: ET.Element, keyword: str) -> Optional[Dict[str, Any]]:
        """Extract article data from RSS item"""
        try:
            # Basic article information
            title = self._get_element_text(item, 'title')
            description = self._get_element_text(item, 'description')
            link = self._get_element_text(item, 'link')
            pub_date = self._get_element_text(item, 'pubDate')
            
            # Clean description (remove HTML tags)
            if description:
                description = re.sub(r'<[^>]+>', '', description)
                description = description.strip()
            
            # Parse publication date
            published_at = self._parse_pub_date(pub_date)
            
            # Extract source from description or title
            source = self._extract_source(item)
            
            # Generate unique ID
            article_id = self._generate_article_id(title, link, published_at)
            
            # Build article object
            article = {
                'id': article_id,
                'title': title,
                'description': description,
                'content': description,  # Use description as content for RSS
                'url': link,
                'published_at': published_at.isoformat(),
                'source': source,
                'keyword': keyword,
                'language': 'ta' if self._contains_tamil(title + ' ' + (description or '')) else 'en',
                'engagement_metrics': {
                    'views': 0,
                    'likes': 0,
                    'comments': 0,
                    'shares': 0
                }
            }
            
            return article
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting article data: {e}")
            return None
    
    def _get_element_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Safely get text content from XML element"""
        element = parent.find(tag)
        return element.text if element is not None else None
    
    def _parse_pub_date(self, pub_date_str: str) -> datetime:
        """Parse RSS publication date"""
        if not pub_date_str:
            return datetime.utcnow()
        
        try:
            # Try to parse RFC 2822 format (common in RSS)
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(pub_date_str)
        except:
            # Fallback to current time
            return datetime.utcnow()
    
    def _extract_source(self, item: ET.Element) -> str:
        """Extract news source from RSS item"""
        # Try to get source from various possible fields
        source = (
            self._get_element_text(item, 'source') or
            self._get_element_text(item, 'author') or
            self._get_element_text(item, 'dc:creator') or
            'Google News'
        )
        
        # Clean source name
        if source:
            source = re.sub(r'\s*-.*$', '', source)  # Remove " - Additional text"
            source = source.strip()
        
        return source or 'Google News'
    
    def _generate_article_id(self, title: str, url: str, published_at: datetime) -> str:
        """Generate unique ID for article"""
        content = f"{title}_{url}_{published_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _contains_tamil(self, text: str) -> bool:
        """Check if text contains Tamil characters"""
        if not text:
            return False
        return any('\u0B80' <= char <= '\u0BFF' for char in text)
    
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """
        Parse raw Google News article into PostCreate model
        
        Args:
            raw_post: Raw article data from RSS
            cluster_id: Associated cluster ID
            
        Returns:
            PostCreate model ready for database insertion
        """
        try:
            # Extract engagement metrics
            engagement = raw_post.get('engagement_metrics', {})
            
            # Determine content for post
            content = raw_post.get('content') or raw_post.get('description') or ''
            
            # Parse posted_at
            posted_at = datetime.fromisoformat(raw_post['published_at'].replace('Z', '+00:00'))
            
            post = PostCreate(
                platform_post_id=raw_post['id'],
                platform=self.get_platform(),
                cluster_id=cluster_id,
                
                # Author information (use source as author for news)
                author_username=raw_post.get('source', 'google_news'),
                author_followers=0,
                
                # Post content
                post_text=self.clean_text(content),
                post_url=raw_post.get('url', ''),
                posted_at=posted_at,
                
                # Engagement metrics
                likes=engagement.get('likes', 0),
                comments=engagement.get('comments', 0),
                shares=engagement.get('shares', 0),
                views=engagement.get('views', 0),
                
                # LLM fields (default values)
                sentiment_score=0.0,
                sentiment_label=SentimentLabel.NEUTRAL,
                is_threat=False,
                key_narratives=[],
                language=raw_post.get('language', 'en'),
                has_been_responded_to=False,
                
                # System metadata
                fetched_at=datetime.utcnow()
            )
            
            return post
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing Google News article: {e}")
            self.logger.debug(f"Raw post data: {raw_post}")
            raise


# Add Google News to Platform enum if not already present
try:
    from app.models.posts_table import Platform
    if not hasattr(Platform, 'GOOGLE_NEWS'):
        # We need to add this to the Platform enum in posts_table.py
        import logging
        logger = logging.getLogger("collector.googlenewscollector")
        logger.warning("⚠️  Need to add GOOGLE_NEWS to Platform enum")
except ImportError:
    pass