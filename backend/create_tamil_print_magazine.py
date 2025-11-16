#!/usr/bin/env python3
"""
Script to create Print Magazine collection with proper Tamil data
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

def create_tamil_print_magazine_data():
    """Insert Tamil print magazine data into MongoDB"""
    print("🗞️ Creating Tamil Print Magazine collection and inserting data...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Tamil Print Magazine data with proper escaping
    print_magazine_data = [
        {
            "platform": "Print Magazine",
            "content": {
                "text": "எடப்பாடிதான் முதல்வர் வேட்பாளர்... விருப்பமிருந்தால் கூட்டணியில் இருக்கலாம்! எடப்பாடி பழனிசாமி - அமித் ஷா சந்திப்பு, எடப்பாடிக்கு எதிரான டி.டி.வி.தினகரனின் அரசியல், அ.தி.மு.க-வை ஒருங்கிணைக்க பா.ஜ.க முனைப்பு காட்டுவதாகச் சொல்லப்படும் விமர்சனம், உள்ளிட்டவைதான் தமிழக அரசியலின் ஹாட் டாபிக்."
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
                        "reasoning": "The article portrays the ADMK leader (EPS) in a strong, assertive position, setting clear terms for the alliance. This is a positive framing of his leadership."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "ADMK Alliance Leadership"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "எடப்பாடிதான் முதல்வர் வேட்பாளர்... விருப்பமிருந்தால் கூட்டணியில் இருக்கலாம்!",
                "author": "லெ. ராம்சங்கர், நா.ராஜமுருகன்",
                "cluster": "ADMK",
                "date": "2025-09-20"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "திமு.க கூட்டணியில் கடந்த முறை போன்று 25 சீட்டுகளை ஏற்றுக்கொள்ள மாட்டோம். கூடுதல் சீட் வேண்டும். ஆட்சி அதிகாரத்தில் பங்கு வேண்டும் என்பதைக் கூட்டணிப் பேச்சுவார்த்தையின்போதே முடிவுசெய்ய வேண்டும் எனச் சத்தமாகக் குரல் கொடுத்துவருகிறார், சட்டமன்ற காங்கிரஸ் தலைவர் ராஜேஷ்குமார்."
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
                        "reasoning": "The article highlights an alliance partner (Congress) making strong demands for more seats and a share in power, which portrays the DMK-led coalition as facing internal pressure and potential instability."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "DMK Alliance Seat Sharing Conflict"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "ஆட்சி அதிகார ஆசை எங்களுக்கும் இருக்கிறது..!",
                "author": "சிந்து ஆர், ஆல்டோ ஷேரன்",
                "cluster": "DMK",
                "date": "2025-09-20"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "திண்டுக்கல் மாநகராட்சியில், அதிகாரிகள் யாருடைய பேச்சையும் கேட்காமல், தனித்துச் செயல்படுவதாக மாமன்றக் கூட்டத்திலேயே மேயர் புகார் கூறியிருப்பது, சர்ச்சையை ஏற்படுத்தியிருக்கிறது!"
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
                        "reasoning": "The article highlights an internal conflict where a DMK Mayor is publicly criticizing the administration she is part of, which is negative for the party's image of unity and effective governance."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "Internal Governance Conflict"
            },
            "published_at": datetime.fromisoformat("2025-09-03T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "சரிவர பதிலளிப்பதில்லை... அலைக்கழிக்கிறார்... தன்னிச்சையாகச் செயல்படுகிறார்!",
                "author": "வினோத்குமார் மாயவன், ஈ.ஜெ.நந்தகுமார்",
                "cluster": "DMK",
                "date": "2025-09-03"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "கடந்த சட்டமன்றத் தேர்தலின்போது, பிரசாரத்துக்குச் சென்ற இடமெல்லாம், அ.தி.மு.க ஆட்சியில் ஊழல் தலைவிரித்தாடுகிறது. தி.மு.க ஆட்சி அமைந்ததும் ஊழல் செய்த அ.தி.மு.க அமைச்சர்களை விசாரிக்கத் தனி நீதிமன்றம் அமைப்போம் என்று சூளுரைத்தார் அப்போதைய எதிர்க்கட்சித் தலைவர் ஸ்டாலின். தி.மு.க ஆட்சிப் பொறுப்பேற்ற 75-வது நாளில், முன்னாள் போக்குவரத்துத்துறை அமைச்சரான எம்.ஆர்.விஜயபாஸ்கரின் வீட்டுக் கதவைத் தட்டியது லஞ்ச ஒழிப்புத்துறை. அடுத்தடுத்து வேலுமணி, தங்கமணி, ஆர்.காமராஜ், சி.விஜயபாஸ்கர், கே.சி.வீரமணி என ஒன்பது மாஜி அமைச்சர்களுமீது சொத்துக்குவிப்பு வழக்குகள் பதிவுசெய்யப்பட்டு பரபரப்பை எகிறவைத்தன. ஆனால், அதன் பிறகு ஒரு இன்சுகூட நகரவில்லை அந்த வழக்குகள்!"
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
                        "reasoning": "The article directly accuses the DMK government of 'silent collusion' and failing to act on its promise to prosecute corruption cases against opponents, which is a very strong attack on its credibility."
                    }
                },
                "threat_level": "High",
                "threat_campaign_topic": "Inaction on ADMK Corruption Cases"
            },
            "published_at": datetime.fromisoformat("2025-09-06T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "மாஜிக்கள் மீதான ஊழல் வழக்குகள்! - கள்ள மௌனத்தில் தி.மு.க அரசு!",
                "author": "மனோஜ் முத்தரசு, ரமேஷ் கந்தசாமி",
                "cluster": "DMK",
                "date": "2025-09-06"
            }
        },
        {
            "platform": "Print Magazine",
            "content": {
                "text": "அரசு வேலை வாங்கித்தருவதாக, ஆளுங்கட்சிப் பிரமுகர் ஒருவர், கட்டபொம்மன் வாரிசு என்று கூறி, 4 லட்சம் ரூபாய் வாங்கிக்கொண்டு ஏமாற்றிவிட்டதாகப் புகார் கொடுத்துப் பரபரப்பைக் கிளப்பியிருக்கிறார் தனியார் பேருந்து மெக்கானிக் ஒருவர்."
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
                        "reasoning": "The article directly implicates a DMK party representative ('ஆளுங்கட்சிப் பிரமுகர்') in a serious job scam. This type of corruption allegation is highly damaging to the party's reputation."
                    }
                },
                "threat_level": "High",
                "threat_campaign_topic": "Corruption Allegation - Job Scam"
            },
            "published_at": datetime.fromisoformat("2025-09-20T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "மாநகராட்சி டிரைவர் வேலைக்கு 4 லட்சம்..! - ஏமாற்றியது கட்டபொம்மன் வாரிசா?",
                "author": "எஸ்.மகேஷ்",
                "cluster": "DMK",
                "date": "2025-09-20"
            }
        }
    ]
    
    # Insert data into print_magazines collection
    try:
        collection = db.print_magazines
        result = collection.insert_many(print_magazine_data)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} Tamil print magazine articles")
        
        # Show inserted data count
        total_count = collection.count_documents({})
        print(f"📊 Total print magazine articles in database: {total_count}")
        
        # Show sample by cluster
        dmk_count = collection.count_documents({"matched_clusters.cluster_name": "DMK"})
        admk_count = collection.count_documents({"matched_clusters.cluster_name": "ADMK"})
        print(f"  - DMK articles: {dmk_count}")
        print(f"  - ADMK articles: {admk_count}")
        
        print("✅ Tamil Print Magazine collection created successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    
    client.close()

if __name__ == "__main__":
    create_tamil_print_magazine_data()