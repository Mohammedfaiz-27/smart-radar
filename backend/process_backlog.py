#!/usr/bin/env python3
"""
Process raw data backlog manually
"""
import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from app.services.llm_processing_service import LLMProcessingService
from app.models.posts_table import PostCreate, Platform, SentimentLabel
from app.models.raw_data import ProcessingStatus
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin")

async def process_backlog(limit=100):
    """Process pending raw data entries"""
    print(f"🔄 Processing {limit} pending raw data entries...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URL)
    db = client.smart_radar
    
    # Initialize LLM service
    llm_service = LLMProcessingService()
    
    # Get pending entries
    pending_entries = list(db.raw_data.find(
        {"processing_status": "pending"}
    ).limit(limit))
    
    print(f"Found {len(pending_entries)} pending entries")
    
    processed_count = 0
    created_count = 0
    error_count = 0
    
    for i, entry in enumerate(pending_entries, 1):
        try:
            print(f"Processing entry {i}/{len(pending_entries)}: {entry.get('keyword', 'Unknown')}")
            
            # Extract post data from raw entry
            raw_json = entry.get("raw_json", {})
            platform = entry.get("platform", "X")
            cluster_id = entry.get("cluster_id")
            keyword = entry.get("keyword", "")
            
            # Create PostCreate object based on platform
            post = None
            
            if platform == "X":
                post = extract_x_post(raw_json, cluster_id, keyword)
            elif platform == "Facebook":
                post = extract_facebook_post(raw_json, cluster_id, keyword)
            elif platform == "YouTube":
                post = extract_youtube_post(raw_json, cluster_id, keyword)
            
            if post:
                # Process with LLM
                llm_update = await llm_service.process_post(post)
                
                # Apply LLM analysis
                post.sentiment_score = llm_update.sentiment_score
                post.sentiment_label = llm_update.sentiment_label
                post.is_threat = llm_update.is_threat
                post.key_narratives = llm_update.key_narratives
                post.language = llm_update.language
                
                # Convert to dict for MongoDB
                post_dict = post.model_dump()
                post_dict["fetched_at"] = datetime.utcnow()
                
                # Save to posts_table (handle duplicates)
                try:
                    result = db.posts_table.insert_one(post_dict)
                    created_count += 1
                    
                    print(f"  ✓ Created post: {result.inserted_id}")
                    print(f"    Language: {post.language}")
                    print(f"    Sentiment: {post.sentiment_label.value if post.sentiment_label else 'None'}")
                    
                except Exception as insert_error:
                    if "duplicate key error" in str(insert_error):
                        print(f"  ⚠️ Duplicate post skipped: {post.platform_post_id}")
                        # Still count as successful processing
                    else:
                        raise insert_error
                
                # Mark raw entry as processed
                db.raw_data.update_one(
                    {"_id": entry["_id"]},
                    {
                        "$set": {
                            "processing_status": "processed",
                            "posts_extracted": 1,
                            "processed_at": datetime.utcnow()
                        }
                    }
                )
                
            else:
                print(f"  ⚠️ Could not extract post from raw data")
                # Mark as failed
                db.raw_data.update_one(
                    {"_id": entry["_id"]},
                    {
                        "$set": {
                            "processing_status": "failed",
                            "processing_error": "Could not extract post data",
                            "processed_at": datetime.utcnow()
                        }
                    }
                )
                error_count += 1
            
            processed_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing entry: {e}")
            error_count += 1
            
            # Mark as failed
            db.raw_data.update_one(
                {"_id": entry["_id"]},
                {
                    "$set": {
                        "processing_status": "failed",
                        "processing_error": str(e),
                        "processed_at": datetime.utcnow()
                    }
                }
            )
            continue
    
    print(f"\n📊 Processing Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Created: {created_count}")
    print(f"  Errors: {error_count}")
    
    client.close()

def extract_x_post(raw_json, cluster_id, keyword):
    """Extract X/Twitter post from raw JSON"""
    try:
        legacy = raw_json.get("legacy", {})
        user = raw_json.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {})
        
        # Extract post data
        post_text = legacy.get("full_text", "")
        if not post_text:
            return None
            
        post = PostCreate(
            cluster_id=cluster_id,
            platform=Platform.X,
            platform_post_id=legacy.get("id_str", ""),
            author_username=user.get("screen_name", ""),
            author_display_name=user.get("name", ""),
            post_text=post_text,
            post_url=f"https://twitter.com/{user.get('screen_name', 'unknown')}/status/{legacy.get('id_str', '')}",
            posted_at=datetime.utcnow(),  # Could parse legacy.get("created_at") 
            likes=legacy.get("favorite_count", 0),
            comments=legacy.get("reply_count", 0),
            shares=legacy.get("retweet_count", 0),
            views=0  # Not available in basic response
        )
        
        return post
        
    except Exception as e:
        print(f"Error extracting X post: {e}")
        return None

def extract_facebook_post(raw_json, cluster_id, keyword):
    """Extract Facebook post from raw JSON"""
    try:
        # Facebook API structure varies, basic extraction
        post_text = raw_json.get("message", raw_json.get("text", ""))
        if not post_text:
            return None
            
        post = PostCreate(
            cluster_id=cluster_id,
            platform=Platform.FACEBOOK,
            platform_post_id=raw_json.get("id", ""),
            author_username=raw_json.get("author", ""),
            author_display_name=raw_json.get("author", ""),
            post_text=post_text,
            post_url=raw_json.get("url", ""),
            posted_at=datetime.utcnow(),
            likes=raw_json.get("reactions_count", 0),
            comments=raw_json.get("comments_count", 0),
            shares=raw_json.get("reshare_count", 0),
            views=0
        )
        
        return post
        
    except Exception as e:
        print(f"Error extracting Facebook post: {e}")
        return None

def extract_youtube_post(raw_json, cluster_id, keyword):
    """Extract YouTube video from raw JSON"""
    try:
        snippet = raw_json.get("snippet", {})
        statistics = raw_json.get("statistics", {})
        
        title = snippet.get("title", "")
        if not title:
            return None
            
        post = PostCreate(
            cluster_id=cluster_id,
            platform=Platform.YOUTUBE,
            platform_post_id=raw_json.get("id", {}).get("videoId", ""),
            author_username=snippet.get("channelTitle", ""),
            author_display_name=snippet.get("channelTitle", ""),
            post_text=f"{title}\n\n{snippet.get('description', '')}",
            post_url=f"https://www.youtube.com/watch?v={raw_json.get('id', {}).get('videoId', '')}",
            posted_at=datetime.utcnow(),  # Could parse snippet.get("publishedAt")
            likes=int(statistics.get("likeCount", 0)),
            comments=int(statistics.get("commentCount", 0)),
            shares=0,  # Not available
            views=int(statistics.get("viewCount", 0))
        )
        
        return post
        
    except Exception as e:
        print(f"Error extracting YouTube post: {e}")
        return None

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(process_backlog(limit))