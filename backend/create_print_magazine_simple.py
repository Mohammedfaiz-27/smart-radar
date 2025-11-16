#!/usr/bin/env python3
"""
Script to create Print Magazine collection and insert sample data
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

def create_print_magazine_data():
    """Insert print magazine data into MongoDB"""
    print("🗞️ Creating Print Magazine collection and inserting data...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Simple print magazine data
    print_magazine_data = [
        {
            "platform": "Print Magazine",
            "content": {
                "text": "ADMK Alliance Leadership: The article portrays the ADMK leader (EPS) in a strong position regarding alliance negotiations. BJP and ADMK discussions continue about seat sharing and leadership roles."
            },
            "author": {"publication_name": "Vikadan"},
            "matched_clusters": [
                {"cluster_name": "ADMK", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "ADMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "The article portrays the ADMK leader (EPS) in a strong, assertive position, setting clear terms for the alliance."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "ADMK Alliance Leadership"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "EPS Alliance Leadership Article",
                "author": "Vikadan Team",
                "cluster": "ADMK",
                "date": "2025-09-20"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "DMK Alliance Seat Sharing: Congress leader demands more seats and a share in power from the DMK-led coalition, highlighting internal pressure within the alliance."
            },
            "author": {"publication_name": "Vikadan"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.5,
                        "reasoning": "The article highlights an alliance partner making strong demands, portraying potential instability in the DMK coalition."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "DMK Alliance Seat Sharing Conflict"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "Congress Demands More Seats from DMK",
                "author": "Vikadan Team", 
                "cluster": "DMK",
                "date": "2025-09-20"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "Internal Governance Conflict: DMK Mayor publicly criticizes administration officials for acting independently, creating internal controversy within party governance."
            },
            "author": {"publication_name": "Vikadan"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.6,
                        "reasoning": "Internal conflict where a DMK Mayor publicly criticizes the administration, negative for party unity."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "Internal Governance Conflict"
            },
            "published_at": datetime.fromisoformat("2025-09-03T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "DMK Mayor Criticizes Officials",
                "author": "Vikadan Team",
                "cluster": "DMK", 
                "date": "2025-09-03"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "Corruption Cases Inaction: Analysis of DMK government's inaction on promised corruption cases against former ADMK ministers, questioning their commitment to anti-corruption promises."
            },
            "author": {"publication_name": "Vikadan"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.9,
                        "reasoning": "Article accuses DMK government of failing to act on corruption promises, very damaging to credibility."
                    }
                },
                "threat_level": "High",
                "threat_campaign_topic": "Inaction on ADMK Corruption Cases"
            },
            "published_at": datetime.fromisoformat("2025-09-06T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "DMK Silent on Corruption Cases",
                "author": "Vikadan Team",
                "cluster": "DMK",
                "date": "2025-09-06"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "Job Scam Allegation: DMK party representative allegedly involved in job scam, taking money under false promises of government employment, serious corruption allegation."
            },
            "author": {"publication_name": "Vikadan"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.8,
                        "reasoning": "Article directly implicates DMK party representative in serious job scam, highly damaging to party reputation."
                    }
                },
                "threat_level": "High",
                "threat_campaign_topic": "Corruption Allegation - Job Scam"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "DMK Leader Job Scam Allegation",
                "author": "Vikadan Team",
                "cluster": "DMK",
                "date": "2025-09-20"
            }
        }
    ]
    
    # Insert data into print_magazines collection
    try:
        collection = db.print_magazines
        
        # Clear existing data
        collection.delete_many({})
        
        result = collection.insert_many(print_magazine_data)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} print magazine articles")
        
        # Show inserted data count
        total_count = collection.count_documents({})
        print(f"📊 Total print magazine articles in database: {total_count}")
        
        # Show sample by cluster
        dmk_count = collection.count_documents({"matched_clusters.cluster_name": "DMK"})
        admk_count = collection.count_documents({"matched_clusters.cluster_name": "ADMK"})
        print(f"  - DMK articles: {dmk_count}")
        print(f"  - ADMK articles: {admk_count}")
        
        print("✅ Print Magazine collection created successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    
    client.close()

if __name__ == "__main__":
    create_print_magazine_data()