#!/usr/bin/env python3
"""
Script to create sample news articles for testing
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

def create_sample_news():
    """Insert sample news articles into MongoDB"""
    print("📰 Creating sample news articles...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Sample news articles
    news_articles = [
        {
            "platform": "web_news",
            "title": "DMK Government Announces New Infrastructure Projects",
            "summary": "Tamil Nadu Chief Minister Stalin announced several new infrastructure projects across the state including new medical colleges and highways.",
            "content": "The DMK government in Tamil Nadu has announced a comprehensive infrastructure development plan worth Rs 50,000 crores. The plan includes construction of new medical colleges, expansion of highway networks, and development of industrial corridors. Chief Minister MK Stalin said this will boost the state's economy and create employment opportunities.",
            "source": "The Hindu",
            "author": "Political Correspondent",
            "url": "https://thehindu.com/dmk-infrastructure-projects",
            "published_at": datetime.fromisoformat("2025-09-22T08:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.8,
                        "reasoning": "Article reports on positive government initiatives and development projects."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "Infrastructure Development"
            },
            "category": "Politics",
            "language": "en",
            "cluster_keywords": ["DMK", "Stalin", "Tamil Nadu"]
        },
        {
            "platform": "web_news", 
            "title": "AIADMK Leader Calls for Unity Within Party",
            "summary": "Former Chief Minister Edappadi Palaniswami urges party workers to maintain unity ahead of upcoming elections.",
            "content": "AIADMK General Secretary Edappadi Palaniswami addressed party workers in Salem, emphasizing the need for unity and disciplined approach towards the upcoming elections. He criticized the current DMK government's policies and promised better governance if voted to power.",
            "source": "Times of India",
            "author": "Chennai Bureau",
            "url": "https://timesofindia.com/aiadmk-unity-call",
            "published_at": datetime.fromisoformat("2025-09-22T06:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "matched_clusters": [
                {"cluster_name": "ADMK", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "ADMK": {
                        "label": "Positive", 
                        "score": 0.6,
                        "reasoning": "Article portrays AIADMK leader in a positive light calling for party unity."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "Party Unity"
            },
            "category": "Politics",
            "language": "en",
            "cluster_keywords": ["AIADMK", "Palaniswami", "Salem"]
        },
        {
            "platform": "web_news",
            "title": "Tamil Nadu Registers High Economic Growth",
            "summary": "State economy shows robust growth in industrial and service sectors, contributing to national GDP.",
            "content": "Tamil Nadu has registered one of the highest economic growth rates among Indian states, with significant contributions from automobile, textile, and information technology sectors. The state government's industrial policies have attracted major investments from both domestic and international companies.",
            "source": "Economic Times",
            "author": "Economics Desk",
            "url": "https://economictimes.com/tn-economic-growth",
            "published_at": datetime.fromisoformat("2025-09-21T14:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "Article credits government policies for economic growth and investment attraction."
                    }
                },
                "threat_level": "Low", 
                "threat_campaign_topic": "Economic Development"
            },
            "category": "Economy",
            "language": "en",
            "cluster_keywords": ["Tamil Nadu", "economic growth", "DMK government"]
        },
        {
            "platform": "web_news",
            "title": "Opposition Criticizes Government's Agricultural Policies",
            "summary": "AIADMK leaders raise concerns about farmer welfare schemes and agricultural subsidies.",
            "content": "AIADMK leaders have strongly criticized the DMK government's handling of agricultural issues, particularly the delay in procurement of paddy and insufficient fertilizer subsidies. They demanded immediate action to address farmer grievances and ensure timely payment of crop insurance.",
            "source": "Deccan Herald",
            "author": "Rural Reporter",
            "url": "https://deccanherald.com/agriculture-criticism",
            "published_at": datetime.fromisoformat("2025-09-21T16:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.6,
                        "reasoning": "Article reports criticism of government's agricultural policies by opposition."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "Agricultural Policy Criticism"
            },
            "category": "Agriculture",
            "language": "en", 
            "cluster_keywords": ["DMK", "agriculture", "criticism", "AIADMK"]
        },
        {
            "platform": "web_news",
            "title": "Chennai Metro Expansion Project Gets Approval",
            "summary": "Union government approves Chennai Metro Phase 2 expansion with increased funding allocation.",
            "content": "The Union Ministry of Housing and Urban Affairs has approved the Chennai Metro Rail Phase 2 expansion project with an enhanced budget allocation. The project will connect peripheral areas to the city center and is expected to reduce traffic congestion significantly.",
            "source": "Indian Express",
            "author": "Infrastructure Correspondent", 
            "url": "https://indianexpress.com/chennai-metro-expansion",
            "published_at": datetime.fromisoformat("2025-09-20T12:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.5,
                        "reasoning": "Article reports positive development for state infrastructure under current government."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "Infrastructure Development"
            },
            "category": "Infrastructure",
            "language": "en",
            "cluster_keywords": ["Chennai", "Metro", "Tamil Nadu", "infrastructure"]
        }
    ]
    
    # Insert data into news_articles collection (web_news platform)
    try:
        collection = db.news_articles
        
        # Clear existing data
        collection.delete_many({})
        
        result = collection.insert_many(news_articles)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} news articles")
        
        # Show inserted data count
        total_count = collection.count_documents({})
        print(f"📊 Total news articles in database: {total_count}")
        
        # Show sample by cluster
        dmk_count = collection.count_documents({"matched_clusters.cluster_name": "DMK"})
        admk_count = collection.count_documents({"matched_clusters.cluster_name": "ADMK"})
        print(f"  - DMK articles: {dmk_count}")
        print(f"  - ADMK articles: {admk_count}")
        
        print("✅ Sample news articles created successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    
    client.close()

if __name__ == "__main__":
    create_sample_news()