"""
Threat clustering service for grouping related threats into campaigns
"""
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from bson import ObjectId

# NLP and clustering imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.core.database import get_database
from app.models.threat_campaign import ThreatCampaignCreate, ThreatCampaignInDB, ThreatCampaignResponse
from app.models.social_post import SocialPostResponse


class ThreatClusteringService:
    def __init__(self):
        self._db = None
        self._posts_collection = None
        self._campaigns_collection = None
        
        # Clustering parameters
        self.similarity_threshold = 0.7  # Cosine similarity threshold
        self.min_posts_for_campaign = 2  # Minimum posts to form a campaign
        self.time_window_hours = 24  # Time window for campaign detection
        self.velocity_threshold = 3  # Posts per hour to mark as high velocity
        
    @property
    def database(self):
        if self._db is None:
            self._db = get_database()
        return self._db
    
    @property
    def posts_collection(self):
        if self._posts_collection is None:
            self._posts_collection = self.database.social_posts
        return self._posts_collection
    
    @property
    def campaigns_collection(self):
        if self._campaigns_collection is None:
            self._campaigns_collection = self.database.threat_campaigns
        return self._campaigns_collection

    async def detect_threat_campaigns(self) -> List[str]:
        """
        Main method to detect new threat campaigns from recent threat posts
        Returns list of newly created campaign IDs
        """
        try:
            # Get recent threat posts that are not already assigned to campaigns
            recent_threats = await self._get_unassigned_threat_posts()
            
            if len(recent_threats) < self.min_posts_for_campaign:
                return []
            
            # Group threats by similarity
            threat_groups = await self._cluster_threats_by_similarity(recent_threats)
            
            # Create campaigns for valid groups
            new_campaign_ids = []
            for group in threat_groups:
                if len(group) >= self.min_posts_for_campaign:
                    campaign_id = await self._create_campaign_from_group(group)
                    if campaign_id:
                        new_campaign_ids.append(campaign_id)
                        
            return new_campaign_ids
            
        except Exception as e:
            print(f"Error detecting threat campaigns: {e}")
            return []

    async def _get_unassigned_threat_posts(self) -> List[Dict[str, Any]]:
        """Get threat posts from the last 24 hours that aren't assigned to campaigns"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.time_window_hours)
        
        query = {
            "intelligence.is_threat": True,
            "threat_campaign_id": {"$in": [None, ""]},
            "collected_at": {"$gte": cutoff_time}
        }
        
        cursor = self.posts_collection.find(query).sort("collected_at", -1)
        posts = await cursor.to_list(length=1000)
        return posts

    async def _cluster_threats_by_similarity(self, threats: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group threats by content similarity using TF-IDF and cosine similarity"""
        if len(threats) < 2:
            return []
        
        # Prepare text content for vectorization
        texts = []
        for threat in threats:
            content = threat.get("content", "")
            # Clean and preprocess text
            cleaned_content = self._preprocess_text(content)
            texts.append(cleaned_content)
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),  # Use unigrams and bigrams
            lowercase=True
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
        except ValueError:
            # Handle case where all texts are too similar or empty
            return []
        
        # Group threats based on similarity
        groups = []
        used_indices = set()
        
        for i in range(len(threats)):
            if i in used_indices:
                continue
                
            # Find similar threats
            similar_indices = []
            for j in range(i, len(threats)):
                if j not in used_indices and similarity_matrix[i][j] >= self.similarity_threshold:
                    similar_indices.append(j)
                    used_indices.add(j)
            
            if len(similar_indices) >= self.min_posts_for_campaign:
                group = [threats[idx] for idx in similar_indices]
                groups.append(group)
        
        return groups

    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for better similarity detection"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions and hashtags for clustering (but keep the words)
        text = re.sub(r'[@#]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text.lower()

    async def _create_campaign_from_group(self, threat_group: List[Dict[str, Any]]) -> Optional[str]:
        """Create a new threat campaign from a group of similar threats"""
        try:
            # Analyze the group to extract campaign characteristics
            campaign_data = await self._analyze_threat_group(threat_group)
            
            # Create campaign
            campaign = ThreatCampaignCreate(**campaign_data)
            campaign_dict = campaign.dict()
            campaign_dict["created_at"] = datetime.utcnow()
            
            result = await self.campaigns_collection.insert_one(campaign_dict)
            campaign_id = str(result.inserted_id)
            
            # Update posts with campaign_id
            post_ids = [str(post["_id"]) for post in threat_group]
            await self.posts_collection.update_many(
                {"_id": {"$in": [ObjectId(pid) for pid in post_ids]}},
                {"$set": {"threat_campaign_id": campaign_id}}
            )
            
            return campaign_id
            
        except Exception as e:
            print(f"Error creating campaign from group: {e}")
            return None

    async def _analyze_threat_group(self, threat_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a group of threats to extract campaign characteristics"""
        # Extract common keywords and hashtags
        all_keywords = []
        all_hashtags = []
        all_accounts = []
        total_engagement = 0
        sentiment_scores = []
        
        for threat in threat_group:
            content = threat.get("content", "")
            
            # Extract hashtags
            hashtags = re.findall(r'#\w+', content)
            all_hashtags.extend([tag.lower() for tag in hashtags])
            
            # Extract keywords (simple approach - can be enhanced)
            words = re.findall(r'\b\w+\b', content.lower())
            all_keywords.extend([word for word in words if len(word) > 3])
            
            # Collect accounts
            author = threat.get("author", "")
            if author:
                all_accounts.append(author)
            
            # Collect engagement and sentiment
            engagement = threat.get("engagement_metrics", {})
            engagement_sum = sum(engagement.values()) if isinstance(engagement, dict) else 0
            total_engagement += engagement_sum
            
            intelligence = threat.get("intelligence", {})
            sentiment_score = intelligence.get("sentiment_score", 0)
            if sentiment_score:
                sentiment_scores.append(sentiment_score)
        
        # Find most common elements
        common_keywords = [word for word, count in Counter(all_keywords).most_common(10) if count > 1]
        common_hashtags = [tag for tag, count in Counter(all_hashtags).most_common(10)]
        unique_accounts = list(set(all_accounts))
        
        # Calculate campaign metrics
        post_count = len(threat_group)
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Calculate velocity (posts per hour)
        time_range = self._calculate_time_range(threat_group)
        velocity = post_count / max(time_range, 1)  # Avoid division by zero
        
        # Determine threat level
        threat_level = self._determine_threat_level(post_count, velocity, avg_sentiment, total_engagement)
        
        # Generate campaign name and description
        campaign_name = self._generate_campaign_name(common_hashtags, common_keywords)
        description = self._generate_campaign_description(threat_group, common_keywords, common_hashtags)
        
        # Determine cluster type (own vs competitor)
        cluster_types = [threat.get("cluster_type", "competitor") for threat in threat_group]
        cluster_type = Counter(cluster_types).most_common(1)[0][0]
        
        return {
            "name": campaign_name,
            "description": description,
            "cluster_type": cluster_type,
            "threat_level": threat_level,
            "status": "active",
            "keywords": common_keywords[:10],
            "hashtags": common_hashtags[:10],
            "participating_accounts": unique_accounts,
            "post_ids": [str(threat["_id"]) for threat in threat_group],
            "total_posts": post_count,
            "total_engagement": total_engagement,
            "average_sentiment": avg_sentiment,
            "campaign_velocity": velocity,
            "reach_estimate": self._estimate_reach(threat_group),
            "first_detected_at": datetime.utcnow(),
            "last_updated_at": datetime.utcnow()
        }

    def _calculate_time_range(self, threat_group: List[Dict[str, Any]]) -> float:
        """Calculate time range of threats in hours"""
        timestamps = []
        for threat in threat_group:
            posted_at = threat.get("posted_at")
            if posted_at:
                if isinstance(posted_at, str):
                    posted_at = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                timestamps.append(posted_at)
        
        if len(timestamps) < 2:
            return 1.0
        
        time_diff = max(timestamps) - min(timestamps)
        return max(time_diff.total_seconds() / 3600, 1.0)  # Convert to hours

    def _determine_threat_level(self, post_count: int, velocity: float, avg_sentiment: float, total_engagement: int) -> str:
        """Determine threat level based on campaign characteristics"""
        if velocity > 10 and avg_sentiment < -0.7 and total_engagement > 5000:
            return "critical"
        elif velocity > 5 and avg_sentiment < -0.5 and total_engagement > 2000:
            return "high"
        elif post_count > 5 and avg_sentiment < -0.3:
            return "medium"
        else:
            return "low"

    def _generate_campaign_name(self, hashtags: List[str], keywords: List[str]) -> str:
        """Generate a descriptive campaign name"""
        if hashtags:
            primary_tag = hashtags[0].replace('#', '').title()
            return f"{primary_tag} Campaign"
        elif keywords:
            primary_keyword = keywords[0].title()
            return f"{primary_keyword} Threat Campaign"
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
            return f"Threat Campaign {timestamp}"

    def _generate_campaign_description(self, threat_group: List[Dict[str, Any]], keywords: List[str], hashtags: List[str]) -> str:
        """Generate a campaign description"""
        post_count = len(threat_group)
        platform_counts = Counter([threat.get("platform", "unknown") for threat in threat_group])
        primary_platform = platform_counts.most_common(1)[0][0] if platform_counts else "social media"
        
        description = f"Coordinated threat campaign detected with {post_count} posts primarily on {primary_platform}."
        
        if hashtags:
            description += f" Key hashtags: {', '.join(hashtags[:3])}."
        
        if keywords:
            description += f" Common themes: {', '.join(keywords[:5])}."
        
        return description

    def _estimate_reach(self, threat_group: List[Dict[str, Any]]) -> int:
        """Estimate campaign reach based on engagement metrics"""
        total_reach = 0
        for threat in threat_group:
            engagement = threat.get("engagement_metrics", {})
            if isinstance(engagement, dict):
                # Simple reach estimation: sum of all engagement metrics
                total_reach += sum(engagement.values())
        
        return total_reach

    async def update_existing_campaigns(self) -> int:
        """Update existing campaigns with new matching threats"""
        updated_count = 0
        
        try:
            # Get active campaigns
            active_campaigns = await self.campaigns_collection.find({"status": "active"}).to_list(length=None)
            
            # Get recent unassigned threats
            recent_threats = await self._get_unassigned_threat_posts()
            
            for campaign in active_campaigns:
                # Find threats that match this campaign
                matching_threats = await self._find_matching_threats(campaign, recent_threats)
                
                if matching_threats:
                    # Update campaign with new threats
                    await self._add_threats_to_campaign(campaign, matching_threats)
                    updated_count += 1
            
            return updated_count
            
        except Exception as e:
            print(f"Error updating existing campaigns: {e}")
            return 0

    async def _find_matching_threats(self, campaign: Dict[str, Any], threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find threats that match an existing campaign"""
        matching_threats = []
        campaign_keywords = set(campaign.get("keywords", []))
        campaign_hashtags = set(campaign.get("hashtags", []))
        
        for threat in threats:
            content = threat.get("content", "").lower()
            
            # Check for keyword matches
            keyword_matches = sum(1 for keyword in campaign_keywords if keyword in content)
            
            # Check for hashtag matches
            threat_hashtags = set(re.findall(r'#\w+', content.lower()))
            hashtag_matches = len(campaign_hashtags.intersection(threat_hashtags))
            
            # Simple matching criteria
            if keyword_matches >= 2 or hashtag_matches >= 1:
                matching_threats.append(threat)
        
        return matching_threats

    async def _add_threats_to_campaign(self, campaign: Dict[str, Any], new_threats: List[Dict[str, Any]]):
        """Add new threats to an existing campaign"""
        campaign_id = str(campaign["_id"])
        new_post_ids = [str(threat["_id"]) for threat in new_threats]
        
        # Update posts with campaign_id
        await self.posts_collection.update_many(
            {"_id": {"$in": [ObjectId(pid) for pid in new_post_ids]}},
            {"$set": {"threat_campaign_id": campaign_id}}
        )
        
        # Update campaign statistics
        current_post_ids = campaign.get("post_ids", [])
        updated_post_ids = current_post_ids + new_post_ids
        
        # Recalculate metrics
        all_posts = await self.posts_collection.find({
            "_id": {"$in": [ObjectId(pid) for pid in updated_post_ids]}
        }).to_list(length=None)
        
        # Update campaign with new metrics
        updated_metrics = await self._calculate_updated_metrics(all_posts)
        
        await self.campaigns_collection.update_one(
            {"_id": campaign["_id"]},
            {
                "$set": {
                    "post_ids": updated_post_ids,
                    "total_posts": len(updated_post_ids),
                    "last_updated_at": datetime.utcnow(),
                    **updated_metrics
                }
            }
        )

    async def _calculate_updated_metrics(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate updated metrics for a campaign"""
        total_engagement = 0
        sentiment_scores = []
        
        for post in posts:
            engagement = post.get("engagement_metrics", {})
            if isinstance(engagement, dict):
                total_engagement += sum(engagement.values())
            
            intelligence = post.get("intelligence", {})
            sentiment_score = intelligence.get("sentiment_score", 0)
            if sentiment_score:
                sentiment_scores.append(sentiment_score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Calculate velocity
        time_range = self._calculate_time_range(posts)
        velocity = len(posts) / max(time_range, 1)
        
        return {
            "total_engagement": total_engagement,
            "average_sentiment": avg_sentiment,
            "campaign_velocity": velocity,
            "reach_estimate": total_engagement
        }

    async def get_campaign_stats(self) -> Dict[str, Any]:
        """Get overall campaign statistics"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get campaign counts
            total_campaigns = await self.campaigns_collection.count_documents({})
            active_campaigns = await self.campaigns_collection.count_documents({"status": "active"})
            critical_campaigns = await self.campaigns_collection.count_documents({"threat_level": "critical"})
            high_threat_campaigns = await self.campaigns_collection.count_documents({"threat_level": "high"})
            campaigns_today = await self.campaigns_collection.count_documents({"created_at": {"$gte": today}})
            
            # Calculate average velocity
            pipeline = [
                {"$group": {"_id": None, "avg_velocity": {"$avg": "$campaign_velocity"}}}
            ]
            velocity_result = await self.campaigns_collection.aggregate(pipeline).to_list(length=1)
            avg_velocity = velocity_result[0]["avg_velocity"] if velocity_result else 0
            
            return {
                "total_campaigns": total_campaigns,
                "active_campaigns": active_campaigns,
                "critical_campaigns": critical_campaigns,
                "high_threat_campaigns": high_threat_campaigns,
                "campaigns_today": campaigns_today,
                "average_velocity": round(avg_velocity, 2)
            }
            
        except Exception as e:
            print(f"Error getting campaign stats: {e}")
            return {
                "total_campaigns": 0,
                "active_campaigns": 0,
                "critical_campaigns": 0,
                "high_threat_campaigns": 0,
                "campaigns_today": 0,
                "average_velocity": 0.0
            }