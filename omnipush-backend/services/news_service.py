"""
News fetching and processing service for automated content generation.
Handles fetching live news, OpenAI moderation, and post creation.
"""

import logging
import asyncio
from openai import AsyncOpenAI
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import aiohttp
from dataclasses import dataclass
import uuid

from core.config import settings
from core.database import get_database
from config.prompts import Prompts
from services.content_service import ContentService
from services.moderation_service import ModerationService, ModerationResult

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class ProcessedNews:
    article: NewsArticle
    moderated_content: str
    is_approved: bool
    moderation_reason: Optional[str] = None
    post_content: Optional[str] = None


class NewsService:
    def __init__(self):
        self.content_service = ContentService()
        self.moderation_service = ModerationService()
        self.db = get_database()

        # News API configuration
        self.news_api_key = settings.news_api_key
        self.news_api_url = "https://newsapi.org/v2/top-headlines"

        # Local news endpoint
        self.local_news_url = "http://localhost:8000/get-live-news"

        # OpenAI configuration
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def fetch_latest_news(
        self, category: str = "technology", country: str = "us", page_size: int = 10
    ) -> List[NewsArticle]:
        """Fetch latest news articles from News API"""
        try:
            if not self.news_api_key:
                logger.warning("News API key not configured, using mock data")
                return self._get_mock_news()

            params = {
                "apiKey": self.news_api_key,
                "category": category,
                "country": country,
                "pageSize": page_size,
                "sortBy": "publishedAt",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.news_api_url, params=params) as response:
                    if response.status != 200:
                        logger.exception(f"News API request failed: {response.status}")
                        return self._get_mock_news()

                    data = await response.json()
                    articles = []

                    for article_data in data.get("articles", []):
                        if not article_data.get("title") or not article_data.get("content"):
                            continue

                        article = NewsArticle(
                            title=article_data["title"],
                            content=article_data["content"] or article_data["description"] or "",
                            source=article_data.get("source", {}).get("name", "Unknown"),
                            published_at=datetime.fromisoformat(
                                article_data["publishedAt"].replace("Z", "+00:00")
                            ),
                            url=article_data["url"],
                            image_url=article_data.get("urlToImage"),
                            category=category,
                            relevance_score=1.0,  # Default score
                        )
                        articles.append(article)

                    return articles

        except Exception as e:
            logger.exception(f"Failed to fetch news: {e}")
            return self._get_mock_news()

    def _get_mock_news(self) -> List[NewsArticle]:
        """Return mock news data for testing"""
        now = datetime.now(timezone.utc)
        return [
            NewsArticle(
                title="Coimbatore IT Park Expansion: New Tech Hub Development",
                content="Coimbatore's IT sector is set for major expansion with the announcement of a new technology hub in the city. The project, expected to create over 5000 jobs, will focus on software development, AI research, and digital innovation. Local businesses and educational institutions are collaborating to make Coimbatore a leading tech destination in South India.",
                source="Coimbatore Business Times",
                published_at=now,
                url="https://example.com/coimbatore-it-expansion",
                category="technology",
                relevance_score=0.95,
            ),
            NewsArticle(
                title="New Medical College Opens in Coimbatore",
                content="A state-of-the-art medical college has been inaugurated in Coimbatore, adding to the city's reputation as a healthcare hub. The institution will offer advanced medical training and research facilities, contributing to the region's healthcare infrastructure and creating opportunities for aspiring medical professionals.",
                source="Coimbatore Health News",
                published_at=now,
                url="https://example.com/coimbatore-medical-college",
                category="health",
                relevance_score=0.9,
            ),
            NewsArticle(
                title="AI Revolution: New Breakthrough in Machine Learning",
                content="Scientists have developed a revolutionary new approach to machine learning that could transform how AI systems process information. The breakthrough promises more efficient and accurate AI models across various industries.",
                source="Tech Today",
                published_at=now,
                url="https://example.com/ai-breakthrough",
                category="technology",
                relevance_score=0.9,
            ),
            NewsArticle(
                title="Coimbatore Textile Industry Adopts Sustainable Practices",
                content="Leading textile manufacturers in Coimbatore are transitioning to eco-friendly production methods. The initiative, supported by local government and industry associations, aims to reduce environmental impact while maintaining the city's position as a major textile hub in India.",
                source="Coimbatore Industrial News",
                published_at=now,
                url="https://example.com/coimbatore-textile-sustainability",
                category="business",
                relevance_score=0.85,
            ),
            NewsArticle(
                title="Green Tech: Solar Panel Efficiency Reaches New Heights",
                content="A new type of solar panel has achieved record-breaking efficiency levels, making renewable energy more accessible and cost-effective for consumers worldwide.",
                source="Green Energy News",
                published_at=now,
                url="https://example.com/solar-breakthrough",
                category="technology",
                relevance_score=0.8,
            ),
        ]

    def parse_social_media_json(
        self, json_data: Dict[str, Any], city: str = "Coimbatore"
    ) -> List[NewsArticle]:
        """Parse social media JSON data directly"""
        articles = []

        try:
            logger.info(f"Parsing social media JSON for city: {city}")

            # Process Facebook posts
            facebook_posts = json_data.get("facebook_posts", {}).get("results", [])
            for post in facebook_posts:
                if post.get("message"):
                    # Convert timestamp to datetime
                    timestamp = post.get("timestamp")
                    if timestamp:
                        published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)

                    # Create title from first line of message or use default
                    message_lines = post["message"].split("\n")
                    title = (
                        message_lines[0][:100] if message_lines[0] else f"Facebook Post - {city}"
                    )

                    article = NewsArticle(
                        title=title,
                        content=post["message"],
                        source=f"Facebook - {post.get('author', {}).get('name', 'Unknown')}",
                        published_at=published_at,
                        url=post.get("url", ""),
                        image_url=post.get("image") or post.get("video_thumbnail"),
                        category="social_media",
                        relevance_score=0.8,
                    )
                    articles.append(article)

            # Process Twitter posts
            twitter_data = json_data.get("twitter_posts", {}).get("result", {}).get("timeline", {})
            if twitter_data and "instructions" in twitter_data:
                for instruction in twitter_data["instructions"]:
                    if instruction.get("type") == "TimelineAddEntries":
                        for entry in instruction.get("entries", []):
                            if entry.get("entryId", "").startswith("tweet-"):
                                content = entry.get("content", {})
                                item_content = content.get("itemContent", {})
                                tweet_results = item_content.get("tweet_results", {})

                                if tweet_results and "result" in tweet_results:
                                    tweet = tweet_results["result"]
                                    legacy = tweet.get("legacy", {})

                                    if legacy.get("full_text"):
                                        # Convert timestamp to datetime
                                        created_at_str = legacy.get("created_at")
                                        if created_at_str:
                                            # Parse Twitter's date format
                                            try:
                                                published_at = datetime.strptime(
                                                    created_at_str, "%a %b %d %H:%M:%S +0000 %Y"
                                                ).replace(tzinfo=timezone.utc)
                                            except ValueError:
                                                published_at = datetime.now(timezone.utc)
                                        else:
                                            published_at = datetime.now(timezone.utc)

                                        # Create title from first line of text
                                        text_lines = legacy["full_text"].split("\n")
                                        title = (
                                            text_lines[0][:100]
                                            if text_lines[0]
                                            else f"Twitter Post - {city}"
                                        )

                                        # Get user info
                                        user_info = (
                                            tweet.get("core", {})
                                            .get("user_results", {})
                                            .get("result", {})
                                        )
                                        screen_name = user_info.get("core", {}).get(
                                            "screen_name", "Unknown"
                                        )

                                        article = NewsArticle(
                                            title=title,
                                            content=legacy["full_text"],
                                            source=f"Twitter - {screen_name}",
                                            published_at=published_at,
                                            url=f"https://twitter.com/i/status/{legacy.get('id_str', '')}",
                                            category="social_media",
                                            relevance_score=0.8,
                                        )
                                        articles.append(article)

            logger.info(f"Parsed {len(articles)} articles from JSON data")
            return articles

        except Exception as e:
            logger.exception(f"Failed to parse social media JSON: {e}")
            return []

    async def fetch_latest_news_from_local(
        self, city: str = "Coimbatore", pipeline_id: Optional[str] = None
    ) -> List[NewsArticle]:
        """Fetch latest news articles from local /get-live-news endpoint"""
        try:
            logger.info(f"Fetching news from local endpoint for city: {city}")

            async with aiohttp.ClientSession() as session:
                async with session.get(self.local_news_url, params={"city": city}) as response:
                    if response.status != 200:
                        logger.exception(f"Local news API request failed: {response.status}")
                        return []

                    data = await response.json()
                    articles = []

                    logger.info(f"Received data structure: {list(data.keys())}")

                    # Process Facebook posts
                    facebook_posts = data.get("facebook_posts", {}).get("results", [])
                    for post in facebook_posts:
                        if post.get("message"):
                            # Convert timestamp to datetime
                            timestamp = post.get("timestamp")
                            if timestamp:
                                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            else:
                                published_at = datetime.now(timezone.utc)

                            # Create title from first line of message or use default
                            message_lines = post["message"].split("\n")
                            title = (
                                message_lines[0][:100]
                                if message_lines[0]
                                else f"Facebook Post - {city}"
                            )

                            article = NewsArticle(
                                title=title,
                                content=post["message"],
                                source=f"Facebook - {post.get('author', {}).get('name', 'Unknown')}",
                                published_at=published_at,
                                url=post.get("url", ""),
                                image_url=post.get("image") or post.get("video_thumbnail"),
                                category="social_media",
                                relevance_score=0.8,
                            )
                            articles.append(article)

                    # Process Twitter posts
                    twitter_data = (
                        data.get("twitter_posts", {}).get("result", {}).get("timeline", {})
                    )
                    if twitter_data and "instructions" in twitter_data:
                        for instruction in twitter_data["instructions"]:
                            if instruction.get("type") == "TimelineAddEntries":
                                for entry in instruction.get("entries", []):
                                    if entry.get("entryId", "").startswith("tweet-"):
                                        content = entry.get("content", {})
                                        item_content = content.get("itemContent", {})
                                        tweet_results = item_content.get("tweet_results", {})

                                        if tweet_results and "result" in tweet_results:
                                            tweet = tweet_results["result"]
                                            legacy = tweet.get("legacy", {})

                                            if legacy.get("full_text"):
                                                # Convert timestamp to datetime
                                                created_at_str = legacy.get("created_at")
                                                if created_at_str:
                                                    # Parse Twitter's date format
                                                    try:
                                                        published_at = datetime.strptime(
                                                            created_at_str,
                                                            "%a %b %d %H:%M:%S +0000 %Y",
                                                        ).replace(tzinfo=timezone.utc)
                                                    except ValueError:
                                                        published_at = datetime.now(timezone.utc)
                                                else:
                                                    published_at = datetime.now(timezone.utc)

                                                # Create title from first line of text
                                                text_lines = legacy["full_text"].split("\n")
                                                title = (
                                                    text_lines[0][:100]
                                                    if text_lines[0]
                                                    else f"Twitter Post - {city}"
                                                )

                                                article = NewsArticle(
                                                    title=title,
                                                    content=legacy["full_text"],
                                                    source=f"Twitter - {tweet.get('core', {}).get('user_results', {}).get('result', {}).get('core', {}).get('screen_name', 'Unknown')}",
                                                    published_at=published_at,
                                                    url=f"https://twitter.com/i/status/{legacy.get('id_str', '')}",
                                                    category="social_media",
                                                    relevance_score=0.8,
                                                )
                                                articles.append(article)

                    logger.info(f"Fetched {len(articles)} articles from local endpoint")
                    return articles

        except Exception as e:
            logger.exception(f"Failed to fetch news from local endpoint: {e}")
            return []

    async def get_last_sync_time(self, pipeline_id: str) -> Optional[datetime]:
        """Get the timestamp of the last successful news sync"""
        try:
            # Get the most recent news item for this pipeline
            response = (
                self.db.service_client.table("external_news_items")
                .select("fetched_at")
                .eq("pipeline_id", pipeline_id)
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                return datetime.fromisoformat(response.data[0]["fetched_at"])
            return None

        except Exception as e:
            logger.exception(f"Failed to get last sync time: {e}")
            return None

    async def store_news_articles(self, articles: List[NewsArticle], pipeline_id: str) -> List[str]:
        """Store news articles in the database"""
        stored_ids = []

        try:
            for article in articles:
                # Check if article already exists (by URL or title)
                existing = (
                    self.db.service_client.table("external_news_items")
                    .select("id")
                    .or_(f"source_url.eq.{article.url},title.eq.{article.title}")
                    .eq("pipeline_id", pipeline_id)
                    .execute()
                )

                if existing.data:
                    logger.info(f"Article already exists: {article.title}")
                    continue

                # Insert new article
                news_data = {
                    "id": str(uuid.uuid4()),
                    "pipeline_id": pipeline_id,
                    "title": article.title,
                    "content": article.content,
                    "source": article.source,
                    "source_url": article.url,
                    "published_at": article.published_at.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "moderation_status": "pending",
                    "moderation_score": article.relevance_score,
                }

                response = self.db.service_client.table("external_news_items").insert(news_data).execute()

                if response.data:
                    stored_ids.append(response.data[0]["id"])
                    logger.info(f"Stored news article: {article.title}")

        except Exception as e:
            logger.exception(f"Failed to store news articles: {e}")

        return stored_ids

    async def fetch_and_store_new_news(
        self, city: str = "Coimbatore", pipeline_id: str = None
    ) -> Dict[str, Any]:
        """Fetch new news since last sync and store them"""
        try:
            # Get last sync time
            last_sync = await self.get_last_sync_time(pipeline_id)

            # Fetch latest news from local endpoint
            articles = await self.fetch_latest_news_from_local(city, pipeline_id)

            if not articles:
                return {
                    "success": True,
                    "articles_fetched": 0,
                    "articles_stored": 0,
                    "last_sync": last_sync.isoformat() if last_sync else None,
                }

            # Filter articles published after last sync
            if last_sync:
                new_articles = [article for article in articles if article.published_at > last_sync]
                logger.info(f"Found {len(new_articles)} new articles since last sync")
            else:
                new_articles = articles
                logger.info(f"No previous sync found, processing all {len(articles)} articles")

            # Store new articles
            stored_ids = await self.store_news_articles(new_articles, pipeline_id)

            return {
                "success": True,
                "articles_fetched": len(articles),
                "articles_stored": len(stored_ids),
                "last_sync": last_sync.isoformat() if last_sync else None,
                "new_sync_time": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.exception(f"Failed to fetch and store news: {e}")
            return {"success": False, "error": str(e), "articles_fetched": 0, "articles_stored": 0}

    async def get_pending_news_articles(
        self, pipeline_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get news articles pending moderation"""
        try:
            response = (
                self.db.service_client.table("external_news_items")
                .select("*")
                .eq("pipeline_id", pipeline_id)
                .eq("moderation_status", "pending")
                .order("fetched_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.exception(f"Failed to get pending news articles: {e}")
            return []

    async def update_news_moderation_status(
        self,
        news_id: str,
        status: str,
        score: Optional[float] = None,
        flags: Optional[List[str]] = None,
        processed_content: Optional[str] = None,
    ) -> bool:
        """Update moderation status of a news article"""
        try:
            update_data = {
                "moderation_status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if score is not None:
                update_data["moderation_score"] = score
            if flags is not None:
                update_data["moderation_flags"] = flags
            if processed_content is not None:
                update_data["processed_content"] = processed_content

            response = (
                self.db.service_client.table("external_news_items")
                .update(update_data)
                .eq("id", news_id)
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.exception(f"Failed to update news moderation status: {e}")
            return False

    async def moderate_news_content(
        self, article: NewsArticle, custom_approval_logic: Optional[str] = None
    ) -> ProcessedNews:
        """Moderate news content using the dedicated moderation service"""
        try:
            # Use the moderation service
            moderation_result = await self.moderation_service.moderate_content(
                title=article.title,
                content=article.content,
                source=article.source,
                category=article.category or "general",
                city_or_keyword=article.category,
                custom_approval_logic=custom_approval_logic,
            )

            if not moderation_result.is_approved:
                return ProcessedNews(
                    article=article,
                    moderated_content=article.content,
                    is_approved=False,
                    moderation_reason=moderation_result.reason,
                )

            # Generate social media post content for approved articles
            post_content = await self._generate_post_content(article)

            return ProcessedNews(
                article=article,
                moderated_content=article.content,
                is_approved=True,
                post_content=post_content,
                moderation_reason=moderation_result.reason,
            )

        except Exception as e:
            logger.exception(f"Failed to moderate content: {e}")
            return ProcessedNews(
                article=article,
                moderated_content=article.content,
                is_approved=False,
                moderation_reason=f"Moderation error: {str(e)}",
            )

    async def _generate_post_content(self, article: NewsArticle) -> str:
        """Generate engaging social media post from news article"""
        try:
            if not self.openai_client:
                return self._create_fallback_post_content(article)

            # Get formatted messages from prompts configuration
            messages = Prompts.get_news_post_generation_messages(
                title=article.title,
                content=article.content,
                source=article.source,
                category=article.category or "general"
            )

            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.exception(f"Failed to generate post content: {e}")
            return self._create_fallback_post_content(article)

    def _create_fallback_post_content(self, article: NewsArticle) -> str:
        """Create basic post content without OpenAI"""
        emoji_map = {
            "technology": "💻",
            "science": "🔬",
            "business": "💼",
            "health": "🏥",
            "sports": "⚽",
            "entertainment": "🎬",
        }

        emoji = emoji_map.get(article.category, "📰")

        # Create a short, engaging post
        post = f"{emoji} {article.title}\n\n"

        # Add a brief excerpt
        if len(article.content) > 100:
            post += f"{article.content[:100]}..."
        else:
            post += article.content

        post += f"\n\nSource: {article.source} 🔗"

        return post

    async def process_news_batch(
        self, city: str = "Coimbatore", pipeline_id: str = None, max_articles: int = 5
    ) -> List[ProcessedNews]:
        """Process a batch of news articles"""
        try:
            # Fetch latest news from local endpoint
            articles = await self.fetch_latest_news_from_local(city=city, pipeline_id=pipeline_id)

            if not articles:
                logger.warning("No articles fetched")
                return []

            # Limit articles to process
            articles = articles[:max_articles]

            # Process each article
            processed_news = []
            for article in articles:
                processed = await self.moderate_news_content(article)
                processed_news.append(processed)

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            return processed_news

        except Exception as e:
            logger.exception(f"Failed to process news batch: {e}")
            return []

    async def create_posts_from_news(
        self, processed_news: List[ProcessedNews], tenant_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """Create posts from processed news articles"""
        created_posts = []

        for news in processed_news:
            if not news.is_approved or not news.post_content:
                logger.info(
                    f"Skipping post creation for article: {news.article.title} - "
                    f"Approved: {news.is_approved}, Content: {bool(news.post_content)}"
                )
                continue

            try:
                # Create post data
                post_data = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "title": f"Auto-generated: {news.article.title[:50]}...",
                    "content": {"text": news.post_content, "media_ids": []},
                    "channels": [],  # Will be set based on tenant's social accounts
                    "status": "draft",  # Start as draft, can be auto-published if configured
                    "metadata": {
                        "source": "automated_news",
                        "original_article_url": news.article.url,
                        "news_source": news.article.source,
                        "published_at": news.article.published_at.isoformat(),
                        "category": news.article.category,
                    },
                }

                # Add news_item_id directly if available
                if hasattr(news.article, "news_item_id") and news.article.news_item_id:
                    post_data["news_item_id"] = news.article.news_item_id
                    logger.info(
                        f"✅ Set news_item_id in post: {news.article.news_item_id} for {news.article.title[:50]}..."
                    )

                created_posts.append(post_data)
                logger.info(f"Created post for article: {news.article.title}")

            except Exception as e:
                logger.exception(f"Failed to create post for article {news.article.title}: {e}")

        return created_posts

    async def get_trending_categories(self) -> List[str]:
        """Get trending news categories for the day"""
        # This could be enhanced to use trending APIs or ML models
        categories = ["technology", "science", "business", "health"]
        return categories

    def calculate_relevance_score(self, article: NewsArticle, keywords: List[str] = None) -> float:
        """Calculate relevance score for an article based on keywords and other factors"""
        if not keywords:
            return 1.0

        score = 0.0
        content_lower = f"{article.title} {article.content}".lower()

        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1.0

        # Normalize by keyword count
        if keywords:
            score = score / len(keywords)

        # Boost recent articles
        hours_old = (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600
        if hours_old < 1:
            score *= 1.5
        elif hours_old < 6:
            score *= 1.2
        elif hours_old < 24:
            score *= 1.1

        return min(score, 1.0)
