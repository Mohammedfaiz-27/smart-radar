#!/usr/bin/env python3
"""
Verify demo data in MongoDB
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_data():
    """Verify the demo data was created successfully"""
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")
    db = client.smart_radar
    
    print("🔍 Verifying SMART RADAR v19.0 demo data...")
    
    try:
        # Check clusters
        clusters = await db.clusters.find({}, {"name": 1, "cluster_type": 1}).to_list(None)
        print(f"\n🎯 Clusters ({len(clusters)} total):")
        for cluster in clusters:
            print(f"   • {cluster['name']} ({cluster['cluster_type']})")
        
        # Check social posts
        posts_count = await db.social_posts.count_documents({})
        print(f"\n📱 Social Posts ({posts_count} total):")
        
        posts = await db.social_posts.find({}, {"platform": 1, "content": 1, "intelligence.entity_sentiments": 1}).to_list(None)
        for post in posts:
            content_preview = post['content'][:50] + "..." if len(post['content']) > 50 else post['content']
            sentiments = list(post.get('intelligence', {}).get('entity_sentiments', {}).keys())
            print(f"   • {post['platform']}: {content_preview}")
            print(f"     Entities: {', '.join(sentiments)}")
        
        # Check news articles
        articles_count = await db.news_articles.count_documents({})
        print(f"\n📰 News Articles ({articles_count} total):")
        
        articles = await db.news_articles.find({}, {"title": 1, "source": 1, "intelligence.entity_sentiments": 1}).to_list(None)
        for article in articles:
            sentiments = list(article.get('intelligence', {}).get('entity_sentiments', {}).keys())
            print(f"   • {article['source']}: {article['title']}")
            print(f"     Entities: {', '.join(sentiments)}")
        
        # Check v19.0 Intelligence Features
        print(f"\n🧠 v19.0 Intelligence Features:")
        
        # Entity sentiment analysis
        dmk_positive = await db.social_posts.count_documents({"intelligence.entity_sentiments.DMK.label": "Positive"})
        bjp_negative = await db.social_posts.count_documents({"intelligence.entity_sentiments.BJP.label": "Negative"})
        
        print(f"   • DMK Positive posts: {dmk_positive}")
        print(f"   • BJP Negative posts: {bjp_negative}")
        
        # Threat levels
        threat_counts = {}
        for level in ["low", "medium", "high", "critical"]:
            count = await db.social_posts.count_documents({"intelligence.threat_level": level})
            if count > 0:
                threat_counts[level] = count
        
        print(f"   • Threat levels: {threat_counts}")
        
        # Platform distribution
        platform_counts = {}
        for platform in ["X", "Facebook", "YouTube"]:
            count = await db.social_posts.count_documents({"platform": platform})
            if count > 0:
                platform_counts[platform] = count
        
        print(f"   • Platform distribution: {platform_counts}")
        
        print("\n✅ Data verification completed successfully!")
        print("\n🚀 Ready to start data collection with:")
        print("   • Multi-platform support (X, Facebook, YouTube)")
        print("   • Entity-centric sentiment analysis")
        print("   • v19.0 'The Umpire' intelligence system")
        print("   • Real-time threat detection")
        
    except Exception as e:
        print(f"❌ Error verifying data: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(verify_data())