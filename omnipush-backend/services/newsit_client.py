"""
NewsIt API Client Service
Handles communication with NewsIt API to fetch news items
"""
import re
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.config import settings
from models.external_news import NewsItAPIResponse, NewsItAPIData
from utils.tamil_text_cleaner import safe_clean_tamil_content

logger = logging.getLogger(__name__)


class NewsItClient:
    """Client for interacting with NewsIt API"""

    def __init__(self):
        """Initialize NewsIt API client"""
        self.base_url = settings.newsit_api_base_url
        self.timeout = settings.newsit_api_timeout
        logger.info(f"NewsIt Client initialized with base URL: {self.base_url}")

    async def fetch_news_item(self, news_id: str) -> Optional[NewsItAPIData]:
        """
        Fetch a single news item from NewsIt API

        Args:
            news_id: The NewsIt news item ID

        Returns:
            NewsItAPIData object or None if fetch fails
        """
        url = f"{self.base_url}/news/{news_id}"

        try:
            logger.info(f"Fetching news item from NewsIt API: {news_id}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        'accept': 'application/json',
                        'User-Agent': 'SmartPost/1.0'
                    },
                    timeout=self.timeout
                )

                # Log response status
                logger.info(f"NewsIt API response status: {response.status_code}")

                # Raise for HTTP errors
                response.raise_for_status()

                # Parse response
                data = response.json()
                logger.debug(f"NewsIt API response: {data}")

                # Validate and parse using Pydantic model
                api_response = NewsItAPIResponse(**data)

                if api_response.status != 200:
                    logger.warning(f"NewsIt API returned non-200 status: {api_response.status}")
                    return None

                logger.info(f"Successfully fetched news item: {news_id}")
                return api_response.data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching news {news_id}: {e.response.status_code} - {e}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching news {news_id} after {self.timeout}s")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching news {news_id}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid JSON response from NewsIt API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching news {news_id}: {e}", exc_info=True)
            return None

    def transform_to_generic_format(
        self,
        newsit_data: NewsItAPIData,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Transform NewsIt API data to generic external news format

        Args:
            newsit_data: NewsIt API data object
            tenant_id: Tenant ID for the news item

        Returns:
            Dictionary ready for ExternalNewsItemCreate
        """
        try:
            # Extract primary language content (default to 'en')
            content_dict = newsit_data.content or {}
            primary_lang = 'en' if 'en' in content_dict else list(content_dict.keys())[0] if content_dict else None
            primary_content = content_dict.get(primary_lang) if primary_lang else None

            # Extract title and content
            title = primary_content.title if primary_content and primary_content.title else "Untitled"
            content = (
                primary_content.web_content or
                primary_content.ai_summary or
                primary_content.headlines or
                ""
            ) if primary_content else ""

            # Clean title - remove HTML tags and user mentions
            if title and title != "Untitled":
                title = re.sub(r'<[^>]+>', '', title)
                title = re.sub(r'@\w+', '', title)
                title = title.strip()
                # Clean Tamil text encoding issues
                title = safe_clean_tamil_content(title, "title")

            # Clean content - remove HTML tags and user mentions
            if content:
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'@\w+', '', content)
                content = content.strip()
                # Clean Tamil text encoding issues
                content = safe_clean_tamil_content(content, "content")

            # Validate that we have meaningful content
            # Skip news items where both title and content are empty
            if not title or title == "Untitled":
                if not content:
                    logger.warning(f"Skipping NewsIt item {newsit_data.id}: Both title and content are empty")
                    return None

            # Extract category
            category = None
            category_data = None
            if newsit_data.category:
                category = newsit_data.category.name
                category_data = {
                    "name": newsit_data.category.name,
                    "multilingual_names": newsit_data.category.multilingual_names,
                    "multilingual_descriptions": newsit_data.category.multilingual_descriptions
                }

            # Extract city
            city_data = None
            if newsit_data.city:
                city_data = {
                    "name": newsit_data.city.name,
                    "multilingual_names": newsit_data.city.multilingual_names
                }

            # Extract topics
            topics = []
            if newsit_data.topics:
                for topic in newsit_data.topics:
                    topics.append({
                        "name": topic.name,
                        "description": topic.description,
                        "multilingual_names": topic.multilingual_names,
                        "multilingual_descriptions": topic.multilingual_descriptions,
                        "image": topic.image
                    })

            # Extract images
            images = None
            if newsit_data.images:
                images = {
                    "original_url": newsit_data.images.original_url,
                    "original_key": newsit_data.images.original_key,
                    "thumbnail_url": newsit_data.images.thumbnail_url,
                    "thumbnail_key": newsit_data.images.thumbnail_key,
                    "low_res_url": newsit_data.images.low_res_url,
                    "low_res_key": newsit_data.images.low_res_key
                }

            # Build multilingual data structure with cleaned content
            multilingual_data = {}
            for lang_code, lang_content in content_dict.items():
                # Clean main content
                multilingual_lang_content = lang_content.web_content or lang_content.ai_summary or lang_content.headlines or ""
                if multilingual_lang_content:
                    multilingual_lang_content = re.sub(r'<[^>]+>', '', multilingual_lang_content)
                    multilingual_lang_content = re.sub(r'@\w+', '', multilingual_lang_content)
                    multilingual_lang_content = multilingual_lang_content.strip()
                    # Clean Tamil text encoding issues
                    multilingual_lang_content = safe_clean_tamil_content(multilingual_lang_content, f"multilingual_content_{lang_code}")

                # Clean title
                cleaned_title = lang_content.title or ""
                if cleaned_title:
                    cleaned_title = re.sub(r'<[^>]+>', '', cleaned_title)
                    cleaned_title = re.sub(r'@\w+', '', cleaned_title)
                    cleaned_title = cleaned_title.strip()
                    # Clean Tamil text encoding issues
                    cleaned_title = safe_clean_tamil_content(cleaned_title, f"multilingual_title_{lang_code}")

                # Clean headlines
                cleaned_headlines = lang_content.headlines or ""
                if cleaned_headlines:
                    cleaned_headlines = re.sub(r'<[^>]+>', '', cleaned_headlines)
                    cleaned_headlines = re.sub(r'@\w+', '', cleaned_headlines)
                    cleaned_headlines = cleaned_headlines.strip()
                    # Clean Tamil text encoding issues
                    cleaned_headlines = safe_clean_tamil_content(cleaned_headlines, f"multilingual_headlines_{lang_code}")

                # Clean ai_summary
                cleaned_ai_summary = lang_content.ai_summary or ""
                if cleaned_ai_summary:
                    cleaned_ai_summary = re.sub(r'<[^>]+>', '', cleaned_ai_summary)
                    cleaned_ai_summary = re.sub(r'@\w+', '', cleaned_ai_summary)
                    cleaned_ai_summary = cleaned_ai_summary.strip()
                    # Clean Tamil text encoding issues
                    cleaned_ai_summary = safe_clean_tamil_content(cleaned_ai_summary, f"multilingual_ai_summary_{lang_code}")

                multilingual_data[lang_code] = {
                    "title": cleaned_title,
                    "content": multilingual_lang_content,
                    "headlines": cleaned_headlines,
                    "ai_summary": cleaned_ai_summary
                }

            # Build generic format
            generic_data = {
                "tenant_id": tenant_id,
                "external_source": "newsit",
                "external_id": newsit_data.id,
                "title": title,
                "content": content,
                "multilingual_data": multilingual_data if multilingual_data else None,
                "category": category,
                "category_data": category_data,
                "city_data": city_data,
                "topics": topics if topics else None,
                "tags": newsit_data.tags if newsit_data.tags else None,
                "images": images,
                "is_breaking": newsit_data.is_breaking or False,
                "source_name": "NewsIt",
                "source_url": None  # NewsIt doesn't provide source URL
            }

            logger.debug(f"Transformed NewsIt data to generic format for news_id: {newsit_data.id}")
            return generic_data

        except Exception as e:
            logger.error(f"Error transforming NewsIt data: {e}", exc_info=True)
            raise

    async def fetch_and_transform(
        self,
        news_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch news from NewsIt API and transform to generic format

        Args:
            news_id: NewsIt news ID
            tenant_id: Tenant ID

        Returns:
            Transformed generic format dictionary or None (if skipped or fetch failed)
        """
        try:
            # Fetch from API
            newsit_data = await self.fetch_news_item(news_id)

            if not newsit_data:
                logger.warning(f"Failed to fetch news item: {news_id}")
                return None

            # Transform to generic format (may return None if content is empty)
            generic_data = self.transform_to_generic_format(newsit_data, tenant_id)

            if generic_data is None:
                logger.info(f"News item {news_id} skipped due to empty content")
                return None

            return generic_data

        except Exception as e:
            logger.error(f"Error in fetch_and_transform for {news_id}: {e}")
            return None


# Singleton instance
_newsit_client_instance: Optional[NewsItClient] = None


def get_newsit_client() -> NewsItClient:
    """Get or create NewsIt client singleton instance"""
    global _newsit_client_instance

    if _newsit_client_instance is None:
        _newsit_client_instance = NewsItClient()

    return _newsit_client_instance
