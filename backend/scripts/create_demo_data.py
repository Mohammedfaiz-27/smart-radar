#!/usr/bin/env python3
"""
Create demo data for testing the new v19.0 Entity-Centric Intelligence system
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from bson import ObjectId

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_database
from app.models.social_post import create_x_post, create_facebook_post, create_youtube_post
from app.models.news_article import create_web_news_article
from app.models.common import ClusterMatch, IntelligenceV19, EntitySentiment


async def create_demo_clusters():
    """Create sample clusters for political entities"""
    db = get_database()
    
    clusters = [
        {
            "_id": ObjectId(),
            "name": "DMK",
            "cluster_type": "own",
            "keywords": ["DMK", "திமுக", "Stalin", "ஸ்டாலின்", "Chief Minister", "முதல்வர்"],
            "description": "Dravida Munnetra Kazhagam - ruling party",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "name": "BJP",
            "cluster_type": "competitor",
            "keywords": ["BJP", "பாஜக", "Modi", "மோடி", "Annamalai", "அண்ணாமலை"],
            "description": "Bharatiya Janata Party",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "name": "ADMK",
            "cluster_type": "competitor", 
            "keywords": ["ADMK", "அதிமுக", "EPS", "OPS", "Palaniswami", "பழனிசாமி"],
            "description": "All India Anna Dravida Munnetra Kazhagam",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "name": "TVK",
            "cluster_type": "competitor",
            "keywords": ["TVK", "தலைவர்", "Vijay", "விஜய்", "Thalapathy"],
            "description": "Tamilaga Vettri Kazhagam",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
    ]
    
    # Insert clusters
    await db.clusters.delete_many({})  # Clear existing
    result = await db.clusters.insert_many(clusters)
    print(f"✅ Created {len(result.inserted_ids)} clusters")
    
    return {cluster["name"]: cluster["_id"] for cluster in clusters}


async def create_demo_social_posts(cluster_ids):
    """Create sample social media posts with v19.0 intelligence"""
    db = get_database()
    
    posts = []
    
    # X (Twitter) Posts
    posts.extend([
        {
            "platform": "X",
            "platform_post_id": "1234567890",
            "content": "மக்கள் விரும்பும் முதல்வர் ஸ்டாலின் அவர்களின் அடுத்த பெரிய அறிவிப்பு இன்று! 🔥 #DMK #TamilNadu",
            "author": "@DMKOfficial",
            "post_url": "https://x.com/DMKOfficial/status/1234567890",
            "posted_at": datetime.utcnow() - timedelta(hours=2),
            "engagement_metrics": {
                "likes": 1250,
                "retweets": 340,
                "replies": 89,
                "impressions": 15000
            },
            "hashtags": ["#DMK", "#TamilNadu"],
            "mentions": ["@CMOTamilNadu"],
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["DMK"]),
                    "cluster_name": "DMK",
                    "cluster_type": "own",
                    "keywords_matched": ["DMK", "முதல்வர்", "ஸ்டாலின்"]
                }
            ],
            "intelligence": {
                "relational_summary": "DMK promoting their Chief Minister's upcoming announcement with positive messaging",
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.8,
                        "reasoning": "Strong promotional content about party leader with enthusiastic tone"
                    }
                },
                "threat_level": "low",
                "threat_campaign_topic": None
            },
            "perspective_type": "multi",
            "has_been_responded_to": False,
            "collected_at": datetime.utcnow()
        },
        {
            "platform": "X", 
            "platform_post_id": "1234567891",
            "content": "BJP's failed policies in Tamil Nadu exposed again! No development, only empty promises. Time for change! #TNRejects BJP",
            "author": "@TamilNaduNews",
            "post_url": "https://x.com/TamilNaduNews/status/1234567891",
            "posted_at": datetime.utcnow() - timedelta(hours=4),
            "engagement_metrics": {
                "likes": 890,
                "retweets": 234,
                "replies": 67,
                "impressions": 8500
            },
            "hashtags": ["#TNRejectsBJP"],
            "mentions": [],
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["BJP"]),
                    "cluster_name": "BJP",
                    "cluster_type": "competitor",
                    "keywords_matched": ["BJP"]
                }
            ],
            "intelligence": {
                "relational_summary": "Critical post attacking BJP's performance in Tamil Nadu",
                "entity_sentiments": {
                    "BJP": {
                        "label": "Negative",
                        "score": -0.7,
                        "reasoning": "Direct criticism of party policies and performance with negative framing"
                    }
                },
                "threat_level": "low",
                "threat_campaign_topic": "Anti-BJP Campaign"
            },
            "perspective_type": "multi",
            "has_been_responded_to": False,
            "collected_at": datetime.utcnow()
        }
    ])
    
    # Facebook Posts
    posts.extend([
        {
            "platform": "Facebook",
            "platform_post_id": "fb_123456789",
            "content": "தலைவர் விஜய் அவர்களின் TVK கட்சி தமிழ் மக்களுக்கு புதிய நம்பிக்கை! 2026ல் மாற்றம் நிச்சயம்! 🔥",
            "author": "TVK Tamil Nadu",
            "post_url": "https://facebook.com/TVKTamilNadu/posts/123456789",
            "posted_at": datetime.utcnow() - timedelta(hours=6),
            "engagement_metrics": {
                "likes": 2100,
                "shares": 450,
                "comments": 178,
                "reactions": {"love": 890, "care": 234, "wow": 123}
            },
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["TVK"]),
                    "cluster_name": "TVK",
                    "cluster_type": "competitor",
                    "keywords_matched": ["தலைவர்", "விஜய்", "TVK"]
                }
            ],
            "intelligence": {
                "relational_summary": "TVK promoting party leader Vijay as a hope for Tamil people with 2026 election focus",
                "entity_sentiments": {
                    "TVK": {
                        "label": "Positive",
                        "score": 0.85,
                        "reasoning": "Strong promotional content positioning party as agent of change with emotional appeal"
                    }
                },
                "threat_level": "medium",
                "threat_campaign_topic": "2026 Election Campaign"
            },
            "perspective_type": "multi",
            "has_been_responded_to": False,
            "collected_at": datetime.utcnow()
        }
    ])
    
    # YouTube Posts
    posts.extend([
        {
            "platform": "YouTube",
            "platform_post_id": "yt_abcd1234",
            "content": "ADMK Leader EPS Press Meet: Criticizes DMK Government's Performance | Full Speech",
            "author": "News18 Tamil",
            "post_url": "https://youtube.com/watch?v=abcd1234",
            "posted_at": datetime.utcnow() - timedelta(hours=8),
            "engagement_metrics": {
                "views": 45000,
                "likes": 1200,
                "dislikes": 340,
                "comments": 89,
                "duration": "00:23:45"
            },
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["ADMK"]),
                    "cluster_name": "ADMK",
                    "cluster_type": "competitor",
                    "keywords_matched": ["ADMK", "EPS", "Palaniswami"]
                },
                {
                    "cluster_id": str(cluster_ids["DMK"]),
                    "cluster_name": "DMK", 
                    "cluster_type": "own",
                    "keywords_matched": ["DMK"]
                }
            ],
            "intelligence": {
                "relational_summary": "ADMK leader criticizing DMK government in press conference, showing inter-party conflict",
                "entity_sentiments": {
                    "ADMK": {
                        "label": "Positive",
                        "score": 0.6,
                        "reasoning": "ADMK leader taking strong stance and criticizing opponents, projecting strength"
                    },
                    "DMK": {
                        "label": "Negative", 
                        "score": -0.6,
                        "reasoning": "DMK government being criticized for poor performance by opposition leader"
                    }
                },
                "threat_level": "medium",
                "threat_campaign_topic": "Opposition Criticism Campaign"
            },
            "perspective_type": "multi",
            "has_been_responded_to": False,
            "collected_at": datetime.utcnow()
        }
    ])
    
    # Insert social posts
    await db.social_posts.delete_many({})  # Clear existing
    result = await db.social_posts.insert_many(posts)
    print(f"✅ Created {len(result.inserted_ids)} social media posts")


async def create_demo_news_articles(cluster_ids):
    """Create sample news articles with v19.0 intelligence"""
    db = get_database()
    
    articles = []
    
    articles.extend([
        {
            "platform": "web_news",
            "title": "Tamil Nadu CM Stalin Announces New Industrial Policy for 2024-25",
            "summary": "Chief Minister M.K. Stalin unveiled a comprehensive industrial policy aimed at attracting ₹1 lakh crore investment and creating 10 lakh jobs in Tamil Nadu.",
            "content": "Chennai: Tamil Nadu Chief Minister M.K. Stalin on Tuesday announced the state's new industrial policy for 2024-25, targeting significant economic growth and employment generation...",
            "source": "The Hindu",
            "author": "Political Correspondent",
            "url": "https://thehindu.com/news/national/tamil-nadu/stalin-announces-industrial-policy/article123456.ece",
            "published_at": datetime.utcnow() - timedelta(hours=3),
            "readers_count": 25000,
            "category": "Politics",
            "tags": ["industrial policy", "Tamil Nadu", "investment"],
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["DMK"]),
                    "cluster_name": "DMK",
                    "cluster_type": "own", 
                    "keywords_matched": ["Stalin", "முதல்வர்", "Chief Minister"]
                }
            ],
            "intelligence": {
                "relational_summary": "Positive coverage of DMK government's new industrial policy announcement by Chief Minister Stalin",
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "Favorable reporting of government policy announcement with focus on economic benefits"
                    }
                },
                "threat_level": "low",
                "threat_campaign_topic": None,
                "impact_level": "high",
                "confidence_score": 0.9
            },
            "perspective_type": "multi",
            "collected_at": datetime.utcnow()
        },
        {
            "platform": "web_news",
            "title": "BJP's Tamil Nadu Unit Faces Internal Conflicts Over Leadership",
            "summary": "Sources within the BJP's Tamil Nadu unit report growing tensions between different factions over the party's direction and leadership structure.",
            "source": "Indian Express",
            "author": "Tamil Nadu Bureau",
            "url": "https://indianexpress.com/article/cities/chennai/bjp-tamil-nadu-internal-conflicts/",
            "published_at": datetime.utcnow() - timedelta(hours=5),
            "readers_count": 18000,
            "category": "Politics",
            "tags": ["BJP", "internal conflict", "leadership"],
            "matched_clusters": [
                {
                    "cluster_id": str(cluster_ids["BJP"]),
                    "cluster_name": "BJP",
                    "cluster_type": "competitor",
                    "keywords_matched": ["BJP"]
                }
            ],
            "intelligence": {
                "relational_summary": "Negative coverage highlighting internal problems within BJP's Tamil Nadu organization",
                "entity_sentiments": {
                    "BJP": {
                        "label": "Negative",
                        "score": -0.6,
                        "reasoning": "Critical reporting of party's internal conflicts and leadership issues"
                    }
                },
                "threat_level": "low",
                "threat_campaign_topic": None,
                "impact_level": "medium",
                "confidence_score": 0.8
            },
            "perspective_type": "multi",
            "collected_at": datetime.utcnow()
        }
    ])
    
    # Insert news articles
    await db.news_articles.delete_many({})  # Clear existing
    result = await db.news_articles.insert_many(articles)
    print(f"✅ Created {len(result.inserted_ids)} news articles")


async def main():
    """Main function to create all demo data"""
    print("🚀 Creating demo data for SMART RADAR v19.0...")
    
    try:
        # Create clusters first
        cluster_ids = await create_demo_clusters()
        
        # Create social media posts
        await create_demo_social_posts(cluster_ids)
        
        # Create news articles
        await create_demo_news_articles(cluster_ids)
        
        print("✅ Demo data creation completed successfully!")
        print("\n📊 Created data:")
        print("   • 4 Political clusters (DMK, BJP, ADMK, TVK)")
        print("   • 4 Social media posts (X, Facebook, YouTube)")
        print("   • 2 News articles (web_news)")
        print("   • All with v19.0 Entity-Centric Intelligence")
        
        print("\n🎯 You can now:")
        print("   • View posts: http://localhost:8000/api/v1/posts")
        print("   • View news: http://localhost:8000/api/v1/news") 
        print("   • Dashboard stats: http://localhost:8000/api/v1/posts/dashboard-stats")
        print("   • API docs: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())