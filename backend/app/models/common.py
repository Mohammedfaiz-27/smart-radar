"""
Common data models for Entity-Centric Sentiment Process v19.0
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class ClusterMatch(BaseModel):
    """Information about a cluster match"""
    cluster_id: str = Field(..., description="Cluster ID")
    cluster_name: str = Field(..., description="Cluster name")
    cluster_type: str = Field(..., pattern="^(own|competitor)$", description="Cluster type")
    keywords_matched: List[str] = Field(default_factory=list, description="Keywords that matched")

class EntitySentiment(BaseModel):
    """Sentiment analysis for a specific entity - v19.0"""
    label: str = Field(..., pattern="^(Positive|Negative|Neutral)$", description="Sentiment label")
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score")
    reasoning: str = Field(..., description="Detailed reasoning for this sentiment assignment")

class IntelligenceV19(BaseModel):
    """Intelligence structure for Entity-Centric Sentiment Process v19.0"""
    relational_summary: str = Field(..., description="Summary of the political interaction")
    entity_sentiments: Dict[str, EntitySentiment] = Field(..., description="Sentiment for each mentioned entity")
    threat_level: str = Field(default="low", pattern="^(low|medium|high|critical)$", description="Threat level based on own entity sentiment")
    threat_campaign_topic: Optional[str] = Field(None, description="Campaign topic if part of coordinated effort")