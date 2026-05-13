"""
Content moderation service for OmniPush platform.
Specializes in filtering content for Coimbatore city relevance and general news quality.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from openai import AsyncOpenAI
from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    """Result of content moderation"""
    is_approved: bool
    reason: str
    content_type: str  # 'coimbatore_local', 'generic_news', 'irrelevant', 'spam', 'harmful'
    confidence: float
    flagged_categories: Optional[List[str]] = None
    suggested_actions: Optional[List[str]] = None


class ModerationService:
    """Service for moderating content using OpenAI GPT API"""
    
    def __init__(self):
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            logger.warning("OpenAI API key not configured - moderation will be limited")
    
    async def moderate_content(
        self,
        title: str,
        content: str,
        source: str = "unknown",
        category: str = "general",
        city_or_keyword: str = "coimbatore",
        custom_approval_logic: Optional[str] = None
    ) -> ModerationResult:
        """
        Moderate content for relevance to specified city/keyword and general news quality

        Args:
            title: Article title
            content: Article content
            source: News source
            category: Content category
            city_or_keyword: City or keyword to filter content for
            custom_approval_logic: Optional custom approval logic in natural language

        Returns:
            ModerationResult with approval status and details
        """
        try:
            if not self.openai_client:
                return self._fallback_moderation(title, content, city_or_keyword)
            
            # Step 1: Check for harmful/inappropriate content
            safety_check = await self._check_content_safety(title, content)
            if not safety_check['is_safe']:
                return ModerationResult(
                    is_approved=False,
                    reason=f"Content flagged as unsafe: {safety_check['reason']}",
                    content_type='harmful',
                    confidence=safety_check['confidence'],
                    flagged_categories=safety_check['flagged_categories']
                )
            
            # Step 2: If custom approval logic is provided, use it
            if custom_approval_logic:
                custom_check = await self._check_custom_approval_logic(
                    title, content, source, category, custom_approval_logic
                )
                return ModerationResult(
                    is_approved=custom_check['is_approved'],
                    reason=custom_check['reason'],
                    content_type=custom_check.get('content_type', 'custom'),
                    confidence=custom_check['confidence'],
                    suggested_actions=custom_check.get('suggested_actions', [])
                )

            # Step 3: Otherwise, check relevance to specified city/keyword or general news
            relevance_check = await self._check_content_relevance(title, content, source, category, city_or_keyword)

            return ModerationResult(
                is_approved=relevance_check['is_relevant'],
                reason=relevance_check['reason'],
                content_type=relevance_check['content_type'],
                confidence=relevance_check['confidence'],
                suggested_actions=relevance_check.get('suggested_actions', [])
            )
            
        except Exception as e:
            logger.exception(f"Moderation failed: {e}")
            return ModerationResult(
                is_approved=False,
                reason=f"Moderation error: {str(e)}",
                content_type='error',
                confidence=0.0
            )
    
    async def _check_content_safety(self, title: str, content: str) -> Dict[str, Any]:
        """Check if content is safe and appropriate using OpenAI moderation"""
        try:
            moderation_response = await self.openai_client.moderations.create(
                input=f"{title}\n\n{content}"
            )
            
            moderation_result = moderation_response.results[0]
            
            if moderation_result.flagged:
                flagged_categories = [
                    category for category, flagged in moderation_result.categories.model_dump().items()
                    if flagged
                ]
                
                return {
                    'is_safe': False,
                    'reason': f"Content flagged for: {', '.join(flagged_categories)}",
                    'confidence': 0.9,
                    'flagged_categories': flagged_categories
                }
            
            return {
                'is_safe': True,
                'reason': 'Content passed safety checks',
                'confidence': 0.95,
                'flagged_categories': []
            }
            
        except Exception as e:
            logger.exception(f"Safety check failed: {e}")
            return {
                'is_safe': False,
                'reason': f'Safety check error: {str(e)}',
                'confidence': 0.0,
                'flagged_categories': []
            }
    
    async def _check_content_relevance(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        city_or_keyword: str
    ) -> Dict[str, Any]:
        """Check if content is relevant to specified city/keyword or general news"""
        try:
            prompt = f"""
            Analyze this news content and determine its relevance for our platform:

            TITLE: {title}
            CONTENT: {content[:1000]}...
            SOURCE: {source}
            CATEGORY: {category}

            RELEVANCE CRITERIA:

            1. LOCATION/KEYWORD SPECIFIC CONTENT (High Priority):
               - Local news, events, developments specifically about {city_or_keyword}
               - Business, technology, education, healthcare news from {city_or_keyword}
               - Cultural, social, community news from {city_or_keyword}
               - Infrastructure, real estate, economic developments in {city_or_keyword}
               - Local government, civic issues, and public services in {city_or_keyword}
               - Educational institutions, hospitals, and major organizations in {city_or_keyword}
               - Content directly related to or mentioning {city_or_keyword}

            2. GENERIC NEWS (Medium Priority):
               - Major national/international developments with broad impact
               - Technology breakthroughs and innovations
               - Scientific discoveries and research
               - Business and economic news of significance
               - Health and wellness updates
               - Environmental and sustainability news
               - Educational and career development news

            REJECTION CRITERIA:
            - Spam, clickbait, or low-quality content
            - Harmful, misleading, or fake news
            - Content completely unrelated to {city_or_keyword} or general news
            - Overly promotional or commercial content without news value
            - Content that could cause harm or spread misinformation
            - Gossip, celebrity news, or entertainment without broader significance

            Please respond with a JSON object:
            {{
                "is_relevant": true/false,
                "reason": "Brief explanation of relevance decision",
                "content_type": "location_specific" or "generic_news" or "irrelevant" or "spam",
                "confidence": 0.0-1.0,
                "suggested_actions": ["action1", "action2"] (optional)
            }}
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a content moderation expert specializing in location-specific news ({city_or_keyword}) and general news content. You help filter high-quality, relevant content while rejecting spam, harmful, or irrelevant material. Be precise and objective in your analysis."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(result_text)
                return {
                    'is_relevant': result.get('is_relevant', False),
                    'reason': result.get('reason', 'No reason provided'),
                    'content_type': result.get('content_type', 'unknown'),
                    'confidence': result.get('confidence', 0.5),
                    'suggested_actions': result.get('suggested_actions', [])
                }
            except json.JSONDecodeError:
                logger.exception(f"Failed to parse GPT response: {result_text}")
                return {
                    'is_relevant': False,
                    'reason': 'Failed to analyze content relevance',
                    'content_type': 'unknown',
                    'confidence': 0.0,
                    'suggested_actions': []
                }
                
        except Exception as e:
            logger.exception(f"Relevance check failed: {e}")
            return {
                'is_relevant': False,
                'reason': f'Error checking relevance: {str(e)}',
                'content_type': 'error',
                'confidence': 0.0,
                'suggested_actions': []
            }
    
    async def _check_custom_approval_logic(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        custom_logic: str
    ) -> Dict[str, Any]:
        """Check content against custom approval logic using AI"""
        try:
            prompt = f"""
            Evaluate the following content against the provided approval logic.

            APPROVAL LOGIC:
            {custom_logic}

            CONTENT TO EVALUATE:
            Title: {title[:200]}
            Source: {source}
            Category: {category}
            Content: {content[:800]}

            Based on the approval logic, determine if this content should be approved or rejected.

            Respond with a JSON object containing:
            {{
                "is_approved": true/false,
                "reason": "Brief explanation of why it was approved or rejected based on the logic",
                "confidence": 0.0-1.0 (confidence in decision),
                "content_type": "category of content (news, social_media, announcement, etc.)",
                "suggested_actions": ["list", "of", "suggested", "actions", "if", "any"]
            }}
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a content moderation expert that evaluates content against specific approval criteria. Be precise and follow the provided logic strictly."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(result_text)
                return {
                    'is_approved': result.get('is_approved', False),
                    'reason': result.get('reason', 'No reason provided'),
                    'content_type': result.get('content_type', 'custom'),
                    'confidence': result.get('confidence', 0.5),
                    'suggested_actions': result.get('suggested_actions', [])
                }
            except json.JSONDecodeError:
                logger.exception(f"Failed to parse GPT response: {result_text}")
                return {
                    'is_approved': False,
                    'reason': 'Failed to evaluate against custom logic',
                    'content_type': 'error',
                    'confidence': 0.0,
                    'suggested_actions': []
                }

        except Exception as e:
            logger.exception(f"Custom logic check failed: {e}")
            return {
                'is_approved': False,
                'reason': f'Error checking custom approval logic: {str(e)}',
                'content_type': 'error',
                'confidence': 0.0,
                'suggested_actions': []
            }

    def _fallback_moderation(self, title: str, content: str, city_or_keyword: str = "coimbatore") -> ModerationResult:
        """Fallback moderation when OpenAI is not available"""
        # Basic keyword-based moderation
        content_lower = f"{title} {content}".lower()
        
        # Generate location-specific keywords based on city_or_keyword
        location_keywords = [city_or_keyword.lower()]

        # Add common variations if it's Coimbatore (for backward compatibility)
        if city_or_keyword.lower() == "coimbatore":
            location_keywords.extend([
                'kovai', 'tamil nadu', 'tamilnadu', 'south india',
                'psg', 'psg tech', 'psg college', 'psg hospital', 'psg ims',
                'coimbatore airport', 'peelamedu', 'rs puram', 'race course',
                'singanallur', 'saravanampatti', 'vadavalli', 'saibaba colony'
            ])
        else:
            # For other cities/keywords, add some generic variations
            location_keywords.extend([
                f"{city_or_keyword} city",
                f"{city_or_keyword} news",
                f"{city_or_keyword} local"
            ])
        
        # Check for spam indicators
        spam_indicators = [
            'click here', 'buy now', 'limited time', 'act now', 'don\'t miss',
            'exclusive offer', 'free money', 'make money fast', 'work from home',
            'weight loss', 'miracle cure', 'get rich quick'
        ]
        
        # Check for harmful content indicators
        harmful_indicators = [
            'hate speech', 'violence', 'discrimination', 'fake news',
            'conspiracy', 'misinformation', 'disinformation'
        ]
        
        # Check for location relevance
        is_location_related = any(keyword in content_lower for keyword in location_keywords)
        
        # Check for spam
        is_spam = any(indicator in content_lower for indicator in spam_indicators)
        
        # Check for harmful content
        is_harmful = any(indicator in content_lower for indicator in harmful_indicators)
        
        if is_harmful:
            return ModerationResult(
                is_approved=False,
                reason="Content contains potentially harmful indicators",
                content_type='harmful',
                confidence=0.7
            )
        
        if is_spam:
            return ModerationResult(
                is_approved=False,
                reason="Content appears to be spam",
                content_type='spam',
                confidence=0.6
            )
        
        if is_location_related:
            return ModerationResult(
                is_approved=True,
                reason=f"Content is relevant to {city_or_keyword}",
                content_type='location_specific',
                confidence=0.8
            )
        
        # Generic approval for non-spam content
        return ModerationResult(
            is_approved=True,
            reason="Content appears to be general news",
            content_type='generic_news',
            confidence=0.5
        )
    
    async def batch_moderate(self, articles: List[Dict[str, Any]]) -> List[ModerationResult]:
        """Moderate multiple articles in batch"""
        results = []
        
        for article in articles:
            result = await self.moderate_content(
                title=article.get('title', ''),
                content=article.get('content', ''),
                source=article.get('source', 'unknown'),
                category=article.get('category', 'general'),
                city_or_keyword=article.get('city_or_keyword', 'coimbatore')
            )
            results.append(result)
        
        return results
    
    def get_moderation_stats(self, results: List[ModerationResult]) -> Dict[str, Any]:
        """Get statistics from moderation results"""
        total = len(results)
        approved = len([r for r in results if r.is_approved])
        rejected = total - approved
        
        content_types = {}
        for result in results:
            content_type = result.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        return {
            'total_articles': total,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0,
            'content_types': content_types,
            'average_confidence': sum(r.confidence for r in results) / total if total > 0 else 0
        }
