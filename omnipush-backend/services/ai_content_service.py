"""
AI Content Service for generating keywords and image search captions
"""
import logging
from typing import List, Optional, Dict, Any
from services.llm_service import llm_service, LLMProfile
from utils.tamil_text_cleaner import safe_truncate_tamil

logger = logging.getLogger(__name__)


class AIContentService:
    """Service for AI-powered content analysis and generation"""

    def __init__(self):
        """Initialize AI Content Service"""
        self.llm_service = llm_service
        if self.llm_service.is_available(LLMProfile.PRECISE):
            logger.info("LLM service initialized successfully")
        else:
            logger.warning("LLM service not available")

    async def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        Extract relevant keywords from post content using LLM

        Args:
            content: The post content text
            max_keywords: Maximum number of keywords to extract (default: 10)

        Returns:
            List of extracted keywords
        """
        if not self.llm_service.is_available(LLMProfile.PRECISE):
            logger.warning("LLM service not available, returning empty keywords")
            return []

        if not content or not content.strip():
            return []

        try:
            prompt = f"""Extract up to {max_keywords} relevant keywords from the following social media post content.
Return only the keywords as a comma-separated list, no explanations or additional text.
Focus on:
- Main topics and themes
- Brand names or product mentions
- Target audience identifiers
- Industry-specific terms
- Trending hashtags (without the # symbol)

Content: {content[:1500]}"""  # Limit content to prevent token overflow

            messages = [
                {
                    "role": "system",
                    "content": "You are a social media marketing expert specializing in SEO and content categorization.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_service.generate(
                messages=messages, profile=LLMProfile.PRECISE, max_tokens=200
            )

            if not response:
                return []

            keywords_text = response.strip()
            # Parse comma-separated keywords and clean them
            keywords = [k.strip().lower() for k in keywords_text.split(",") if k.strip()]
            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for keyword in keywords:
                if keyword not in seen and len(keyword) > 1:  # Skip single-character keywords
                    seen.add(keyword)
                    unique_keywords.append(keyword)

            return unique_keywords[:max_keywords]

        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return []

    async def generate_image_search_caption(
        self, content: str, keywords: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate an optimized image search term for finding relevant images based on post content

        Args:
            content: The post content text
            keywords: Optional list of relevant keywords to incorporate

        Returns:
            Generated image search term or None if failed
        """
        if not self.llm_service.is_available(LLMProfile.DEFAULT):
            logger.warning("LLM service not available, returning None")
            return None

        if not content or not content.strip():
            return None

        try:
            keywords_context = f"Keywords: {', '.join(keywords)}" if keywords else ""

            prompt = f"""Generate a concise image search term (max 80 characters) that would find the best stock photo or AI-generated image for this social media post.

The search term should:
- Be specific
- If this is about a person, party or any key item, include the it in the search term
- No need to describe the image or situation, just the search term.
- Search term can be directly a word or a phrase, mainly on the person, party or key item.

{keywords_context}

Content: {content[:1000]}

Return ONLY the search term, no quotes, no explanations."""

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at creating visual search queries for finding or generating images that match social media content.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_service.generate(
                messages=messages, profile=LLMProfile.DEFAULT, max_tokens=100, temperature=0.5
            )

            if not response:
                return None

            caption = response.strip()
            # Clean up the caption
            caption = caption.replace('"', "").replace("'", "")
            # Truncate if too long
            if len(caption) > 500:
                caption = caption[:497] + "..."

            return caption

        except Exception as e:
            logger.error(f"Failed to generate image search caption: {e}")
            return None

    async def analyze_post_content(self, content: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of post content including keywords and image caption

        Args:
            content: The post content text

        Returns:
            Dictionary with keywords and image_search_caption
        """
        result = {
            'keywords': [],
            'image_search_caption': None
        }

        if not content or not content.strip():
            return result

        # Extract keywords
        keywords = await self.extract_keywords(content)
        result['keywords'] = keywords

        # Generate image search caption using the extracted keywords
        caption = await self.generate_image_search_caption(content, keywords)
        result['image_search_caption'] = caption

        logger.info(f"Content analysis complete - Keywords: {len(keywords)}, Caption: {bool(caption)}")

        return result


# Singleton instance
ai_content_service = AIContentService()