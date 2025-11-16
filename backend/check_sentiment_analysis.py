#!/usr/bin/env python3
"""
Check sentiment analysis in the latest collected data
"""
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

async def check_sentiment_analysis():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client.smart_radar
    
    # Check latest monitored_content documents with intelligence
    recent_time = datetime.utcnow() - timedelta(minutes=10)
    
    print(f"🔍 Checking sentiment analysis in recent documents...")
    
    # Get recent documents with intelligence
    docs_with_intelligence = []
    async for doc in db.monitored_content.find(
        {
            "collected_at": {"$gte": recent_time},
            "intelligence": {"$exists": True}
        }
    ).sort("collected_at", -1).limit(3):
        docs_with_intelligence.append(doc)
    
    print(f"\n📊 Found {len(docs_with_intelligence)} documents with intelligence")
    
    for i, doc in enumerate(docs_with_intelligence, 1):
        print(f"\n{'='*60}")
        print(f"📄 DOCUMENT {i}")
        print(f"{'='*60}")
        
        # Basic info
        print(f"Title: {doc.get('title', 'N/A')}")
        print(f"Platform: {doc.get('platform', 'N/A')}")
        print(f"Content: {doc.get('content', 'N/A')[:100]}...")
        
        # Matched clusters and keywords
        matched_clusters = doc.get('matched_clusters', [])
        if matched_clusters:
            print(f"\n🎯 MATCHED CLUSTERS:")
            for cluster in matched_clusters:
                print(f"  - Cluster: {cluster.get('cluster_name', 'N/A')}")
                print(f"    Type: {cluster.get('cluster_type', 'N/A')}")
                print(f"    Match Score: {cluster.get('match_score', 'N/A')}")
                print(f"    Keywords Matched: {cluster.get('matched_keywords', [])}")
        
        # Intelligence analysis
        intelligence = doc.get('intelligence', {})
        if intelligence:
            print(f"\n🧠 INTELLIGENCE ANALYSIS:")
            print(f"  - Threat Level: {intelligence.get('threat_level', 'N/A')}")
            print(f"  - Summary: {intelligence.get('relational_summary', 'N/A')[:100]}...")
            
            # Entity sentiments - this is what we're looking for
            entity_sentiments = intelligence.get('entity_sentiments', {})
            if entity_sentiments:
                print(f"\n💭 ENTITY SENTIMENTS (Keyword-based):")
                for entity, sentiment_data in entity_sentiments.items():
                    if isinstance(sentiment_data, dict):
                        print(f"  - {entity}:")
                        print(f"    Label: {sentiment_data.get('label', 'N/A')}")
                        print(f"    Score: {sentiment_data.get('score', 'N/A')}")
                        print(f"    Confidence: {sentiment_data.get('confidence', 'N/A')}")
                        print(f"    Mentioned Count: {sentiment_data.get('mentioned_count', 'N/A')}")
                        print(f"    Reasoning: {sentiment_data.get('reasoning', 'N/A')[:80]}...")
            else:
                print(f"\n❌ No entity sentiments found")
        else:
            print(f"\n❌ No intelligence data found")
    
    if not docs_with_intelligence:
        print("❌ No documents with intelligence found in recent data")
    
    try:
        client.close()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(check_sentiment_analysis())