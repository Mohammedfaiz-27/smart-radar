#!/usr/bin/env python3
"""
Script to process news articles with LLM analysis and insert into posts_table
This will make them appear in the cluster dashboard with proper sentiment and threat analysis.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
import google.generativeai as genai
from bson import ObjectId

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')

# Import database
import sys
sys.path.append('/Users/Samrt radar Final /backend')
from app.core.database import connect_to_mongo, get_database

# Sample articles data
ARTICLES = [
    {
        "headline": "TVK chief Vijay hits out at T.N. CM Stalin over campaign curbs, foreign investment trips",
        "author": "The Hindu Bureau",
        "cluster": "TVK",
        "date": "2025-09-20",
        "body_text": "Tamilaga Vettri Kazhagam (TVK) founder and actor Vijay, in the second leg of his State-wide political tour on Saturday (September 20, 2025), questioned Chief Minister M.K. Stalin's claims about attracting investments through his foreign visits, and asked whether the trips were \"to bring investment to the State or to secure personal investments abroad.\" Addressing a large gathering at the Puthur roundabout near the Anna Statue in Nagapattinam, Mr. Vijay also accused the Chief Minister of indirectly threatening him by imposing restrictions on his campaign and hampering it. Criticising the BJP and the DMK on issues concerning the fishing community in the State, Mr. Vijay said the BJP was engaged in \"politics of exclusion,\" and charged that Mr. Stalin only writes letters on fishermen's issues, but takes no concrete action."
    },
    {
        "headline": "BJP will not interfere in internal affairs of other parties, says Nainar Nagendran",
        "author": "The Hindu Bureau", 
        "cluster": "BJP",
        "date": "2025-09-21",
        "body_text": "Tamil Nadu BJP president Nainar Nagendran on Sunday said his party would not interfere in the internal affairs of other parties, including the AIADMK and PMK. After meeting AIADMK general secretary Edappadi K. Palaniswami at his residence in Salem, Nagendran told reporters that the hour-long meeting was only a \"courtesy call\" and no political issues were taken up. BJP's national in-charge for Tamil Nadu, Arvind Menon and state vice-president of the party, K.P. Ramalingam, were also present during the meeting. \"There are no permanent friends or foes in politics. On speculation that AIADMK's splits could affect its electoral strength in southern Tamil Nadu, he dismissed such concerns, saying the real issue was the DMK government's failure to deliver on governance and people's welfare. He asserted that a change of government was certain in the next assembly elections. Nagendran also responded to actor Vijay's recent comment that the 2026 assembly polls would be a contest between DMK and his newly launched party, TVK. \"He has just started his party. He has to identify suitable candidates, prepare an election strategy and build his organisation. Nagendran also announced that the BJP would formally launch its assembly election campaign on October 11 in Madurai, with alliance leaders set to participate."
    },
    {
        "headline": "No place for betrayers: AIADMK chief rules out OPS, TTV Dhinakaran's return",
        "author": "Lokpria Vasudevan",
        "cluster": "ADMK", 
        "date": "2025-09-16",
        "body_text": "AIADMK general secretary Edappadi K Palaniswami (EPS) on Monday firmly ruled out any move to bring back expelled leaders O Panneerselvam (OPS) or TTV Dhinakaran, even as some veterans, including KA Sengottaiyan, urged reunification ahead of the 2026 assembly polls. Speaking at an event to mark the birth anniversary of Dravidian stalwart and former Chief Minister CN Annadurai, EPS said those who \"betrayed\" the organisation had no place in it. \"More than power, self-respect is important for us. I will not give even a bit of it,\" he declared. Without naming OPS, the former chief minister recalled how some leaders voted against the AIADMK government during the 2017 trust vote and later vandalised the party headquarters in July 2022. \"We forgave him and even made him deputy Chief Minister. Still he didn't reform.\""
    },
    {
        "headline": "DMK made Tamil Nadu bow its head due to corruption scandals, says EPS",
        "author": "Express News Service",
        "cluster": "ADMK",
        "date": "2025-09-20", 
        "body_text": "The DMK can think of defeating the AIADMK in 2036, not 2026, as we are moving at jet speed while they remain far behind, said AIADMK general secretary Edappadi K Palaniswami, on Friday. Addressing large crowds in Rasipuram and Senthamangalam constituencies in Namakkal district as part of his 'Makkalai Kaapom, Thamizhagathai Meetpom' campaign, Palaniswami attacked the government over corruption. The chief minister says that he will not let Tamil Nadu bow its head. But at the national level, the DMK and its former union ministers made Tamil Nadu bow its head due to its corruption scandals, including the 2G spectrum case, he said. \"When people hear the word corruption, the DMK comes to mind.\" He also attacked the DMK government over \"serious governance failures\". Citing the incident at Sirkazhi government hospital where 27 pregnant women were allegedly given the wrong injection, Palaniswami accused Health and Family Welfare Minister Ma Subramanian of neglecting government hospitals. Raising concern over alleged cases of kidney thefts, he said, \"After the illegal kidney sale racket came to light and was proven, the government has only cancelled the kidney transplant license, but no arrests have been made yet.\" He criticised the shifting of Rasipuram's new bus stand to a location seven kilometres away, alleging the move was designed to boost real estate prices, benefitting those close to the DMK. Further, Palaniswami said the DMK government had put aside a Rs 932-crore drinking water project that was meant to benefit Rasipuram and nearby panchayats. He also alleged that law and order problems were increasing. On the education front, Palaniswami accused the DMK of betraying students by failing to abolish NEET."
    },
    {
        "headline": "Annamalai will not contest 2026 Tamil Nadu Assembly elections: BJP sources",
        "author": "Shalini Lobo",
        "cluster": "BJP",
        "date": "2025-07-30",
        "body_text": "Former Tamil Nadu BJP president K Annamalai will not contest the 2026 polls, he is expected to be elevated to a national position within the party, according to sources from the BJP. Although there has been no official announcement from the BJP's central leadership, sources within the party said discussions have been ongoing about repositioning Annamalai in a key national role in Delhi. Last month, Union Home Minister Amit Shah had confirmed that Annamalai will play an important role in the state politics and will also be given responsibilities at the national level. Annamalai, a former IPS officer of the Karnataka cadre who joined the BJP in 2020, was made the Tamil Nadu state president in 2021. Though Annamalai contested the Coimbatore Lok Sabha seat last year, he was defeated by DMK's Ganapathy Rajkumar."
    },
    {
        "headline": "TVK's Prabhakaran praise ignites political row in Tamil Nadu; DMK hits back",
        "author": None,
        "cluster": "TVK",
        "date": "2025-09-21",
        "body_text": "A political controversy is developing in Tamil Nadu ahead of the 2026 elections. Actor-politician Vijay, chief of the TVK, invoked Liberation Tigers of Tamil Eelam (LTTE) leader Prabhakaran at a rally in Nagapattinam on Saturday. During his speech, Vijay referred to Prabhakaran as a 'mother figure' for Sri Lankan Tamils and stated it is TVK's responsibility to amplify their voice, noting their suffering after his death. Posters of Prabhakaran, the mastermind behind the 1991 assassination of Prime Minister Rajiv Gandhi, were also seen at the rally. The DMK has responded to Vijay's comments, stating they have consistently championed Tamil rights. The party has also described Vijay's supporters as disruptive, with a speaker stating, \"Vijay gathers a huge crowd, they spoil everything...they climb on the electric posts...they fall, they get injured...even they disconnect the wiring and other things. All mischief they do.\""
    }
]

async def analyze_article_with_llm(article: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze article with Gemini 2.5 Pro for sentiment, threats, and intelligence"""
    
    prompt = f"""Analyze this Tamil Nadu political news article and provide a JSON response with intelligence analysis:

**Article Details:**
Headline: {article['headline']}
Author: {article.get('author', 'Unknown')}
Date: {article['date']}
Cluster: {article['cluster']}
Content: {article['body_text']}

**Analysis Required:**
1. **Sentiment Analysis**: Determine if this article is positive, negative, or neutral towards:
   - DMK (current ruling party)
   - AIADMK (main opposition)
   - BJP (national party)
   - TVK (new party by actor Vijay)

2. **Threat Level Assessment**: Evaluate if this article represents a threat to any political party:
   - high: Direct attacks, serious allegations, major controversies
   - medium: Moderate criticism, political challenges
   - low: Minor issues, routine political news
   - none: Neutral reporting

3. **Intelligence Summary**: Provide key insights and implications

4. **Entity Sentiments**: Analyze sentiment towards key political figures mentioned

**CRITICAL: Return ONLY a valid JSON object with this exact structure:**
{{
    "sentiment": "positive|negative|neutral",
    "sentiment_score": 0.0-1.0,
    "sentiment_label": "Positive|Negative|Neutral", 
    "threat_level": "high|medium|low|none",
    "is_threat": true|false,
    "summary": "Brief 2-3 sentence summary of key points",
    "key_topics": ["topic1", "topic2", "topic3"],
    "entity_sentiments": {{
        "M.K. Stalin": {{"label": "Positive|Negative|Neutral", "score": 0.0-1.0}},
        "Edappadi Palaniswami": {{"label": "Positive|Negative|Neutral", "score": 0.0-1.0}},
        "Vijay": {{"label": "Positive|Negative|Neutral", "score": 0.0-1.0}}
    }},
    "political_impact": "high|medium|low",
    "target_party": "DMK|AIADMK|BJP|TVK|multiple",
    "controversy_level": "high|medium|low|none"
}}

Do NOT include any text before or after the JSON object."""

    try:
        logger.info(f"Analyzing article: {article['headline'][:50]}...")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response text
        if response_text.startswith('```json') and response_text.endswith('```'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```') and response_text.endswith('```'):
            response_text = response_text[3:-3].strip()
        elif '{' in response_text and '}' in response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            response_text = response_text[start:end]
        
        # Parse JSON
        analysis = json.loads(response_text)
        logger.info(f"✅ Analysis complete: {analysis.get('sentiment', 'unknown')} sentiment, {analysis.get('threat_level', 'unknown')} threat")
        return analysis
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        logger.error(f"Raw response: {response_text}")
        # Return fallback analysis
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.5,
            "sentiment_label": "Neutral",
            "threat_level": "low",
            "is_threat": False,
            "summary": "Political news article requiring manual review",
            "key_topics": ["politics", "tamil nadu"],
            "entity_sentiments": {},
            "political_impact": "medium",
            "target_party": article['cluster'],
            "controversy_level": "low"
        }
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return {
            "sentiment": "neutral", 
            "sentiment_score": 0.5,
            "sentiment_label": "Neutral",
            "threat_level": "low",
            "is_threat": False,
            "summary": "Analysis failed - manual review required",
            "key_topics": ["error"],
            "entity_sentiments": {},
            "political_impact": "low",
            "target_party": article['cluster'],
            "controversy_level": "none"
        }

