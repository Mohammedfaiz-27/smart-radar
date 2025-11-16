"""
Unified Intelligence Service for SMART RADAR v25.0
Master Intelligence Prompt v24.0 - Enhanced Entity-Centric Scoring
"""
import json
import openai
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import get_database
from app.models.monitored_content import (
    MonitoredContent, 
    IntelligenceV24, 
    EntitySentiment,
    ContentType,
    Platform
)

class UnifiedIntelligenceService:
    """
    Unified Intelligence Service for all content types
    Implements Master Intelligence Prompt v24.0
    """
    
    def __init__(self):
        self._db = None
        self._collection = None
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            self._collection = self._db.monitored_content
        return self._collection
    
    async def analyze_content(
        self,
        content: str,
        content_type: ContentType,
        platform: Platform,
        matched_clusters: List[Dict[str, Any]],
        title: str = "",
        author: str = "",
        engagement_metrics: Dict[str, Any] = None,
        additional_context: Dict[str, Any] = None
    ) -> IntelligenceV24:
        """
        Master Intelligence Prompt v24.0 - Enhanced Entity-Centric Scoring
        Universal content analysis for all platforms and content types
        """
        try:
            # Build entities list for prompt
            entities_list = []
            for cluster in matched_clusters:
                entities_list.append(f"{cluster.get('cluster_name', '')} ({cluster.get('cluster_type', '')})")
            
            entities_text = "\n".join([f"- {e}" for e in entities_list]) if entities_list else "- No specific entities detected"
            
            # Build platform and content type context
            platform_context = self._get_platform_context(platform, content_type, engagement_metrics or {})
            
            # Build content context
            content_context = self._build_content_context(title, content, author, additional_context or {})
            
            # Master Intelligence Prompt v24.0
            prompt = f"""You are SMART RADAR's Master Intelligence Analyst v24.0, specializing in comprehensive content analysis across all digital platforms and content types. Your mandate is to provide entity-centric scoring with enhanced threat assessment and narrative alignment analysis.

### CONTENT ANALYSIS CONTEXT

**Platform:** {platform.value}
**Content Type:** {content_type.value}
**Analysis Target:** Tamil Nadu Political Intelligence

{platform_context}

### CORE INTELLIGENCE MANDATE v24.0

Your analysis must be completely objective and comprehensive, following this enhanced framework:

1. **Entity-Centric Sentiment Scoring**
   - Identify ALL political entities mentioned
   - Score sentiment FOR EACH entity (-1.0 to +1.0)
   - Assess confidence level (0.0 to 1.0)
   - Count entity mentions and relevance
   - Apply entity relationship dynamics

2. **Advanced Threat Assessment**
   - Evaluate threat level: low/medium/high/critical
   - Provide detailed threat reasoning
   - Assess misinformation risk (0.0 to 1.0)
   - Evaluate virality potential (0.0 to 1.0)

3. **Response Urgency Classification**
   - Classify as: low/medium/high/immediate
   - Based on threat level + sentiment + platform reach

4. **Narrative Alignment Analysis**
   - Identify alignment with known political narratives
   - Score narrative strength (0.0 to 1.0)
   - Detect coordinated messaging patterns

5. **Comprehensive Content Intelligence**
   - Extract key themes and topics
   - Assess geopolitical context
   - Evaluate strategic implications

### ENHANCED ANALYSIS RULES v24.0

**Entity Sentiment Scoring Rules:**
- Subject of praise/defense → Positive sentiment
- Object of criticism/attack → Negative sentiment  
- Entity A attacks Entity B → A=Positive (strength), B=Negative (targeted)
- Neutral mention without sentiment → Neutral
- Multiple mentions → Weighted average with relevance

**Threat Level Determination:**
- Critical: High negative sentiment + high engagement + misinformation risk
- High: Moderate negative sentiment + viral potential
- Medium: Low negative sentiment or neutral with high engagement
- Low: Positive sentiment or low engagement neutral content

**Platform-Specific Intelligence:**
- X: Real-time reactions, hashtag analysis, retweet patterns
- Facebook: Community engagement, sharing behavior, comment sentiment
- YouTube: Video content analysis, engagement duration, subscriber influence
- News Sites: Editorial credibility, journalist bias, publication reach

### TARGET ENTITIES FOR ANALYSIS
{entities_text}

### CONTENT TO ANALYZE
{content_context}

**REQUIRED JSON OUTPUT - INTELLIGENCE v24.0 FORMAT:**
{{
  "relational_summary": "Comprehensive summary of content with entity relationships and context",
  "entity_sentiments": {{
    "ENTITY_NAME": {{
      "label": "Positive|Negative|Neutral",
      "score": float_between_minus1_and_1,
      "confidence": float_between_0_and_1,
      "mentioned_count": integer_count_of_mentions,
      "context_relevance": float_between_0_and_1
    }}
  }},
  "threat_level": "low|medium|high|critical",
  "threat_reasoning": "Detailed explanation of threat assessment",
  "narrative_alignment": {{
    "narrative_name": confidence_score_0_to_1
  }},
  "response_urgency": "low|medium|high|immediate",
  "key_themes": ["theme1", "theme2", "theme3"],
  "geopolitical_context": "Relevant political/social context",
  "misinformation_risk": float_between_0_and_1,
  "virality_potential": float_between_0_and_1
}}"""

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are SMART RADAR's Master Intelligence Analyst v24.0. Return only valid JSON with comprehensive analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse and validate JSON response
            try:
                result = json.loads(result_text)
                
                # Build entity sentiments with enhanced structure
                entity_sentiments = {}
                for entity_name, sentiment_data in result.get("entity_sentiments", {}).items():
                    entity_sentiments[entity_name] = EntitySentiment(
                        label=sentiment_data.get("label", "Neutral"),
                        score=float(sentiment_data.get("score", 0.0)),
                        confidence=float(sentiment_data.get("confidence", 0.5)),
                        mentioned_count=int(sentiment_data.get("mentioned_count", 1)),
                        context_relevance=float(sentiment_data.get("context_relevance", 0.5))
                    )
                
                # Create IntelligenceV24 object
                intelligence = IntelligenceV24(
                    relational_summary=result.get("relational_summary", ""),
                    entity_sentiments=entity_sentiments,
                    threat_level=result.get("threat_level", "low"),
                    threat_reasoning=result.get("threat_reasoning", "Standard content analysis"),
                    narrative_alignment=result.get("narrative_alignment", {}),
                    response_urgency=result.get("response_urgency", "low"),
                    key_themes=result.get("key_themes", []),
                    geopolitical_context=result.get("geopolitical_context", ""),
                    misinformation_risk=float(result.get("misinformation_risk", 0.0)),
                    virality_potential=float(result.get("virality_potential", 0.0))
                )
                
                return intelligence
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Failed to parse Master Intelligence v24.0 response: {e}")
                return await self._fallback_intelligence_analysis(content, matched_clusters)
        
        except Exception as e:
            print(f"Master Intelligence v24.0 analysis failed: {e}")
            return await self._fallback_intelligence_analysis(content, matched_clusters)
    
    def _get_platform_context(self, platform: Platform, content_type: ContentType, engagement_metrics: Dict[str, Any]) -> str:
        """Generate platform-specific analysis context"""
        
        base_context = f"**Content Type:** {content_type.value}\n"
        
        if platform == Platform.X:
            context = base_context + f"""**Platform Intelligence:** X (Twitter) - Real-time political discourse
- Engagement Metrics: {engagement_metrics.get('likes', 0)} likes, {engagement_metrics.get('shares', 0)} retweets, {engagement_metrics.get('comments', 0)} replies
- Follower Influence: {engagement_metrics.get('follower_count', 0)} followers
- Viral Indicators: Rapid engagement growth, hashtag usage, mention patterns
- Analysis Focus: Real-time sentiment shifts, hashtag movements, retweet amplification"""
        
        elif platform == Platform.FACEBOOK:
            context = base_context + f"""**Platform Intelligence:** Facebook - Community engagement and sharing
- Engagement Metrics: {engagement_metrics.get('likes', 0)} reactions, {engagement_metrics.get('shares', 0)} shares, {engagement_metrics.get('comments', 0)} comments
- Community Reach: Page followers and organic reach patterns
- Sharing Behavior: Cross-community propagation and demographic targeting
- Analysis Focus: Community sentiment, sharing motivations, comment discussions"""
        
        elif platform == Platform.YOUTUBE:
            context = base_context + f"""**Platform Intelligence:** YouTube - Video content and sustained engagement
- Engagement Metrics: {engagement_metrics.get('views', 0)} views, {engagement_metrics.get('likes', 0)} likes, {engagement_metrics.get('comments', 0)} comments
- Content Duration: Extended engagement vs quick consumption
- Subscriber Influence: Channel authority and audience loyalty
- Analysis Focus: Content depth, sustained attention, comment sentiment analysis"""
        
        elif platform == Platform.NEWS_SITE:
            context = base_context + f"""**Platform Intelligence:** News Website - Editorial journalism and credibility
- Article Metrics: {engagement_metrics.get('word_count', 0)} words, {engagement_metrics.get('reading_time_minutes', 0)} min read
- Source Credibility: {engagement_metrics.get('source_credibility', 0.5)} credibility score
- Editorial Context: Journalist reputation and publication bias
- Analysis Focus: Editorial stance, fact-checking, journalistic integrity"""
        
        else:
            context = base_context + "**Platform Intelligence:** Generic digital content analysis"
        
        return context
    
    def _build_content_context(self, title: str, content: str, author: str, additional_context: Dict[str, Any]) -> str:
        """Build comprehensive content context for analysis"""
        
        context_parts = []
        
        if title:
            context_parts.append(f"**Title/Headline:** {title}")
        
        if author:
            context_parts.append(f"**Author/Creator:** {author}")
        
        context_parts.append(f"**Content:**\n{content}")
        
        if additional_context.get("hashtags"):
            context_parts.append(f"**Hashtags:** {', '.join(additional_context['hashtags'])}")
        
        if additional_context.get("mentions"):
            context_parts.append(f"**Mentions:** {', '.join(additional_context['mentions'])}")
        
        if additional_context.get("url"):
            context_parts.append(f"**Source URL:** {additional_context['url']}")
        
        return "\n\n".join(context_parts)
    
    async def _fallback_intelligence_analysis(self, content: str, matched_clusters: List[Dict[str, Any]]) -> IntelligenceV24:
        """Fallback analysis when AI processing fails"""
        
        # Simple entity sentiment analysis
        entity_sentiments = {}
        for cluster in matched_clusters:
            cluster_name = cluster.get('cluster_name', '')
            if cluster_name:
                # Basic sentiment analysis - check for positive/negative keywords
                content_lower = content.lower()
                cluster_lower = cluster_name.lower()
                
                if any(word in content_lower for word in ['good', 'great', 'excellent', 'support', 'praise']):
                    sentiment_score = 0.5
                    sentiment_label = "Positive"
                elif any(word in content_lower for word in ['bad', 'terrible', 'attack', 'criticize', 'oppose']):
                    sentiment_score = -0.5
                    sentiment_label = "Negative"
                else:
                    sentiment_score = 0.0
                    sentiment_label = "Neutral"
                
                entity_sentiments[cluster_name] = EntitySentiment(
                    label=sentiment_label,
                    score=sentiment_score,
                    confidence=0.3,  # Low confidence for fallback
                    mentioned_count=content_lower.count(cluster_lower),
                    context_relevance=0.5
                )
        
        return IntelligenceV24(
            relational_summary=f"Fallback analysis of content mentioning: {', '.join(entity_sentiments.keys())}",
            entity_sentiments=entity_sentiments,
            threat_level="low",
            threat_reasoning="Fallback analysis - limited intelligence processing",
            narrative_alignment={},
            response_urgency="low",
            key_themes=["fallback_analysis"],
            geopolitical_context="Limited context available",
            misinformation_risk=0.1,
            virality_potential=0.1
        )
    
    async def process_content_intelligence(self, content_id: str) -> bool:
        """Process intelligence for existing content in database"""
        try:
            # Fetch content from database
            content_doc = await self.collection.find_one({"_id": ObjectId(content_id)})
            if not content_doc:
                print(f"Content not found for ID: {content_id}")
                return False
            
            # Convert ObjectId to string for Pydantic model
            content_doc["_id"] = str(content_doc["_id"])
            content = MonitoredContent(**content_doc)
            
            # Generate intelligence analysis
            intelligence = await self.analyze_content(
                content=content.content,
                content_type=content.content_type,
                platform=content.platform,
                matched_clusters=content.matched_clusters,
                title=content.title,
                author=content.author,
                engagement_metrics=content.social_metrics.dict() if content.social_metrics else (content.news_metrics.dict() if content.news_metrics else {})
            )
            
            # Update content with intelligence
            await self.collection.update_one(
                {"_id": ObjectId(content_id)},
                {
                    "$set": {
                        "intelligence": intelligence.dict(),
                        "processing_status": "completed",
                        "last_updated": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to process intelligence for content {content_id}: {e}")
            await self.collection.update_one(
                {"_id": ObjectId(content_id)},
                {
                    "$set": {
                        "processing_status": "failed",
                        "processing_errors": [str(e)],
                        "last_updated": datetime.utcnow()
                    }
                }
            )
            return False
    
    async def batch_process_intelligence(self, limit: int = 10) -> Dict[str, int]:
        """Process intelligence for multiple pending contents"""
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        # Find pending content
        async for content_doc in self.collection.find(
            {"processing_status": "pending"}
        ).limit(limit):
            
            try:
                success = await self.process_content_intelligence(content_doc["_id"])
                if success:
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                print(f"Batch processing error for {content_doc.get('_id')}: {e}")
                stats["failed"] += 1
        
        return stats