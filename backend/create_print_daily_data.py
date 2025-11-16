#!/usr/bin/env python3
"""
Script to create Print_Daily collection and insert data
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

def create_print_daily_data():
    """Insert print daily data into MongoDB"""
    print("📰 Creating Print_Daily collection and inserting data...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Print Daily data - Times of India
    times_of_india_data = [
        {
            "platform": "Print Daily",
            "publisher": "Times of India",
            "content": {
                "text": "On the eve of the month-long festival season, which begins with the first day of Navratri, PM Narendra Modi on Sunday asked for people to take advantage of the \"Bachat Utsav\" (savings festival) starting Monday, when the next generation GST reforms roll out, helping reduce prices, lower compliance and accelerate India's growth story. In a special address to the nation ahead of the rollout of the GST reforms, the PM also made a strong pitch for promoting 'swadeshi' goods and urged people to liberate themselves from \"the dependence on foreign goods\" and buy products that are 'Made in India'. \"Tomorrow, on the first day of Navratri, at dawn, the next generation of GST reforms will be implemented. From tomorrow, the 'savings festival' begins. Your savings will increase, you will be able to purchase your preferred items more easily. With lower GST, it will be easier for citizens to fulfil their dreams,\" the PM said."
            },
            "author": {"publication_name": "Times of India", "author_name": "TIMES NEWS NETWORK"},
            "matched_clusters": [
                {"cluster_name": "BJP", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "BJP": {
                        "label": "Positive",
                        "score": 0.8,
                        "reasoning": "The article positively portrays PM Modi's GST reforms as beneficial for people and economic growth."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "GST Reforms Announcement"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "PM: 'Savings festival' starts today as GST reforms will lower prices, boost growth",
                "author": "TIMES NEWS NETWORK",
                "cluster": "BJP",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Times of India",
            "content": {
                "text": "Tamil Nadu has the full potential to emerge as a global hub for the tyre market, says V K Misra, technical director, JK Tyre and Industries. The state's conducive industrial climate, robust infrastructure, and proactive government policies make it a preferred destination for investors. In an interview to TOI, he says the state's potential is yet to be fully exploited. We have one of our biggest and most efficient manufacturing facilities in Sriperumbudur. We started production in a record time of 15 months, and now we are producing more than 60 lakh tyres per annum. Our plant is located in an industrial area, where all facilities are available. We are happy with the state government's support."
            },
            "author": {"publication_name": "Times of India", "author_name": "Yogesh Kabirdoss"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "The article highlights Tamil Nadu's positive industrial climate and government support under DMK administration."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "Industrial Development in Tamil Nadu"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "'TN has ability to serve global tyre market'",
                "author": "Yogesh Kabirdoss",
                "cluster": "DMK",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Times of India",
            "content": {
                "text": "The 17th century Indo-Saracenic building on the Chepauk Palace complex, which houses several government offices including that of the directorate of industries and commerce, has been restored to its original glory by the public works department. The lime and mortar structure, which had suffered extensive damage over the years, has been restored with traditional materials. The restoration work, which began in 2021, was carried out at a cost of ₹18 crore. The building, which was in a dilapidated condition, has been strengthened and restored to its original grandeur."
            },
            "author": {"publication_name": "Times of India", "author_name": "T K Rohit"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.6,
                        "reasoning": "The article shows successful government restoration work completed under DMK administration."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "Heritage Conservation"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "Kalas Mahal structure restored to past glory",
                "author": "T K Rohit",
                "cluster": "DMK",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Times of India",
            "content": {
                "text": "Many residents of a luxury apartment complex in Velachery are seeing red over their electricity bills after a TANGEDCO assessor failed to record the meter readings correctly. The residents of the 240-flat complex, where each flat has a three-phase connection, were shocked to see their bi-monthly bills running into lakhs of rupees. The residents alleged that the assessor had recorded the readings of only one phase and multiplied it by three, resulting in exorbitant bills. We were shocked to see the bills. We have never paid such high amounts. We have been running from pillar to post to get the bills corrected, but to no avail."
            },
            "author": {"publication_name": "Times of India", "author_name": "Vandhana.K"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Negative",
                        "score": -0.7,
                        "reasoning": "The article highlights service failures in TANGEDCO under DMK government causing public distress."
                    }
                },
                "threat_level": "Medium",
                "threat_campaign_topic": "TANGEDCO Service Issues"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "Assessor's negligence leaves lux flats with sky-high power bills",
                "author": "Vandhana.K",
                "cluster": "DMK",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Times of India",
            "content": {
                "text": "In politics, especially in Tamil Nadu, one man's rebellion is another's revolution. For some, it is Edappadi K Palaniswami's (EPS) arrogance, for others, it is his assertion. But for the AIADMK cadre, it is a much-needed shot in the arm. The former chief minister's tough stand against allies, including the BJP, has enthused the party cadre, who were demoralised after the 2021 assembly poll defeat. EPS has made it clear that he will not have any truck with the BJP if it continues to hobnob with his detractors, T T V Dhinakaran and O Panneerselvam (OPS)."
            },
            "author": {"publication_name": "Times of India", "author_name": "Arun Ram"},
            "matched_clusters": [
                {"cluster_name": "ADMK", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "ADMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "The article portrays EPS as a strong leader who has revitalized AIADMK cadre and asserted independence from BJP."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "AIADMK Leadership Assertion"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "Why this EPS is good for AIADMK, bad for NDA",
                "author": "Arun Ram",
                "cluster": "ADMK",
                "date": "2025-09-22"
            }
        }
    ]
    
    # Hindu Tamil data
    hindu_tamil_data = [
        {
            "platform": "Print Daily",
            "publisher": "Hindu Tamil",
            "content": {
                "text": "நாடு முழுவதும் ஜிஎஸ்டி வரி குறைப்பு இன்று அமலுக்கு வருகிறது. இதன்மூலம் நாட்டின் பொருளாதாரம் அபரிமிதமாக வளர்ச்சி அடையும் என்று பிரதமர் மோடி தெரிவித்துள்ளார். ஜிஎஸ்டி 2.0 வரி விகிதம் இன்று அமலுக்கு வருகிறது. இதையொட்டி, பிரதமர் மோடி நேற்று மாலை 5 மணிக்கு நாட்டு மக்களிடையே உரையாற்றினார். நவராத்திரி பண்டிகை தொடங்கும் இந்த நன்னாளில் (இன்று) சுயசார்பு இந்தியா இயக்கத்தின் மிக முக்கிய மாற்றம் தொடங்க உள்ளது."
            },
            "author": {"publication_name": "Hindu Tamil", "author_name": "Staff Reporter"},
            "matched_clusters": [
                {"cluster_name": "BJP", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "BJP": {
                        "label": "Positive",
                        "score": 0.8,
                        "reasoning": "Tamil article positively covers PM Modi's GST reforms and their economic benefits."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "GST வரி குறைப்பு"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "ஜிஎஸ்டி வரி குறைப்பால் வளர்ச்சி அதிகரிக்கும்",
                "author": None,
                "cluster": "BJP",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Hindu Tamil",
            "content": {
                "text": "நாகர்கோவிலில் நடந்த அரசு விழாவில் கூட்டுறவுத் துறை அமைச்சர் ஐ.பெரியசாமி பேசியதாவது: குஜராத் மாநிலத்தில் அரசுப் பணியாளர்கள் மிகச் சிறப்பாக பணியாற்றுகின்றனர். அண்மையில் குஜராத் சென்றிருந்தபோது அரசு அலுவலகங்களின் செயல்பாடுகளை பார்த்தேன். அங்கு ஒரு கோப்பு கூட தேங்கிக் கிடப்பதைப் பார்க்க முடியவில்லை. அதுபோல, தமிழகத்திலும் அரசுப் பணியாளர்கள் பணியாற்ற வேண்டும்."
            },
            "author": {"publication_name": "Hindu Tamil", "author_name": "Staff Reporter"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Neutral",
                        "score": 0.1,
                        "reasoning": "Minister's statement about improving government efficiency, neutral administrative discussion."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "அரசு நிர்வாக முன்னேற்றம்"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "சிறந்த நிர்வாகத்துக்கு குஜராத் பணியாளர்கள் முன்மாதிரி",
                "author": None,
                "cluster": "DMK",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Hindu Tamil",
            "content": {
                "text": "சென்னை அண்ணா அறிவாலயத்தில் திமுக மகளிர் அணி சார்பில் நடைபெற்ற நிகழ்ச்சியில் திமுக எம்.பி. கனிமொழி கருணாநிதி பேசியதாவது: இந்தித் திணிப்புக்கு எதிராக திமுக தொடர்ந்து போராடி வருகிறது. மும்மொழிக் கொள்கையை மத்திய அரசு திணிக்கப் பார்க்கிறது. ஆனால், அதுகுறித்து தெளிவான பார்வை மத்திய அரசிடம் இல்லை. தமிழகத்தில் இருமொழிக் கொள்கைதான் எப்போதும் நடைமுறையில் இருக்கும்."
            },
            "author": {"publication_name": "Hindu Tamil", "author_name": "Staff Reporter"},
            "matched_clusters": [
                {"cluster_name": "DMK", "cluster_type": "own"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "DMK": {
                        "label": "Positive",
                        "score": 0.6,
                        "reasoning": "Article shows DMK's strong stance on language policy and Tamil rights."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "மொழிக் கொள்கை"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "மும்மொழிக் கொள்கை மீது மத்திய அரசிடம் பார்வை இல்லை",
                "author": None,
                "cluster": "DMK",
                "date": "2025-09-22"
            }
        },
        {
            "platform": "Print Daily",
            "publisher": "Hindu Tamil",
            "content": {
                "text": "சேலத்தில் நடைபெற்ற அதிமுக நிர்வாகிகள் கூட்டத்தில், கட்சியின் பொதுச் செயலாளர் எடப்பாடி பழனிசாமி பேசியதாவது: அதிமுகவில் நிலவும் அனைத்துப் பிரச்சினைகளுக்கும் விரைவில் முற்றுப்புள்ளி வைக்கப்படும். கட்சி மீண்டும் வலுப்பெற்று, வரும் தேர்தலில் மாபெரும் வெற்றி பெறும். தொண்டர்கள் அனைவரும் ஒற்றுமையுடன் செயல்பட வேண்டும்."
            },
            "author": {"publication_name": "Hindu Tamil", "author_name": "Staff Reporter"},
            "matched_clusters": [
                {"cluster_name": "ADMK", "cluster_type": "competitor"}
            ],
            "intelligence": {
                "entity_sentiments": {
                    "ADMK": {
                        "label": "Positive",
                        "score": 0.7,
                        "reasoning": "EPS shows confidence and unity message for AIADMK, positive party leadership."
                    }
                },
                "threat_level": "Low",
                "threat_campaign_topic": "அதிமுக ஒற்றுமை"
            },
            "published_at": datetime.fromisoformat("2025-09-22T00:00:00+00:00"),
            "collected_at": datetime.fromisoformat("2025-09-22T10:00:00+00:00"),
            "raw_data": {
                "headline": "அதிமுக பிரச்சினைகளுக்கு முற்றுப்புள்ளி வைப்போம்",
                "author": None,
                "cluster": "ADMK",
                "date": "2025-09-22"
            }
        }
    ]
    
    # Combine all data
    all_print_daily_data = times_of_india_data + hindu_tamil_data
    
    # Insert data into print_daily collection
    try:
        collection = db.print_daily
        
        # Clear existing data
        collection.delete_many({})
        
        result = collection.insert_many(all_print_daily_data)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} print daily articles")
        
        # Show inserted data count
        total_count = collection.count_documents({})
        print(f"📊 Total print daily articles in database: {total_count}")
        
        # Show sample by cluster and publisher
        times_count = collection.count_documents({"publisher": "Times of India"})
        hindu_count = collection.count_documents({"publisher": "Hindu Tamil"})
        dmk_count = collection.count_documents({"matched_clusters.cluster_name": "DMK"})
        admk_count = collection.count_documents({"matched_clusters.cluster_name": "ADMK"})
        bjp_count = collection.count_documents({"matched_clusters.cluster_name": "BJP"})
        
        print(f"  - Times of India articles: {times_count}")
        print(f"  - Hindu Tamil articles: {hindu_count}")
        print(f"  - DMK articles: {dmk_count}")
        print(f"  - ADMK articles: {admk_count}")
        print(f"  - BJP articles: {bjp_count}")
        
        print("✅ Print Daily collection created successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    
    client.close()

if __name__ == "__main__":
    create_print_daily_data()