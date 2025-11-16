#!/usr/bin/env python3
"""
Simple demo data creation script
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bson import ObjectId

async def create_demo_data():
    """Create demo data directly in MongoDB"""
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")
    db = client.smart_radar
    
    print("🚀 Creating demo data for SMART RADAR v19.0...")
    
    # Test connection
    try:
        await client.admin.command('ping')
        print("✅ MongoDB connection successful")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Create clusters
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
            "name": "TVK",
            "cluster_type": "competitor",
            "keywords": ["TVK", "தலைவர்", "Vijay", "விஜய்", "Thalapathy"],
            "description": "Tamilaga Vettri Kazhagam",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
    ]
    
    await db.clusters.delete_many({})
    cluster_result = await db.clusters.insert_many(clusters)
    print(f"✅ Created {len(cluster_result.inserted_ids)} clusters")
    
    # Get cluster IDs for reference
    cluster_map = {cluster["name"]: str(cluster["_id"]) for cluster in clusters}
    
    # Create social posts
    posts = [
        {
            "_id": ObjectId(),
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
                    "cluster_id": cluster_map["DMK"],
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
            "_id": ObjectId(),
            "platform": "X",
            "platform_post_id": "1234567891", 
            "content": "BJP's failed policies in Tamil Nadu exposed again! No development, only empty promises. Time for change! #TNRejectsBJP",
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
                    "cluster_id": cluster_map["BJP"],
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
        },
        {
            "_id": ObjectId(),
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
                    "cluster_id": cluster_map["TVK"],
                    "cluster_name": "TVK", 
                    "cluster_type": "competitor",
                    "keywords_matched": ["தலைவர்", "விஜய்", "TVK"]
                }
            ],
            "intelligence": {
                "relational_summary": "TVK promoting party leader Vijay as hope for Tamil people with 2026 election focus",
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
    ]
    
    await db.social_posts.delete_many({})
    posts_result = await db.social_posts.insert_many(posts)
    print(f"✅ Created {len(posts_result.inserted_ids)} social media posts")
    
    # Create news articles
    articles = [
        {
            "_id": ObjectId(),
            "platform": "web_news",
            "title": "Tamil Nadu CM Stalin Announces New Industrial Policy for 2024-25",
            "summary": "Chief Minister M.K. Stalin unveiled a comprehensive industrial policy aimed at attracting ₹1 lakh crore investment and creating 10 lakh jobs in Tamil Nadu.",
            "content": "Chennai: Tamil Nadu Chief Minister M.K. Stalin on Tuesday announced the state's new industrial policy for 2024-25...",
            "source": "The Hindu",
            "author": "Political Correspondent",
            "url": "https://thehindu.com/news/national/tamil-nadu/stalin-announces-industrial-policy/article123456.ece",
            "published_at": datetime.utcnow() - timedelta(hours=3),
            "readers_count": 25000,
            "category": "Politics",
            "tags": ["industrial policy", "Tamil Nadu", "investment"],
            "matched_clusters": [
                {
                    "cluster_id": cluster_map["DMK"],
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
        }
    ]
    
    await db.news_articles.delete_many({})
    articles_result = await db.news_articles.insert_many(articles)
    print(f"✅ Created {len(articles_result.inserted_ids)} news articles")
    
    print("✅ Demo data creation completed successfully!")
    print("\n📊 Created data:")
    print("   • 3 Political clusters (DMK, BJP, TVK)")
    print("   • 3 Social media posts (X, Facebook)")
    print("   • 1 News article (web_news)")
    print("   • All with v19.0 Entity-Centric Intelligence")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_demo_data())