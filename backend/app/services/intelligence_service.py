"""
Intelligence service for sentiment analysis and threat detection
"""
import os
import json
from typing import Dict, Any, List
import google.generativeai as genai
from app.models.common import ClusterMatch, IntelligenceV19


class IntelligenceService:
    def __init__(self):
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Tamil positive keywords that should always be positive
        self.POSITIVE_KEYWORDS_TAMIL = [
            "மக்கள் விரும்பும்",  # desired by people
            "வெற்றி",  # victory
            "நம்மளுது",  # ours
            "முதல்வர் வேட்பாளர்",  # CM candidate
            "தளபதி",  # leader/commander (positive context)
            "வாழ்த்துக்கள்",  # congratulations
            "பெருமை",  # pride
            "சாதனை",  # achievement
            "முன்னேற்றம்",  # progress
            "வளர்ச்சி",  # development
            "நம்பிக்கை",  # trust/hope
            "ஆதரவு",  # support
            "பலம்",  # strength
            "வெற்றிகரமான",  # successful
            "சிறப்பான",  # excellent
        ]
        
        # English positive keywords
        self.POSITIVE_KEYWORDS_ENGLISH = [
            "victory", "support", "congratulations", "proud", "achievement", 
            "success", "excellent", "great", "amazing", "wonderful", 
            "fantastic", "outstanding", "brilliant", "impressive", 
            "inspiring", "hope", "trust", "strength", "progress", 
            "development", "growth", "positive", "best", "winner"
        ]
        
        # Negative keywords that should be negative (for clarity)
        self.NEGATIVE_KEYWORDS_TAMIL = [
            "தோல்வி",  # failure
            "கோபம்",  # anger
            "எதிர்ப்பு",  # opposition/protest
            "கண்டனம்",  # condemnation
            "தவறு",  # mistake/wrong
            "பிரச்சனை",  # problem
            "கெட்ட",  # bad
        ]
        
        self.NEGATIVE_KEYWORDS_ENGLISH = [
            "failure", "angry", "protest", "condemn", "wrong", "bad", 
            "terrible", "awful", "hate", "worst", "stupid", "fight", 
            "battle", "war", "attack", "against", "oppose"
        ]
    
    async def analyze_post(self, post_content: str, engagement: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyze a social media post for sentiment and threat level
        """
        try:
            # First, check for keyword-based sentiment override
            keyword_sentiment = self._check_keyword_sentiment(post_content)
            
            if keyword_sentiment:
                # Use keyword-based sentiment if found
                sentiment_data = keyword_sentiment
            else:
                # Get sentiment analysis from Gemini
                sentiment_data = await self._analyze_sentiment(post_content)
            
            # Determine threat level based on sentiment and engagement
            threat_data = self._assess_threat_level(sentiment_data, engagement)
            
            return {
                "sentiment_score": sentiment_data["score"],
                "sentiment_label": sentiment_data["label"],
                "is_threat": threat_data["is_threat"],
                "threat_level": threat_data["level"]
            }
            
        except Exception as e:
            # Fallback to neutral analysis if Gemini fails
            print(f"Intelligence analysis failed: {e}")
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "is_threat": False,
                "threat_level": "low"
            }
    
    def _check_keyword_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Check for keyword-based sentiment override before AI analysis
        """
        content_lower = content.lower()
        
        # Count positive keywords (Tamil and English)
        positive_count = 0
        for keyword in self.POSITIVE_KEYWORDS_TAMIL + self.POSITIVE_KEYWORDS_ENGLISH:
            if keyword.lower() in content_lower:
                positive_count += 1
        
        # Count negative keywords (Tamil and English)
        negative_count = 0
        for keyword in self.NEGATIVE_KEYWORDS_TAMIL + self.NEGATIVE_KEYWORDS_ENGLISH:
            if keyword.lower() in content_lower:
                negative_count += 1
        
        # Strong positive indicators - override to positive
        strong_positive_phrases = [
            "மக்கள் விரும்பும்",  # desired by people
            "முதல்வர் வேட்பாளர்",  # CM candidate
            "நம்மளுது",  # ours
            "வெற்றி",  # victory
        ]
        
        for phrase in strong_positive_phrases:
            if phrase in content:
                return {"score": 0.8, "label": "Positive"}
        
        # If significantly more positive than negative keywords
        if positive_count > 0 and positive_count > negative_count:
            return {"score": 0.6, "label": "Positive"}
        
        # If significantly more negative than positive keywords
        if negative_count > 0 and negative_count > positive_count:
            return {"score": -0.6, "label": "Negative"}
        
        # No clear keyword-based sentiment, let AI decide
        return None
    
    async def _analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Use Gemini to analyze sentiment of post content
        """
        try:
            prompt = f"""You are a political sentiment analysis expert specializing in Tamil and English social media posts. 
                        
                        Understand that:
                        - 'மக்கள் விரும்பும்' means 'desired by people' (POSITIVE endorsement)
                        - 'முதல்வர் வேட்பாளர்' means 'Chief Minister candidate' (POSITIVE promotional)
                        - 'நம்மளுது' means 'ours' (POSITIVE ownership/support)
                        - Fire emoji 🔥 often means excitement/enthusiasm (POSITIVE)
                        - Campaign endorsements and promotional posts are typically POSITIVE
                        - Victory claims and support messages are POSITIVE
                        - Only mark as NEGATIVE if there's clear criticism, opposition, attack, or conflict
                        - Political discourse can be passionate without being negative
                        
                        Examples:
                        "மக்கள் விரும்பும் முதல்வர் வேட்பாளர் 🔥" = POSITIVE (endorsement)
                        "2026 உம் நம்மளுது தான் 🔥" = POSITIVE (victory claim)
                        "No work from home, we are on the battle field!" = NEGATIVE (confrontational)
                        
                        Return ONLY a JSON object with 'score' (float between -1 and 1) and 'label' (Positive, Negative, or Neutral).

                        Analyze sentiment of this post: {content}"""
            
            response = self.model.generate_content(prompt)
            
            result_text = response.text.strip()
            
            # Try to parse JSON response
            import json
            try:
                result = json.loads(result_text)
                score = float(result.get("score", 0.0))
                label = result.get("label", "Neutral")
                
                # Ensure score is within bounds
                score = max(-1.0, min(1.0, score))
                
                # Ensure label is valid
                if label not in ["Positive", "Negative", "Neutral"]:
                    label = "Neutral"
                
                return {"score": score, "label": label}
                
            except (json.JSONDecodeError, KeyError, ValueError):
                # Fallback parsing
                if "negative" in result_text.lower():
                    return {"score": -0.6, "label": "Negative"}
                elif "positive" in result_text.lower():
                    return {"score": 0.6, "label": "Positive"}
                else:
                    return {"score": 0.0, "label": "Neutral"}
                    
        except Exception as e:
            print(f"Gemini sentiment analysis failed: {e}")
            # Simple keyword-based fallback
            content_lower = content.lower()
            negative_words = ["bad", "terrible", "awful", "hate", "worst", "fail", "wrong", "stupid", "angry"]
            positive_words = ["good", "great", "excellent", "love", "best", "amazing", "perfect", "happy"]
            
            negative_count = sum(1 for word in negative_words if word in content_lower)
            positive_count = sum(1 for word in positive_words if word in content_lower)
            
            if negative_count > positive_count:
                return {"score": -0.5, "label": "Negative"}
            elif positive_count > negative_count:
                return {"score": 0.5, "label": "Positive"}
            else:
                return {"score": 0.0, "label": "Neutral"}
    
    def _assess_threat_level(self, sentiment_data: Dict[str, Any], engagement: Dict[str, int]) -> Dict[str, Any]:
        """
        Assess threat level based on sentiment and engagement metrics
        """
        sentiment_score = sentiment_data["score"]
        sentiment_label = sentiment_data["label"]
        
        # Calculate engagement score
        likes = engagement.get("likes", 0)
        shares = engagement.get("shares", 0)
        comments = engagement.get("comments", 0)
        retweets = engagement.get("retweets", 0)
        
        total_engagement = likes + shares + comments + retweets
        
        # Threat assessment logic
        is_threat = False
        threat_level = "low"
        
        # High negative sentiment + high engagement = potential threat
        if sentiment_label == "Negative" and sentiment_score < -0.5:
            if total_engagement > 1000:
                is_threat = True
                threat_level = "critical"
            elif total_engagement > 500:
                is_threat = True
                threat_level = "high"
            elif total_engagement > 100:
                is_threat = True
                threat_level = "medium"
            elif sentiment_score < -0.8:
                is_threat = True
                threat_level = "medium"
        
        # Moderate negative sentiment with very high engagement
        elif sentiment_label == "Negative" and total_engagement > 2000:
            is_threat = True
            threat_level = "high"
        
        return {
            "is_threat": is_threat,
            "level": threat_level
        }
    
    async def analyze_news_content(self, content: str) -> Dict[str, Any]:
        """
        Analyze news article content for sentiment, impact, and threat assessment
        """
        try:
            prompt = f"""You are a news article intelligence analyst. Analyze news content for:
                        1. Sentiment (-1 to 1): Overall tone toward mentioned entities
                        2. Impact level (low/medium/high): Potential reach and influence
                        3. Threat indicators: Keywords suggesting controversy, conflict, or negative implications
                        4. Is threat (true/false): Whether this could impact reputation or require response
                        5. Confidence (0-1): How confident you are in this analysis
                        
                        Return ONLY a JSON object with these fields:
                        {{
                            "sentiment_score": float,
                            "impact_level": "low|medium|high", 
                            "threat_indicators": [list of concerning phrases],
                            "is_threat": boolean,
                            "confidence_score": float
                        }}

                        Analyze this news content: {content}"""
            
            response = self.model.generate_content(prompt)
            
            result_text = response.text.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(result_text)
                
                # Validate and format response
                intelligence = {
                    "sentiment_score": max(-1.0, min(1.0, float(result.get("sentiment_score", 0.0)))),
                    "impact_level": result.get("impact_level", "medium"),
                    "threat_indicators": result.get("threat_indicators", []),
                    "is_threat": bool(result.get("is_threat", False)),
                    "confidence_score": max(0.0, min(1.0, float(result.get("confidence_score", 0.8))))
                }
                
                # Ensure impact_level is valid
                if intelligence["impact_level"] not in ["low", "medium", "high"]:
                    intelligence["impact_level"] = "medium"
                
                return intelligence
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Failed to parse AI response: {e}")
                # Fallback to simple analysis
                return self._simple_news_analysis(content)
                
        except Exception as e:
            print(f"News intelligence analysis failed: {e}")
            return self._simple_news_analysis(content)
    
    def _simple_news_analysis(self, content: str) -> Dict[str, Any]:
        """
        Fallback simple news analysis when AI fails
        """
        content_lower = content.lower()
        
        # Keywords for threat detection
        threat_keywords = [
            "scandal", "controversy", "corruption", "investigation", "lawsuit",
            "protest", "opposition", "conflict", "crisis", "failure", "decline",
            "criticism", "condemn", "attack", "allegation", "violation"
        ]
        
        # Keywords for impact assessment  
        high_impact_keywords = [
            "government", "election", "policy", "minister", "parliament",
            "economy", "budget", "infrastructure", "major", "significant"
        ]
        
        # Count threat indicators
        threat_indicators = []
        for keyword in threat_keywords:
            if keyword in content_lower:
                threat_indicators.append(keyword)
        
        # Assess impact level
        impact_level = "low"
        for keyword in high_impact_keywords:
            if keyword in content_lower:
                impact_level = "high"
                break
        
        # Basic sentiment analysis
        positive_words = ["success", "achievement", "progress", "growth", "development", "improve"]
        negative_words = ["fail", "crisis", "problem", "decline", "concern", "issue"]
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if negative_count > positive_count:
            sentiment_score = -0.5
        elif positive_count > negative_count:
            sentiment_score = 0.5
        else:
            sentiment_score = 0.0
        
        return {
            "sentiment_score": sentiment_score,
            "impact_level": impact_level,
            "threat_indicators": threat_indicators,
            "is_threat": len(threat_indicators) > 0,
            "confidence_score": 0.6
        }
    
    async def detect_matched_clusters(self, content: str, all_clusters: List[Dict]) -> List[ClusterMatch]:
        """
        Scans content against ALL cluster keywords and returns list of matched clusters
        """
        matched_clusters = []
        content_lower = content.lower()
        
        for cluster in all_clusters:
            cluster_id = cluster.get("id", "")
            cluster_name = cluster.get("name", "")
            cluster_type = cluster.get("cluster_type", "")
            keywords = cluster.get("keywords", [])
            
            keywords_matched = []
            
            # Check each keyword against content
            for keyword_group in keywords:
                # Split keyword groups (e.g., "#DMK #திமுக #DravidianModel #திராவிடமாடல்")
                individual_keywords = keyword_group.split() if isinstance(keyword_group, str) else [keyword_group]
                
                for keyword in individual_keywords:
                    # Clean keyword (remove # and extra spaces)
                    clean_keyword = keyword.replace("#", "").strip().lower()
                    if clean_keyword and clean_keyword in content_lower:
                        keywords_matched.append(keyword)
                        break  # Only add one match per keyword group
            
            # If any keywords matched, add cluster to matched list
            if keywords_matched:
                matched_clusters.append(ClusterMatch(
                    cluster_id=cluster_id,
                    cluster_name=cluster_name,
                    cluster_type=cluster_type,
                    keywords_matched=keywords_matched
                ))
        
        return matched_clusters
    
    async def analyze_multi_perspective_content(
        self, 
        content: str,
        matched_clusters: List[ClusterMatch],
        platform: str = "X",
        engagement_metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Entity-Centric Sentiment Analysis v19.0 - The Umpire
        Neutral political analyst that scores interaction for each entity
        """
        try:
            # Build entities list for prompt
            entities_list = []
            for cluster in matched_clusters:
                entities_list.append(f"{cluster.cluster_name} ({cluster.cluster_type})")
            
            entities_text = "\n".join([f"- {e}" for e in entities_list])
            
            # Build platform-specific context
            platform_context = self._get_platform_context(platform, engagement_metrics or {})
            
            # Master Intelligence Prompt v19.0 - The Umpire (Enhanced for Multi-Platform)
            prompt = f"""You are a neutral, expert political analyst specializing in Tamil Nadu politics across multiple platforms. Your task is to perform a detailed, entity-centric sentiment analysis on content from {platform}. You must be completely objective.

### Platform Context: {platform}
{platform_context}

### Core Mandate: Score the Interaction for Each Player

Your goal is to determine the sentiment of the content *relative to each political entity mentioned*. A single piece of content can be positive for one entity and negative for another.

### Analysis Steps (You must follow this sequence)

1. **Entity Recognition:** Identify all political entities mentioned from the provided list.
2. **Platform-Aware Analysis:** Consider platform-specific features (engagement patterns, content format, audience behavior).
3. **Relational Analysis:** Determine the relationship between entities. Who is the actor? What is the action (praise, attack, report, react)? Who is the recipient?
4. **Entity-Centric Sentiment Scoring:** For EACH entity you identified, provide a separate sentiment analysis.
   * Rule: If an entity is the subject of a positive action (praise, defense), its score is Positive.
   * Rule: If an entity is the object of a negative action (attack, criticism), its score is Negative.
   * Rule: If Entity A attacks Entity B, the score for A is Positive (projecting strength) and the score for B is Negative (being attacked).

### Platform-Specific Considerations:
- **X (Twitter):** Real-time reactions, hashtag movements, viral potential
- **Facebook:** Community discussions, page posts, sharing patterns
- **YouTube:** Video content analysis, comment sentiment, view duration
- **WebNews:** Editorial stance, journalist bias, publication credibility

### Your Task:

Analyze the following content from {platform}. Return ONLY a structured JSON object with the specified keys.

**ENTITIES DETECTED:**
---
{entities_text}
---

**CONTENT TO ANALYZE:**
---
{content}
---

**REQUIRED JSON OUTPUT FORMAT:**
{{
  "relational_summary": "Brief summary of the interaction between entities",
  "entity_sentiments": {{
    "ENTITY_NAME": {{
      "label": "Positive|Negative|Neutral",
      "score": float_between_minus1_and_1,
      "reasoning": "Brief explanation of why this sentiment was assigned"
    }}
  }},
  "threat_campaign_topic": "Topic if this is part of a coordinated campaign, otherwise null"
}}"""

            full_prompt = f"You are a neutral political analyst. Return only valid JSON.\n\n{prompt}"
            
            response = self.model.generate_content(full_prompt)
            
            result_text = response.text.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                
                # Determine threat level based on "own" entity sentiments
                threat_level = "low"
                for cluster in matched_clusters:
                    if cluster.cluster_type == "own" and cluster.cluster_name in result.get("entity_sentiments", {}):
                        sentiment = result["entity_sentiments"][cluster.cluster_name]
                        if sentiment.get("score", 0) < -0.7:
                            threat_level = "critical"
                        elif sentiment.get("score", 0) < -0.4:
                            threat_level = "high"
                        elif sentiment.get("score", 0) < -0.1:
                            threat_level = "medium"
                
                # Return v19.0 format
                return {
                    "relational_summary": result.get("relational_summary", ""),
                    "entity_sentiments": result.get("entity_sentiments", {}),
                    "threat_level": threat_level,
                    "threat_campaign_topic": result.get("threat_campaign_topic")
                }
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Failed to parse multi-perspective AI response: {e}")
                return await self._fallback_multi_perspective_analysis(content, matched_clusters)
                
        except Exception as e:
            print(f"Multi-perspective analysis failed: {e}")
            return await self._fallback_multi_perspective_analysis(content, matched_clusters)
    
    async def _fallback_multi_perspective_analysis(self, content: str, matched_clusters: List[ClusterMatch]) -> Dict[str, Any]:
        """
        Fallback analysis when AI fails - v19.0 format
        """
        content_lower = content.lower()
        
        # Simple keyword-based sentiment for each cluster
        entity_sentiments = {}
        
        # Negative action words that affect the object/recipient
        negative_actions = ["challenge", "question", "slam", "criticize", "blame", "attack", "accuse", "condemn"]
        # Positive action words that benefit the subject
        positive_actions = ["praise", "support", "inaugurate", "launch", "achieve", "success"]
        
        threat_level = "low"
        
        for cluster in matched_clusters:
            # Check if cluster is mentioned with negative actions
            cluster_name_lower = cluster.cluster_name.lower()
            
            sentiment_score = 0.0
            reasoning = "Neutral mention in fallback analysis"
            
            # Check for negative associations
            for action in negative_actions:
                if action in content_lower and cluster_name_lower in content_lower:
                    sentiment_score = -0.6
                    reasoning = f"Entity mentioned in context of {action}"
                    break
            
            # Check for positive associations
            if sentiment_score == 0.0:
                for action in positive_actions:
                    if action in content_lower and cluster_name_lower in content_lower:
                        sentiment_score = 0.6
                        reasoning = f"Entity mentioned in context of {action}"
                        break
            
            label = "Positive" if sentiment_score > 0.1 else "Negative" if sentiment_score < -0.1 else "Neutral"
            
            entity_sentiments[cluster.cluster_name] = {
                "label": label,
                "score": sentiment_score,
                "reasoning": reasoning
            }
            
            # Update threat level based on own entity sentiment
            if cluster.cluster_type == "own" and sentiment_score < -0.5:
                threat_level = "high"
        
        return {
            "relational_summary": "Fallback analysis based on keyword detection",
            "entity_sentiments": entity_sentiments,
            "threat_level": threat_level,
            "threat_campaign_topic": None
        }
    
    def _get_platform_context(self, platform: str, engagement_metrics: Dict[str, Any]) -> str:
        """Generate platform-specific context for intelligence analysis"""
        
        if platform == "X":
            likes = engagement_metrics.get("likes", 0)
            retweets = engagement_metrics.get("retweets", 0)
            replies = engagement_metrics.get("replies", 0)
            
            viral_indicator = ""
            if retweets > 100:
                viral_indicator = " (HIGH VIRAL POTENTIAL)"
            elif retweets > 50:
                viral_indicator = " (MODERATE VIRAL POTENTIAL)"
                
            return f"""X (Twitter) post with {likes} likes, {retweets} retweets, {replies} replies{viral_indicator}.
Consider: Real-time political discourse, hashtag campaigns, rapid sentiment shifts, influencer amplification."""

        elif platform == "Facebook":
            likes = engagement_metrics.get("likes", 0)
            shares = engagement_metrics.get("shares", 0)
            comments = engagement_metrics.get("comments", 0)
            reactions = engagement_metrics.get("reactions", {})
            
            engagement_level = "low"
            if shares > 50:
                engagement_level = "high"
            elif shares > 20:
                engagement_level = "moderate"
                
            return f"""Facebook post with {likes} likes, {shares} shares, {comments} comments ({engagement_level} engagement).
Consider: Community-based discussions, page authority, demographic targeting, longer-form content analysis."""

        elif platform == "YouTube":
            views = engagement_metrics.get("views", 0)
            likes = engagement_metrics.get("likes", 0)
            comments = engagement_metrics.get("comments", 0)
            duration = engagement_metrics.get("duration", "unknown")
            
            reach_level = "limited"
            if views > 10000:
                reach_level = "high reach"
            elif views > 1000:
                reach_level = "moderate reach"
                
            return f"""YouTube video with {views} views, {likes} likes, {comments} comments, duration: {duration} ({reach_level}).
Consider: Video content analysis, comment sentiment, subscriber influence, long-form political messaging."""

        elif platform in ["web_news", "print_daily", "print_magazine"]:
            readers = engagement_metrics.get("readers_count", 0)
            publication_type = "Digital" if platform == "web_news" else "Print"
            
            return f"""{publication_type} news article with estimated {readers} readers.
Consider: Editorial stance, journalist credibility, publication bias, mainstream media influence, fact-checking standards."""
        
        else:
            return f"""Content from {platform} platform.
Consider: Platform-specific engagement patterns and audience behavior."""
    
    async def analyze_content_with_platform_context(
        self,
        content: str,
        platform: str,
        matched_clusters: List[ClusterMatch],
        engagement_metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Enhanced wrapper for multi-perspective analysis with platform context
        """
        return await self.analyze_multi_perspective_content(
            content=content,
            matched_clusters=matched_clusters,
            platform=platform,
            engagement_metrics=engagement_metrics
        )