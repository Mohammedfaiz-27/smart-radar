"""
LLM Processing Service for analyzing and enriching social media posts
Uses Gemini AI to generate structured intelligence from raw post data
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
from app.models.posts_table import PostCreate, PostUpdate, SentimentLabel
from app.models.raw_data import RawDataInDB, ProcessingStatus

class LLMProcessingService:
    """Service for processing posts with LLM intelligence"""
    
    def __init__(self):
        """Initialize LLM service with Gemini API"""
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            
            # Configure safety settings to be more permissive
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # Create model with safety settings
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash-lite',
                safety_settings=safety_settings
            )
        else:
            self.model = None
            print("Warning: GEMINI_API_KEY not configured")
        
        # Processing configuration
        self.batch_size = 50
        self.max_retries = 3
        self.retry_delay = 2.0
    
    def create_analysis_prompt(self, post_text: str, platform: str, author: str) -> str:
        """
        Create comprehensive prompt for sentiment and threat analysis

        Args:
            post_text: The text content of the post
            platform: Source platform (X, Facebook, YouTube, Google News)
            author: Post author username

        Returns:
            Formatted prompt for LLM with comprehensive analysis framework
        """
        # Clean text to avoid language detection issues
        clean_text = post_text.replace('\n', ' ').strip()[:800]  # Increased limit for better context

        prompt = f"""You are an Expert Social Media Content Analyzer specializing in Political Content. Analyze this post for BOTH sentiment and potential threats.

**POST TO ANALYZE:**
Platform: {platform}
Author: @{author}
Content: {clean_text}

**ANALYSIS FRAMEWORK:**

## SENTIMENT SCORING:
- Scale: -1.0 (Very Negative) to 1.0 (Very Positive)
- Consider: Text (50%), Emojis (30%), Hashtags/Keywords (20%)
- Detect: Sarcasm, irony, cultural context, political metaphors

## THREAT ASSESSMENT:
- Scale: 0.0 (No Threat) to 1.0 (Critical Threat)
- 0.0-0.2: Normal discourse
- 0.3-0.4: Heated rhetoric (monitor)
- 0.5-0.6: Concerning (review needed)
- 0.7-0.8: Clear threats
- 0.9-1.0: Imminent danger

## CRITICAL RULES:
✓ Protected Speech (DO NOT flag as threat):
  - Electoral metaphors: "destroy at polls", "crush their campaign"
  - Policy criticism: "this policy is killing businesses"
  - Satire and legitimate political debate

✗ Genuine Threats (FLAG):
  - Specific violence with target, time, location
  - Doxxing + violent intent
  - Coordinated attack planning
  - Incitement to immediate violence

**OUTPUT (JSON ONLY):**
{{
    "sentiment_analysis": {{
        "sentiment_score": <-1.0 to 1.0>,
        "sentiment_label": "Positive|Negative|Neutral",
        "confidence": "High|Medium|Low",
        "text_sentiment": <-1.0 to 1.0>,
        "emoji_sentiment": <-1.0 to 1.0>,
        "keyword_sentiment": <-1.0 to 1.0>,
        "sarcasm_detected": <true|false>,
        "emotional_intensity": "Low|Medium|High"
    }},

    "threat_assessment": {{
        "threat_score": <0.0 to 1.0>,
        "threat_level": "None|Low|Medium|High|Critical",
        "is_threat": <true|false>,
        "threat_type": "None|Violence|Hate Speech|Incitement|Doxxing|Election Interference|Disinformation",
        "specificity": "Vague|Moderate|Highly Specific",
        "imminence": "No Timeline|Future|Soon|Immediate",
        "protected_speech": <true|false>,
        "false_positive_likely": <true|false>
    }},

    "content_analysis": {{
        "language": "English|Tamil|Hindi|Tanglish|Mixed|Other",
        "key_narratives": ["topic1", "topic2", "topic3"],
        "political_context": "Electoral|Policy|Protest|General|Other",
        "target_identified": <true|false>,
        "target_type": "None|Individual|Group|Institution"
    }},

    "recommendation": {{
        "action": "None|Monitor|Human Review|Escalate|Emergency",
        "priority": "Low|Medium|High|Urgent|Critical",
        "reasoning": "Brief explanation of assessment"
    }}
}}

