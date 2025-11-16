"""
OpenAI Processing Service for fast, reliable LLM analysis
Uses OpenAI GPT for analyzing and enriching social media posts
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import time

# Load environment variables
load_dotenv()
from app.models.posts_table import PostCreate, PostUpdate, SentimentLabel
from app.models.raw_data import RawDataInDB, ProcessingStatus

class OpenAIProcessingService:
    """Service for processing posts with OpenAI GPT"""
    
    def __init__(self):
        """Initialize OpenAI service"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "sk-openai_api_key_here":
            print("Warning: OPENAI_API_KEY not configured properly")
            self.api_key = None
        
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"  # Fast and reliable
        self.max_tokens = 500
        self.temperature = 0.1
        
        # Processing configuration
        self.batch_size = 50
        self.max_retries = 1  # Minimal retries for speed
        self.timeout = 30.0   # 30 second timeout
        
    async def process_raw_data(self, raw_data: RawDataInDB) -> Optional[PostCreate]:
        """
        Process raw data into PostCreate model using OpenAI
        
        Args:
            raw_data: Raw data to process
            
        Returns:
            PostCreate model or None if processing fails
        """
        if not self.api_key:
            return None
            
        try:
            # Extract post data from raw JSON
            raw_json = raw_data.raw_json
            if not raw_json or not isinstance(raw_json, dict):
                return None
                
            # Get basic post info
            platform = raw_data.platform
            post_text = self._extract_text(raw_json, platform)
            if not post_text:
                return None
                
            # Create OpenAI analysis
            analysis = await self._analyze_post_with_openai(
                post_text=post_text,
                platform=platform,
                author=self._extract_author(raw_json),
                raw_data=raw_json
            )
            
            if not analysis:
                return None
                
            # Build PostCreate model
            post_create = PostCreate(
                platform_post_id=self._extract_post_id(raw_json, platform),
                platform=platform,
                cluster_id=raw_data.cluster_id,
                author_username=analysis.get("author", "unknown"),
                author_followers=self._extract_followers(raw_json),
                post_text=post_text,
                post_url=self._extract_url(raw_json, platform),
                posted_at=self._extract_datetime(raw_json),
                likes=self._extract_engagement(raw_json, "likes"),
                comments=self._extract_engagement(raw_json, "comments"),
                shares=self._extract_engagement(raw_json, "shares"),
                views=self._extract_engagement(raw_json, "views"),
                language=analysis.get("language", "Unknown"),
                sentiment=analysis.get("sentiment", "neutral"),
                intelligence=analysis.get("intelligence", {}),
                keywords=analysis.get("keywords", []),
                entities=analysis.get("entities", [])
            )
            
            return post_create
            
        except Exception as e:
            print(f"❌ Error processing raw data {raw_data.id}: {e}")
            return None
    
    async def process_post_intelligence(self, post_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add intelligence analysis to existing post using OpenAI
        
        Args:
            post_dict: Post dictionary from database
            
        Returns:
            Intelligence data or None if processing fails
        """
        if not self.api_key:
            return None
            
        try:
            post_text = post_dict.get("post_text", "")
            platform = post_dict.get("platform", "unknown")
            author = post_dict.get("author_username", "unknown")
            
            if not post_text:
                return None
                
            # Create intelligence analysis
            analysis = await self._analyze_post_with_openai(
                post_text=post_text,
                platform=platform,
                author=author,
                raw_data=None,
                intelligence_only=True
            )
            
            return analysis.get("intelligence", {}) if analysis else None
            
        except Exception as e:
            print(f"❌ Error processing post intelligence: {e}")
            return None
    
    async def _analyze_post_with_openai(
        self, 
        post_text: str, 
        platform: str, 
        author: str, 
        raw_data: Optional[Dict] = None,
        intelligence_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Analyze post with OpenAI GPT"""
        
        if intelligence_only:
            prompt = self._create_intelligence_prompt(post_text, platform, author)
        else:
            prompt = self._create_analysis_prompt(post_text, platform, author)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert social media analyst specializing in Tamil political content."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return json.loads(content)
                    else:
                        error_text = await response.text()
                        print(f"❌ OpenAI API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            print(f"⏰ OpenAI timeout for text: {post_text[:50]}...")
            return None
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return None
    
    def _create_analysis_prompt(self, post_text: str, platform: str, author: str) -> str:
        """Create comprehensive analysis prompt"""
        return f"""
Analyze this {platform} post by {author} and return a JSON response with the following structure:

Post: "{post_text}"

Return JSON with these exact fields:
{{
    "language": "Tamil|English|Mixed|Other",
    "sentiment": "positive|neutral|negative",
    "author": "cleaned_author_name",
    "keywords": ["keyword1", "keyword2"],
    "entities": ["entity1", "entity2"],
    "intelligence": {{
        "is_threat": false,
        "threat_level": "low|medium|high",
        "sentiment_score": 0.5,
        "political_relevance": true,
        "topic_category": "politics|general|news",
        "contains_tamil": true,
        "engagement_potential": "low|medium|high"
    }}
}}

Focus on:
1. Detecting Tamil language (தமிழ் script or romanized Tamil)
2. Political sentiment about DMK, ADMK, or Tamil Nadu politics
3. Threat assessment for harmful content
4. Key entities and topics mentioned
"""

    def _create_intelligence_prompt(self, post_text: str, platform: str, author: str) -> str:
        """Create intelligence-only prompt for existing posts"""
        return f"""
Analyze this {platform} post for intelligence metrics and return JSON:

Post: "{post_text}"
Author: {author}

Return JSON with this structure:
{{
    "intelligence": {{
        "is_threat": false,
        "threat_level": "low|medium|high", 
        "sentiment_score": 0.5,
        "political_relevance": true,
        "topic_category": "politics|general|news",
        "contains_tamil": true,
        "engagement_potential": "low|medium|high",
        "entities_mentioned": ["entity1", "entity2"],
        "key_topics": ["topic1", "topic2"]
    }}
}}

Focus on Tamil political content, threats, and engagement potential.
"""
    
    # Helper methods for extracting data from raw JSON
    def _extract_text(self, raw_json: Dict, platform: str) -> str:
        """Extract post text from raw JSON"""
        if platform == "X":
            return raw_json.get("text", raw_json.get("full_text", ""))
        elif platform == "YouTube":
            return raw_json.get("snippet", {}).get("description", "")
        elif platform == "Facebook":
            return raw_json.get("message", raw_json.get("text", ""))
        return ""
    
    def _extract_author(self, raw_json: Dict) -> str:
        """Extract author from raw JSON"""
        author = raw_json.get("author", {})
        if isinstance(author, dict):
            return author.get("name", author.get("username", "unknown"))
        return str(author) if author else "unknown"
    
    def _extract_post_id(self, raw_json: Dict, platform: str) -> str:
        """Extract post ID from raw JSON"""
        return raw_json.get("id", raw_json.get("post_id", f"{platform}_{int(time.time())}"))
    
    def _extract_url(self, raw_json: Dict, platform: str) -> str:
        """Extract post URL from raw JSON"""
        return raw_json.get("url", raw_json.get("post_url", ""))
    
    def _extract_datetime(self, raw_json: Dict) -> datetime:
        """Extract datetime from raw JSON"""
        timestamp = raw_json.get("timestamp", raw_json.get("created_at"))
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                pass
        return datetime.utcnow()
    
    def _extract_followers(self, raw_json: Dict) -> int:
        """Extract follower count from raw JSON"""
        author = raw_json.get("author", {})
        if isinstance(author, dict):
            return author.get("followers_count", 0)
        return 0
    
    def _extract_engagement(self, raw_json: Dict, metric: str) -> int:
        """Extract engagement metrics from raw JSON"""
        # Try direct field names
        value = raw_json.get(f"{metric}_count", raw_json.get(metric, 0))
        
        # Try alternative field names
        if not value:
            alt_names = {
                "likes": ["reactions_count", "favorite_count"],
                "comments": ["comments_count", "reply_count"],
                "shares": ["reshare_count", "retweet_count"],
                "views": ["view_count", "impression_count"]
            }
            for alt_name in alt_names.get(metric, []):
                value = raw_json.get(alt_name, 0)
                if value:
                    break
        
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0