def map_cluster_to_type(cluster: str) -> str:
    """Map cluster name to cluster_type for dashboard"""
    cluster_mapping = {
        'DMK': 'own',        # DMK is ruling party (own)
        'ADMK': 'competitor', # AIADMK is main opposition
        'BJP': 'competitor',  # BJP is opposition
        'TVK': 'competitor'   # TVK is new opposition party
    }
    return cluster_mapping.get(cluster, 'competitor')

async def insert_article_to_posts_table(article: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Insert analyzed article into posts_table"""
    
    # Connect to database
    db = get_database()
    collection = db.posts_table
    
    # Map cluster to cluster_type
    cluster_type = map_cluster_to_type(article['cluster'])
    
    # Create post document
    post_doc = {
        "_id": ObjectId(),
        "platform": "Print Magazine",
        "platform_post_id": f"news_{article['cluster']}_{article['date']}_{hash(article['headline']) % 10000}",
        "author_username": article.get('author', 'News Bureau'),
        "author_display_name": article.get('author', 'News Bureau'),
        "post_text": f"{article['headline']}\n\n{article['body_text']}",
        "content": f"{article['headline']}\n\n{article['body_text']}",
        "post_url": f"https://news.example.com/{article['cluster'].lower()}/{article['date']}",
        "url": f"https://news.example.com/{article['cluster'].lower()}/{article['date']}",
        "posted_at": datetime.fromisoformat(f"{article['date']}T10:00:00"),
        "fetched_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        
        # Cluster information
        "cluster_id": article['cluster'].lower(),
        "cluster_type": cluster_type,
        "cluster_name": article['cluster'],
        
        # Sentiment and Intelligence from LLM analysis
        "sentiment": analysis['sentiment'],
        "sentiment_score": analysis['sentiment_score'],
        "sentiment_label": analysis['sentiment_label'],
        "intelligence": {
            "sentiment_label": analysis['sentiment_label'],
            "sentiment_score": analysis['sentiment_score'],
            "threat_level": analysis['threat_level'],
            "is_threat": analysis['is_threat'],
            "summary": analysis['summary'],
            "entity_sentiments": analysis['entity_sentiments'],
            "political_impact": analysis['political_impact'],
            "target_party": analysis['target_party'],
            "controversy_level": analysis['controversy_level']
        },
        
        # Threat information
        "threat_level": analysis['threat_level'],
        "is_threat": analysis['is_threat'],
        
        # Engagement metrics (news articles)
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "views": 100,  # Default view count for news
        "engagement_metrics": {
            "likes": 0,
            "comments": 0, 
            "shares": 0,
            "views": 100
        },
        
        # Processing status
        "processing_status": "completed",
        "has_been_responded_to": False,
        "response_generated": False,
        
        # Additional metadata
        "language": "tamil" if any(word in article['body_text'] for word in ['தமிழ்', 'நாடு', 'அரசு']) else "english",
        "key_topics": analysis.get('key_topics', []),
        "article_type": "news",
        "source_type": "news_article"
    }
    
    try:
        # Insert into posts_table
        result = await collection.insert_one(post_doc)
        logger.info(f"✅ Inserted article: {article['headline'][:50]}... (ID: {result.inserted_id})")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"❌ Failed to insert article: {e}")
        return None

async def get_cluster_keywords() -> Dict[str, List[str]]:
    """Get cluster keywords from database"""
    db = get_database()
    clusters_collection = db.clusters
    
    cluster_keywords = {}
    async for cluster in clusters_collection.find():
        cluster_name = cluster.get('name', '').upper()
        keywords = cluster.get('keywords', [])
        cluster_keywords[cluster_name] = keywords
        
    logger.info(f"Found cluster keywords: {cluster_keywords}")
    return cluster_keywords

async def main():
    """Main function to process all articles"""
    logger.info("🚀 Starting article processing with LLM analysis...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Get cluster keywords for reference
    cluster_keywords = await get_cluster_keywords()
    
    processed_count = 0
    success_count = 0
    
    for article in ARTICLES:
        try:
            logger.info(f"\n📰 Processing: {article['headline'][:60]}...")
            
            # Analyze with LLM
            analysis = await analyze_article_with_llm(article)
            
            # Insert into posts_table
            post_id = await insert_article_to_posts_table(article, analysis)
            
            if post_id:
                success_count += 1
                logger.info(f"✅ Successfully processed article #{processed_count + 1}")
            else:
                logger.error(f"❌ Failed to insert article #{processed_count + 1}")
                
            processed_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing article #{processed_count + 1}: {e}")
            processed_count += 1
            continue
    
    logger.info(f"\n🎯 Processing Complete!")
    logger.info(f"📊 Total articles processed: {processed_count}")
    logger.info(f"✅ Successfully inserted: {success_count}")
    logger.info(f"❌ Failed: {processed_count - success_count}")
    logger.info(f"\n💡 Articles are now available in the cluster dashboard at:")
    logger.info(f"   🌐 http://localhost:3000")
    logger.info(f"   📈 Check sentiment analysis and threat detection!")

if __name__ == "__main__":
    asyncio.run(main())