**IMPORTANT:**
- Distinguish harsh political criticism from genuine threats
- Consider Tamil/regional cultural context
- Electoral competition language is protected speech
- Provide ONLY valid JSON, no additional text"""

        return prompt
    
    async def process_post(self, post: PostCreate) -> PostUpdate:
        """
        Process a single post with LLM analysis
        
        Args:
            post: PostCreate model with raw post data
            
        Returns:
            PostUpdate model with LLM-generated fields
        """
        if not self.model:
            # Return default values if LLM not configured
            return PostUpdate(
                sentiment_score=0.0,
                sentiment_label=SentimentLabel.NEUTRAL,
                is_threat=False,
                key_narratives=[],
                language="Unknown"
            )
        
        try:
            # Check if content contains Tamil characters
            has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in post.post_text) if post.post_text else False
            
            # Try LLM analysis for all content, with fallback for language issues
            try:
                prompt = self.create_analysis_prompt(
                    post.post_text,
                    post.platform.value,
                    post.author_username
                )
                
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )
                
                # Parse JSON response
                analysis = self.parse_llm_response(response.text)
                print(f"LLM analysis successful (Tamil content: {has_tamil})")
                
            except Exception as llm_error:
                print(f"LLM generation error (Tamil content: {has_tamil}): {llm_error}")
                # Check if it's a language issue
                if ("language override unsupported" in str(llm_error) or 
                    "errmsg" in str(llm_error) or
                    has_tamil):
                    print("Using enhanced basic analysis for Tamil/unsupported content")
                    analysis = self.create_basic_analysis(post.post_text)
                else:
                    # For other errors, still fallback to basic analysis
                    print("LLM error, using basic analysis fallback")
                    analysis = self.create_basic_analysis(post.post_text)
            
            # Create update model with enhanced threat data
            update = PostUpdate(
                sentiment_score=analysis.get("sentiment_score", 0.0),
                sentiment_label=SentimentLabel(analysis.get("sentiment_label", "Neutral")),
                is_threat=analysis.get("is_threat", False),
                threat_level=analysis.get("threat_level", "None"),
                threat_score=analysis.get("threat_score", 0.0),
                key_narratives=analysis.get("key_narratives", [])[:5],  # Limit to 5
                language=analysis.get("language", "Unknown"),
                llm_analysis=analysis.get("full_analysis")  # Store complete analysis
            )

            return update
            
        except Exception as e:
            print(f"Error processing post with LLM: {e}")
            # Create basic analysis for failed posts
            basic_analysis = self.create_basic_analysis(post.post_text)
            return PostUpdate(
                sentiment_score=basic_analysis.get("sentiment_score", 0.0),
                sentiment_label=SentimentLabel(basic_analysis.get("sentiment_label", "Neutral")),
                is_threat=basic_analysis.get("is_threat", False),
                threat_level=basic_analysis.get("threat_level", "None"),
                threat_score=basic_analysis.get("threat_score", 0.0),
                key_narratives=basic_analysis.get("key_narratives", []),
                language=basic_analysis.get("language", "Unknown"),
                llm_analysis=None
            )
    
    def parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse comprehensive LLM response to extract analysis data

        Args:
            response_text: Raw text from LLM with comprehensive analysis

        Returns:
            Parsed analysis as simplified dictionary for backward compatibility
        """
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                full_analysis = json.loads(json_str)
            else:
                full_analysis = json.loads(response_text)

            # Extract and simplify for backward compatibility
            sentiment_data = full_analysis.get('sentiment_analysis', {})
            threat_data = full_analysis.get('threat_assessment', {})
            content_data = full_analysis.get('content_analysis', {})

            # Map to existing format
            return {
                "sentiment_score": sentiment_data.get('sentiment_score', 0.0),
                "sentiment_label": sentiment_data.get('sentiment_label', 'Neutral'),
                "is_threat": threat_data.get('is_threat', False),
                "threat_level": threat_data.get('threat_level', 'None'),
                "threat_score": threat_data.get('threat_score', 0.0),
                "key_narratives": content_data.get('key_narratives', []),
                "language": content_data.get('language', 'Unknown'),
                # Store full analysis for future use
                "full_analysis": full_analysis
            }

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON response: {e}")
            print(f"Response text: {response_text[:500]}...")
            return {}
    
    def create_basic_analysis(self, text: str) -> Dict[str, Any]:
        """
        Create basic analysis without LLM for unsupported languages
        
        Args:
            text: Post text to analyze
            
        Returns:
            Basic analysis dictionary
        """
        # Detect language
        has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in text)
        has_english = any('a' <= char.lower() <= 'z' for char in text)
        
        if has_tamil and has_english:
            language = "Tanglish"
        elif has_tamil:
            language = "Tamil"
        elif has_english:
            language = "English"
        else:
            language = "Unknown"
        
        # Log Tamil content detection
        if has_tamil:
            print(f"Tamil content detected in basic analysis: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Enhanced sentiment analysis
        positive_words = ["good", "great", "excellent", "wonderful", "amazing", "love", 
                         "நல்ல", "சிறப்பு", "அருமை", "பெருமை", "மகிழ்ச்சி", "வெற்றி"]
        negative_words = ["bad", "terrible", "awful", "hate", "angry", "sad", "corruption", "failure",
                         "மோசம்", "கோபம்", "வருத்தம்", "தோல்வி", "ஊழல்", "துர்நிதி"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment_score = 0.5
            sentiment_label = "Positive"
        elif negative_count > positive_count:
            sentiment_score = -0.5
            sentiment_label = "Negative"
        else:
            sentiment_score = 0.0
            sentiment_label = "Neutral"
        
        # Enhanced threat detection
        threat_words = ["kill", "attack", "destroy", "bomb", "violence", "death", "murder",
                       "கொல்", "தாக்கு", "அழி", "வன்முறை", "கொலை", "மரணம்"]
        is_threat = any(word.lower() in text_lower for word in threat_words)
        
        # Better keyword extraction
        words = text.split()
        # Filter for meaningful words (length > 3, not common stop words)
        stop_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
        key_narratives = [word for word in words[:10] if len(word) > 3 and word.lower() not in stop_words][:5]
        
        # Calculate threat score based on threat detection
        threat_score = 0.3 if is_threat else 0.0
        threat_level = "Low" if is_threat else "None"

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "is_threat": is_threat,
            "threat_level": threat_level,
            "threat_score": threat_score,
            "key_narratives": key_narratives,
            "language": language
        }
    
    async def process_batch(self, posts: List[PostCreate]) -> List[PostUpdate]:
        """
        Process multiple posts in batch
        
        Args:
            posts: List of PostCreate models
            
        Returns:
            List of PostUpdate models with LLM analysis
        """
        updates = []
        
        # Process posts concurrently with rate limiting
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent LLM calls
        
        async def process_with_limit(post):
            async with semaphore:
                return await self.process_post(post)
        
        tasks = [process_with_limit(post) for post in posts]
        updates = await asyncio.gather(*tasks)
        
        return updates
    
    async def process_raw_data(self, raw_data: RawDataInDB) -> Optional[PostCreate]:
        """
        Extract and process post from raw API data
        
        Args:
            raw_data: Raw data entry from database
            
        Returns:
            PostCreate model with extracted data, or None if extraction fails
        """
        try:
            platform = raw_data.platform
            raw_json = raw_data.raw_json
            
            # Platform-specific extraction
            if platform == "X":
                post = self.extract_x_post(raw_json, raw_data.cluster_id)
            elif platform == "Facebook":
                post = self.extract_facebook_post(raw_json, raw_data.cluster_id)
            elif platform == "YouTube":
                post = self.extract_youtube_post(raw_json, raw_data.cluster_id)
            elif platform == "Google News":
                post = self.extract_google_news_post(raw_json, raw_data.cluster_id)
            else:
                print(f"Unknown platform: {platform}")
                return None
            
            # Process with LLM
            if post:
                update = await self.process_post(post)
                # Apply LLM analysis to post
                post.sentiment_score = update.sentiment_score
                post.sentiment_label = update.sentiment_label
                post.is_threat = update.is_threat
                post.key_narratives = update.key_narratives
                post.language = update.language
            
            return post
            
        except Exception as e:
            print(f"Error processing raw data: {e}")
            return None
    
    def extract_x_post(self, raw_data: Dict[str, Any], cluster_id: str) -> Optional[PostCreate]:
        """Extract X/Twitter post from raw data"""
        try:
            from app.collectors.x_collector import XCollector
            collector = XCollector()
            return collector.parse_post(raw_data, cluster_id)
        except Exception as e:
            print(f"Error extracting X post: {e}")
            return None
    
    def extract_facebook_post(self, raw_data: Dict[str, Any], cluster_id: str) -> Optional[PostCreate]:
        """Extract Facebook post from raw data"""
        try:
            from app.collectors.facebook_collector import FacebookCollector
            collector = FacebookCollector()
            return collector.parse_post(raw_data, cluster_id)
        except Exception as e:
            print(f"Error extracting Facebook post: {e}")
            return None
    
    def extract_youtube_post(self, raw_data: Dict[str, Any], cluster_id: str) -> Optional[PostCreate]:
        """Extract YouTube video from raw data"""
        try:
            from app.collectors.youtube_collector import YouTubeCollector
            collector = YouTubeCollector()
            return collector.parse_post(raw_data, cluster_id)
        except Exception as e:
            print(f"Error extracting YouTube post: {e}")
            return None

    def extract_google_news_post(self, raw_data: Dict[str, Any], cluster_id: str) -> Optional[PostCreate]:
        """Extract Google News article from raw data"""
        try:
            from app.collectors.google_news_collector import GoogleNewsCollector
            collector = GoogleNewsCollector()
            return collector.parse_post(raw_data, cluster_id)
        except Exception as e:
            print(f"Error extracting Google News article: {e}")
            return None
    
    def create_threat_analysis_prompt(self, posts: List[Dict[str, Any]]) -> str:
        """
        Create prompt for threat pattern analysis across multiple posts
        
        Args:
            posts: List of post data for analysis
            
        Returns:
            Formatted prompt for threat analysis
        """
        posts_text = "\n\n".join([
            f"Post {i+1} ({p.get('platform', 'Unknown')}): {p.get('post_text', '')[:500]}"
            for i, p in enumerate(posts[:10])  # Limit to 10 posts
        ])
        
        prompt = f"""
Analyze the following collection of social media posts for threat patterns and coordinated campaigns:

{posts_text}

Identify:
1. Common narratives or themes
2. Coordinated messaging patterns
3. Potential misinformation campaigns
4. Threat indicators or escalation patterns
5. Key influencers or orchestrators

Provide analysis in JSON format:
{{
    "threat_level": "<low|medium|high|critical>",
    "coordinated_campaign": <true|false>,
    "main_narratives": ["<narrative1>", "<narrative2>", ...],
    "threat_indicators": ["<indicator1>", "<indicator2>", ...],
    "recommended_action": "<monitor|respond|escalate|ignore>",
    "confidence_score": <float between 0.0 and 1.0>
}}

Return ONLY valid JSON.
"""
        return prompt
    
    async def analyze_threat_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple posts for threat patterns

        Args:
            posts: List of post data

        Returns:
            Threat analysis results
        """
        if not self.model or not posts:
            return {
                "threat_level": "low",
                "coordinated_campaign": False,
                "main_narratives": [],
                "threat_indicators": [],
                "recommended_action": "monitor",
                "confidence_score": 0.0
            }

        try:
            prompt = self.create_threat_analysis_prompt(posts)
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            return self.parse_llm_response(response.text)

        except Exception as e:
            print(f"Error analyzing threat patterns: {e}")
            return {
                "threat_level": "low",
                "coordinated_campaign": False,
                "main_narratives": [],
                "threat_indicators": [],
                "recommended_action": "monitor",
                "confidence_score": 0.0
            }

    def create_multi_entity_analysis_prompt(
        self,
        post_text: str,
        platform: str,
        author: str,
        active_clusters: List[Dict[str, Any]]
    ) -> str:
        """
        Create multi-entity aspect-based sentiment analysis prompt

        Analyzes sentiment separately for each political entity/cluster mentioned in the post.
        Configured for Tamil Nadu political landscape: DMK (own) vs ADMK/BJP/TVK (competitors)

        Args:
            post_text: The text content to analyze
            platform: Source platform (X, Facebook, YouTube, Google News)
            author: Post author username
            active_clusters: List of cluster configs with {name, keywords, cluster_type}

        Returns:
            Comprehensive prompt for multi-entity sentiment analysis
        """
        # Clean text
        clean_text = post_text.replace('\n', ' ').strip()[:1200]

        # Build entity detection context
        entity_context = "\n".join([
            f"- **{cluster['name']}** ({cluster['cluster_type']} cluster): "
            f"Keywords: {', '.join(cluster['keywords'][:5])}"  # Limit keywords for prompt brevity
            for cluster in active_clusters
        ])

        prompt = f"""You are an Expert Multi-Entity Political Sentiment Analyzer for Tamil Nadu Politics.

**ENTITIES TO TRACK:**
{entity_context}

**POST TO ANALYZE:**
Platform: {platform}
Author: @{author}
Content: {clean_text}

**YOUR TASK:**
Perform aspect-based sentiment analysis - analyze sentiment SEPARATELY for EACH mentioned entity.

═══════════════════════════════════════════════════════════

## STEP 1: ENTITY DETECTION
Identify which entities are mentioned:
- Direct mentions (name, keywords from list)
- Indirect references (pronouns after entity mention: "they", "their", "them", "it")
- Comparative statements ("X vs Y", "X is better than Y")

**PRONOUN RESOLUTION RULE:**
If "their/they/them" appears after mentioning an entity → assign to that entity.
Example: "BJP policies failed. Their approach is wrong" → "Their" refers to BJP

═══════════════════════════════════════════════════════════

## STEP 2: PER-ENTITY SENTIMENT ANALYSIS

For EACH detected entity, calculate:

### A. TEXT SENTIMENT (50% weight):
- Extract text segments mentioning this entity
- Analyze sentiment in those SPECIFIC segments only
- Handle comparisons: "X is better than Y" → X gets positive, Y gets negative

### B. EMOJI SENTIMENT (30% weight):
**Assignment Rules:**
- Emoji near entity name (within 5 words) → assign to that entity
- Emoji at end with no clear target → apply to BOTH/ALL mentioned entities
- Example: "#DMK #BJP are both great! 🎉" → 🎉 applies to BOTH DMK and BJP

Common emoji sentiment:
- Positive: 😊😍🎉👍❤️🔥💪✨🙏🌟
- Negative: 😡😠👎💩😭😤🤬😒
- Neutral: 🤔😐

### C. HASHTAG SENTIMENT (20% weight):
- Hashtags containing entity name: #SupportDMK, #RejectBJP
- Support hashtags → positive
- Reject/oppose hashtags → negative

### D. SARCASM DETECTION:
**CRITICAL:** Detect sarcasm and FLIP sentiment
Indicators:
- "/s" marker
- "Great job" followed by criticism
- Excessive praise with clear negative context
- "Sure, X is doing great 🙄" (eye roll emoji)

Example: "Great job BJP! /s" → Negative sentiment (NOT positive)

═══════════════════════════════════════════════════════════

## STEP 3: COMPARATIVE ANALYSIS

If multiple entities mentioned:

**Direct Comparison:**
"X is better than Y" → X=Positive, Y=Negative
"Both X and Y are corrupt" → Both Negative
"Neither X nor Y" → Both Negative/Neutral

**Implicit Comparison:**
"While X succeeded, Y failed" → X=Positive, Y=Negative

═══════════════════════════════════════════════════════════

## STEP 4: THREAT ASSESSMENT (Per Entity)

For each entity, assess threats DIRECTED AT that entity:
- Violence/harm against entity or supporters
- Calls to attack/destroy entity
- Doxxing with violent intent
- Scale: 0.0 (no threat) to 1.0 (critical)

**PROTECTED SPEECH (NOT threats):**
- Electoral metaphors: "destroy at polls", "crush their campaign"
- Policy criticism: "their policies are killing businesses"

═══════════════════════════════════════════════════════════

## OUTPUT FORMAT (STRICT JSON):

{{
  "detected_entities": ["EntityName1", "EntityName2"],

  "entity_sentiments": {{
    "EntityName1": {{
      "label": "Positive|Negative|Neutral",
      "score": <-1.0 to 1.0>,
      "confidence": <0.0 to 1.0>,
      "mentioned_count": <integer>,
      "context_relevance": <0.0 to 1.0>,

      "text_sentiment": {{
        "score": <-1.0 to 1.0>,
        "segments": ["text segment 1", "text segment 2"]
      }},

      "emoji_sentiment": {{
        "score": <-1.0 to 1.0>,
        "emojis": ["😊", "👍"],
        "assignment_reason": "near entity name|end of post applies to all"
      }},

      "hashtag_sentiment": {{
        "score": <-1.0 to 1.0>,
        "hashtags": ["#hashtag1", "#hashtag2"]
      }},

      "sarcasm_detected": <true|false>,
      "sarcasm_reasoning": "explanation if sarcasm detected",

      "threat_level": <0.0 to 1.0>,
      "threat_reasoning": "explanation"
    }}
  }},

  "comparative_analysis": {{
    "has_comparison": <true|false>,
    "comparison_type": "Direct Contrast|Implicit|Neutral Coexistence|None",
    "entities_compared": ["Entity1", "Entity2"],
    "relationship": "description of relationship",
    "context_segments": ["relevant text"]
  }},

  "overall_analysis": {{
    "language": "English|Tamil|Tanglish|Mixed",
    "key_themes": ["theme1", "theme2"],
    "overall_threat_level": "None|Low|Medium|High|Critical",
    "overall_threat_score": <0.0 to 1.0>
  }}
}}

═══════════════════════════════════════════════════════════

**CRITICAL RULES:**
1. If entity NOT mentioned → OMIT from entity_sentiments (don't create with 0.0)
2. Emojis at end with no clear target → apply to ALL mentioned entities
3. Detect sarcasm and FLIP the sentiment score
4. "X is better than Y" → X positive, Y negative
5. Pronouns context: "BJP failed. Their policies..." → "Their" = BJP
6. Return ONLY valid JSON, no extra text

**EXAMPLE:**
Post: "DMK's healthcare is excellent 👍 but BJP's approach has failed 👎"

Output:
{{
  "detected_entities": ["DMK", "BJP"],
  "entity_sentiments": {{
    "DMK": {{
      "label": "Positive",
      "score": 0.75,
      "text_sentiment": {{"score": 0.8, "segments": ["DMK's healthcare is excellent"]}},
      "emoji_sentiment": {{"score": 0.7, "emojis": ["👍"], "assignment_reason": "near entity name"}},
      ...
    }},
    "BJP": {{
      "label": "Negative",
      "score": -0.65,
      "text_sentiment": {{"score": -0.7, "segments": ["BJP's approach has failed"]}},
      "emoji_sentiment": {{"score": -0.6, "emojis": ["👎"], "assignment_reason": "near entity name"}},
      ...
    }}
  }},
  "comparative_analysis": {{
    "has_comparison": true,
    "comparison_type": "Direct Contrast",
    "entities_compared": ["DMK", "BJP"],
    "relationship": "DMK praised while BJP criticized"
  }}
}}"""

        return prompt

    async def analyze_post_multi_entity(
        self,
        post_text: str,
        platform: str,
        author: str,
        active_clusters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform multi-entity aspect-based sentiment analysis

        Args:
            post_text: The text content to analyze
            platform: Source platform
            author: Post author
            active_clusters: List of active cluster configurations

        Returns:
            {
                "detected_entities": [...],
                "entity_sentiments": {...},
                "comparative_analysis": {...},
                "overall_analysis": {...}
            }
        """
        if not self.model:
            print("Warning: LLM model not configured, using basic analysis")
            return self._create_basic_entity_analysis(post_text, active_clusters)

        try:
            # Create prompt
            prompt = self.create_multi_entity_analysis_prompt(
                post_text, platform, author, active_clusters
            )

            # Call LLM
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            # Parse response
            result = self._parse_multi_entity_response(response.text)

            print(f"✅ Multi-entity analysis complete: {len(result.get('detected_entities', []))} entities detected")
            return result

        except Exception as e:
            print(f"❌ Error in multi-entity analysis: {e}")
            # Fallback to basic analysis
            return self._create_basic_entity_analysis(post_text, active_clusters)

    def _parse_multi_entity_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from multi-entity analysis"""
        try:
            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                result = json.loads(response_text)
                return result

        except json.JSONDecodeError as e:
            print(f"Failed to parse multi-entity JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {
                "detected_entities": [],
                "entity_sentiments": {},
                "comparative_analysis": {"has_comparison": False},
                "overall_analysis": {}
            }

    def _create_basic_entity_analysis(
        self,
        text: str,
        active_clusters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create basic entity analysis when LLM unavailable

        Detects entity mentions using keyword matching and basic sentiment
        """
        text_lower = text.lower()

        detected_entities = []
        entity_sentiments = {}

        # Simple keyword matching for entity detection
        for cluster in active_clusters:
            entity_name = cluster["name"]
            keywords = [kw.lower() for kw in cluster.get("keywords", [])]

            # Check if any keyword mentioned
            if any(kw in text_lower for kw in keywords):
                detected_entities.append(entity_name)

                # Basic sentiment
                positive_words = ["good", "great", "excellent", "👍", "😊", "❤️"]
                negative_words = ["bad", "failed", "terrible", "👎", "😡", "💩"]

                pos_count = sum(1 for w in positive_words if w in text_lower)
                neg_count = sum(1 for w in negative_words if w in text_lower)

                if pos_count > neg_count:
                    score, label = 0.5, "Positive"
                elif neg_count > pos_count:
                    score, label = -0.5, "Negative"
                else:
                    score, label = 0.0, "Neutral"

                entity_sentiments[entity_name] = {
                    "label": label,
                    "score": score,
                    "confidence": 0.5,
                    "mentioned_count": 1,
                    "context_relevance": 0.7,
                    "threat_level": 0.0,
                    "threat_reasoning": "Basic analysis - no threat detection"
                }

        return {
            "detected_entities": detected_entities,
            "entity_sentiments": entity_sentiments,
            "comparative_analysis": {
                "has_comparison": len(detected_entities) > 1
            },
            "overall_analysis": {
                "language": "Unknown",
                "key_themes": [],
                "overall_threat_level": "None",
                "overall_threat_score": 0.0
            }
        }