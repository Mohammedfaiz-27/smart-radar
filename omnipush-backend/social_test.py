import os
import requests
import re
from langdetect import detect, LangDetectException


def detect_language(text):
    """
    Detect if text is in English or Tamil.
    Returns 'english', 'tamil', or 'other'.
    """
    if not text or not isinstance(text, str):
        return 'other'

    # Clean text - remove URLs, mentions, hashtags for better detection
    cleaned_text = re.sub(r'http\S+|www\.\S+', '', text)  # Remove URLs
    cleaned_text = re.sub(r'@\w+', '', cleaned_text)  # Remove mentions
    cleaned_text = re.sub(r'#\w+', '', cleaned_text)  # Remove hashtags
    cleaned_text = cleaned_text.strip()

    # Require minimum 10 characters for reliable detection
    if not cleaned_text or len(cleaned_text) < 10:
        return 'other'

    # First check for Tamil using Unicode range (more reliable for Tamil)
    tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
    tamil_chars = len(tamil_pattern.findall(text))
    total_chars = len(text.strip())

    if total_chars > 0:
        tamil_percentage = (tamil_chars / total_chars) * 100
        # If significant Tamil characters present (>15%), it's Tamil
        if tamil_percentage > 15:
            return 'tamil'

    # Use langdetect for Latin-script languages (English, Spanish, etc.)
    try:
        detected_lang = detect(cleaned_text)

        # Map langdetect codes to our language categories
        if detected_lang == 'en':
            return 'english'
        elif detected_lang == 'ta':
            return 'tamil'
        else:
            # Spanish (es), Italian (it), Turkish (tr), Polish (pl), etc.
            return 'other'
    except LangDetectException:
        # If detection fails, fall back to simple heuristic
        return 'other'


def filter_by_language(posts, allowed_languages=['english', 'tamil']):
    """
    Filter posts to keep only those in allowed languages.
    Works with both Facebook and Twitter post formats.
    """
    filtered_posts = []

    for post in posts:
        # Extract text content based on post structure
        text_content = None

        # Facebook post format
        if 'message' in post:
            text_content = post.get('message', '')
        # Twitter post format (nested structure)
        elif 'legacy' in post and 'full_text' in post.get('legacy', {}):
            text_content = post['legacy']['full_text']
        # Direct text field
        elif 'text' in post:
            text_content = post.get('text', '')
        elif 'full_text' in post:
            text_content = post.get('full_text', '')

        if text_content:
            language = detect_language(text_content)
            if language in allowed_languages:
                filtered_posts.append(post)

    return filtered_posts


def get_facebook_posts(query="Jolarpet", cursor=None):
    from datetime import datetime, timedelta

    """
    Fetch Facebook posts for a given query using cursor-based pagination.

    Args:
        query: Search query string
        cursor: Pagination cursor from previous response (optional)

    Returns:
        Dict with posts data and pagination cursor
        Format:
        {
            'data': {
                'items': [...],
                'page_info': {
                    'cursor': '...'  # Next page cursor
                }
            }
        }
    """
    url = "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts"

    # Calculate date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    querystring = {
        "query": query
    }

    # Add cursor for pagination if provided
    if cursor:
        querystring["cursor"] = cursor
    else:
        querystring.update({
            "location_uid": "0",
            "start_time": start_date.strftime("%Y-%m-%d"),
            "end_time": end_date.strftime("%Y-%m-%d"),
            "recent_posts": "true"
        })

    headers = {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY_FACEBOOK", "d5adc2df3dmsh1ec84b4b22692aep11a79cjsn27b1ce51db9e"),
        "x-rapidapi-host": "facebook-scraper-api4.p.rapidapi.com",
    }

    import logging
    logger = logging.getLogger(__name__)

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    # Extract cursor from response
    next_cursor = data.get('data', {}).get('page_info', {}).get('cursor')
    items_count = len(data.get('data', {}).get('items', []))

    # Debug logging
    if cursor:
        logger.info(f"Facebook pagination request - cursor: {cursor[:50] if len(cursor) > 50 else cursor}...")
        logger.info(f"Facebook pagination response - items: {items_count}, next_cursor: {'exists' if next_cursor else 'none'}")
    else:
        logger.info(f"Facebook initial request - query: '{query}', items: {items_count}, next_cursor: {'exists' if next_cursor else 'none'}")

    # Normalize response to include pagination metadata
    if 'data' not in data:
        data['data'] = {}
    if 'page_info' not in data['data']:
        data['data']['page_info'] = {}

    # Add has_more flag
    data['pagination'] = {
        'next_cursor': next_cursor,
        'has_more': bool(next_cursor)
    }

    return data

    """
    Response format from facebook-scraper-api4:
    {
        "status": true,
        "data": {
            "items": [
                {
                    "basic_info": {
                        "post_text": "சார் இங்க வாங்க பொம்பள இருக்குற வீட்டுல எப்படி நீங்க எகிறி குதிக்கலாம்?.. #Jolarpet | #LandIssue | #Police",
                        "url": "https://www.facebook.com/polimernews/videos/519053341145263/",
                        "post_id": "1199243465574950",
                        "created_time": "2026-01-03T10:30:16+0000"
                    },
                    "engagement": {
                        "reactions": 10832,
                        "comments": 376,
                        "shares": 5612
                    },
                    "author": {
                        "name": "Polimer News",
                        "id": "100064679229816",
                        "url": "https://www.facebook.com/polimernews"
                    },
                    "media": {
                        "type": "video",
                        "video_url": "https://www.facebook.com/polimernews/videos/519053341145263/"
                    }
                }
            ],
            "total_results": 20
        }
    }
    """


def get_twitter_posts(query="Jolarpet", pagination_token=None, max_results=20):
    """
    Fetch Twitter posts for a given query using Twitter v2 pagination pattern.

    Args:
        query: Search query string
        pagination_token: Token from previous response for getting next page (optional)
        max_results: Number of tweets to fetch (default: 20, max: 100)

    Returns:
        Dict with tweets data including next_token for pagination
        Format:
        {
            'data': [...],           # Tweet entries (v1.1 style from RapidAPI)
            'result': {...},         # Timeline result structure
            'meta': {
                'next_token': '...'  # Token for next page
            },
            'cursor': {...}          # Legacy cursor (if provided by API)
        }
    """
    url = "https://twitter241.p.rapidapi.com/search-v2"

    # Build query parameters following Twitter v2 pattern
    querystring = {
        "type": "Latest",
        "count": str(min(max_results, 20)),  # API may have max limit
        "query": query
    }

    # Add pagination token if provided (Twitter v2 style)
    if pagination_token:
        # Try both parameter names as different RapidAPI wrappers may use different names
        querystring["pagination_token"] = pagination_token
        querystring["cursor"] = pagination_token  # Fallback for v1.1-style APIs

    headers = {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY_TWITTER"),
        "x-rapidapi-host": "twitter241.p.rapidapi.com",
    }

    import logging
    logger = logging.getLogger(__name__)

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    # Extract next_token from response (check multiple possible locations)
    next_token = None

    # Method 1: Check meta.next_token (Twitter v2 standard)
    if 'meta' in data:
        next_token = data['meta'].get('next_token')

    # Method 2: Check cursor.bottom (Twitter v1.1 / RapidAPI wrapper style)
    if not next_token and 'cursor' in data:
        next_token = data['cursor'].get('bottom')

    # Method 3: Check pagination_token at root level
    if not next_token:
        next_token = data.get('pagination_token') or data.get('next_token')

    # Normalize response structure to include meta.next_token
    if 'meta' not in data:
        data['meta'] = {}

    data['meta']['next_token'] = next_token

    # Count actual entries for logging
    entry_count = 0
    instructions = data.get('result', {}).get('timeline', {}).get('instructions', [])
    for instruction in instructions:
        if instruction.get('type') == 'TimelineAddEntries':
            entry_count = len(instruction.get('entries', []))
            break

    # Debug logging
    if pagination_token:
        logger.info(f"Twitter pagination request - token: {pagination_token[:50] if len(pagination_token) > 50 else pagination_token}...")
        logger.info(f"Twitter pagination response - entries: {entry_count}, next_token: {next_token[:50] if next_token and len(next_token) > 50 else next_token}")
    else:
        logger.info(f"Twitter initial request - query: '{query}', entries: {entry_count}, next_token: {'exists' if next_token else 'none'}")

    if entry_count == 0 and next_token:
        logger.warning("Twitter API returned next_token but no entries. This may indicate API pagination issue.")

    return data

    """
    {
        "cursor": {
            "bottom": "DAADDAABCgABGyM1vKba0K0KAAIbF_9z0NqhEQAIAAIAAAACCAADAAAAAAgABAAAAAAKAAUbIzpPtUAnEAoABhsjOk-1P9jwAAA",
            "top": "DAADDAABCgABGyM1vKba0K0KAAIbF_9z0NqhEQAIAAIAAAABCAADAAAAAAgABAAAAAAKAAUbIzpPtUAnEAoABhsjOk-1P9jwAAA",
        },
        "result": {
            "timeline": {
                "instructions": [
                    {
                        "type": "TimelineAddEntries",
                        "entries": [
                            {
                                "entryId": "tweet-1955465747578409133",
                                "sortIndex": "1955470777226625024",
                                "content": {
                                    "entryType": "TimelineTimelineItem",
                                    "__typename": "TimelineTimelineItem",
                                    "itemContent": {
                                        "itemType": "TimelineTweet",
                                        "__typename": "TimelineTweet",
                                        "tweet_results": {
                                            "result": {
                                                "__typename": "Tweet",
                                                "rest_id": "1955465747578409133",
                                                "core": {
                                                    "user_results": {
                                                        "result": {
                                                            "__typename": "User",
                                                            "id": "VXNlcjoxNzk4MTYwMTYyODA2NzMwNzUz",
                                                            "rest_id": "1798160162806730753",
                                                            "affiliates_highlighted_label": {},
                                                            "avatar": {
                                                                "image_url": "https://pbs.twimg.com/profile_images/1887806343068708864/tWyfjJmT_normal.jpg"
                                                            },
                                                            "core": {
                                                                "created_at": "Wed Jun 05 01:09:43 +0000 2024",
                                                                "name": "Manikandan R - Say Yes To Women Safety & AIADMK",
                                                                "screen_name": "Manikandan_RIT",
                                                            },
                                                            "dm_permissions": {
                                                                "can_dm": False
                                                            },
                                                            "has_graduated_access": True,
                                                            "is_blue_verified": False,
                                                            "legacy": {
                                                                "default_profile": True,
                                                                "default_profile_image": False,
                                                                "description": "Subasri Enterprises -\nAIADMK - IT WING JOLARPET TIRUPATTUR DISTRICT",
                                                                "entities": {
                                                                    "description": {
                                                                        "urls": []
                                                                    },
                                                                    "url": {
                                                                        "urls": [
                                                                            {
                                                                                "display_url": "youtube.com/@aiadmkjolarpe…",
                                                                                "expanded_url": "https://youtube.com/@aiadmkjolarpetitwing?si=OSrlHEYX7sGRDNhI",
                                                                                "url": "https://t.co/tPb9btXkSU",
                                                                                "indices": [
                                                                                    0,
                                                                                    23,
                                                                                ],
                                                                            }
                                                                        ]
                                                                    },
                                                                },
                                                                "fast_followers_count": 0,
                                                                "favourites_count": 5417,
                                                                "followers_count": 167,
                                                                "friends_count": 451,
                                                                "has_custom_timelines": False,
                                                                "is_translator": False,
                                                                "listed_count": 1,
                                                                "media_count": 513,
                                                                "normal_followers_count": 167,
                                                                "pinned_tweet_ids_str": [
                                                                    "1941647521216069987"
                                                                ],
                                                                "possibly_sensitive": False,
                                                                "profile_banner_url": "https://pbs.twimg.com/profile_banners/1798160162806730753/1751772939",
                                                                "profile_interstitial_type": "",
                                                                "statuses_count": 2914,
                                                                "translator_type": "none",
                                                                "url": "https://t.co/tPb9btXkSU",
                                                                "want_retweets": False,
                                                                "withheld_in_countries": [],
                                                            },
                                                            "location": {"location": ""},
                                                            "media_permissions": {
                                                                "can_media_tag": True
                                                            },
                                                            "parody_commentary_fan_label": "None",
                                                            "profile_image_shape": "Circle",
                                                            "privacy": {"protected": False},
                                                            "relationship_perspectives": {
                                                                "following": False
                                                            },
                                                            "tipjar_settings": {
                                                                "is_enabled": True
                                                            },
                                                            "verification": {
                                                                "verified": False
                                                            },
                                                        }
                                                    }
                                                },
                                                "unmention_data": {},
                                                "edit_control": {
                                                    "edit_tweet_ids": [
                                                        "1955465747578409133"
                                                    ],
                                                    "editable_until_msecs": "1755057939000",
                                                    "is_edit_eligible": False,
                                                    "edits_remaining": "5",
                                                },
                                                "is_translatable": False,
                                                "views": {
                                                    "count": "4",
                                                    "state": "EnabledWithCount",
                                                },
                                                "source": '<a href="http://twitter.com/download/android" rel="nofollow">Twitter for Android</a>',
                                                "grok_analysis_button": True,
                                            }
                                        },
                                        "tweetDisplayType": "Tweet",
                                        "highlights": {
                                            "textHighlights": [
                                                {"startIndex": 51, "endIndex": 59}
                                            ]
                                        },
                                    },
                                    "clientEventInfo": {
                                        "component": "result",
                                        "element": "tweet",
                                        "details": {
                                            "timelinesDetails": {
                                                "controllerData": "DAACDAAFDAABDAABDAABCgABAAAAAAAAAAAAAAwAAgoAAQAAAAAAAAABCgACPmc3PbTGL24LAAMAAAAISm9sYXJwZXQKAAVFTzdSHzDFNAgABgAAAAEKAAdvYEeIW47v7QAAAAAA"
                                            }
                                        },
                                    },
                                },
                            },
                            {
                                "entryId": "tweet-1955100126663557429",
                                "sortIndex": "1955470777226625023",
                                "content": {
                                    "entryType": "TimelineTimelineItem",
                                    "__typename": "TimelineTimelineItem",
                                    "itemContent": {
                                        "itemType": "TimelineTweet",
                                        "__typename": "TimelineTweet",
                                        "tweet_results": {
                                            "result": {
                                                "__typename": "Tweet",
                                                "rest_id": "1955100126663557429",
                                                "core": {
                                                    "user_results": {
                                                        "result": {
                                                            "__typename": "User",
                                                            "id": "VXNlcjoxMTQzMzAwMg==",
                                                            "rest_id": "11433002",
                                                            "affiliates_highlighted_label": {},
                                                            "avatar": {
                                                                "image_url": "https://pbs.twimg.com/profile_images/1639879931101614091/8Ek2jVIO_normal.jpg"
                                                            },
                                                            "core": {
                                                                "created_at": "Sat Dec 22 14:50:52 +0000 2007",
                                                                "name": "മുരളി",
                                                                "screen_name": "muralewrites",
                                                            },
                                                            "dm_permissions": {
                                                                "can_dm": False
                                                            },
                                                            "has_graduated_access": True,
                                                            "is_blue_verified": True,
                                                            "legacy": {
                                                                "default_profile": False,
                                                                "default_profile_image": False,
                                                                "description": "Public Relations practitioner - Freelance content marketer, Writer, Executive Search professional, Freelancer, Cyclist 🚵🚵🚵 - Chennai & Kochi",
                                                                "entities": {
                                                                    "description": {
                                                                        "urls": []
                                                                    }
                                                                },
                                                                "fast_followers_count": 0,
                                                                "favourites_count": 58932,
                                                                "followers_count": 5042,
                                                                "friends_count": 3667,
                                                                "has_custom_timelines": True,
                                                                "is_translator": False,
                                                                "listed_count": 0,
                                                                "media_count": 3443,
                                                                "normal_followers_count": 5042,
                                                                "pinned_tweet_ids_str": [
                                                                    "1405474635588595712"
                                                                ],
                                                                "possibly_sensitive": False,
                                                                "profile_banner_url": "https://pbs.twimg.com/profile_banners/11433002/1679472667",
                                                                "profile_interstitial_type": "",
                                                                "statuses_count": 127689,
                                                                "translator_type": "none",
                                                                "want_retweets": False,
                                                                "withheld_in_countries": [],
                                                            },
                                                            "location": {
                                                                "location": "Chennai, India"
                                                            },
                                                            "media_permissions": {
                                                                "can_media_tag": True
                                                            },
                                                            "parody_commentary_fan_label": "None",
                                                            "profile_image_shape": "Circle",
                                                            "professional": {
                                                                "rest_id": "1463129859379527683",
                                                                "professional_type": "Business",
                                                                "category": [
                                                                    {
                                                                        "id": 580,
                                                                        "name": "Media & News Company",
                                                                        "icon_name": "",
                                                                    }
                                                                ],
                                                            },
                                                            "privacy": {"protected": False},
                                                            "relationship_perspectives": {
                                                                "following": False
                                                            },
                                                            "tipjar_settings": {},
                                                            "verification": {
                                                                "verified": False
                                                            },
                                                        }
                                                    }
                                                },
                                                "unmention_data": {},
                                                "edit_control": {
                                                    "edit_tweet_ids": [
                                                        "1955100126663557429"
                                                    ],
                                                    "editable_until_msecs": "1754970768000",
                                                    "is_edit_eligible": False,
                                                    "edits_remaining": "5",
                                                },
                                                "is_translatable": False,
                                                "views": {
                                                    "count": "166",
                                                    "state": "EnabledWithCount",
                                                },
                                                "source": '<a href="https://mobile.twitter.com" rel="nofollow">Twitter Web App</a>',
                                                "grok_analysis_button": True,
                                                "legacy": {
                                                    "bookmark_count": 0,
                                                    "bookmarked": False,
                                                    "created_at": "Tue Aug 12 02:52:48 +0000 2025",
                                                    "conversation_id_str": "1955099195922321527",
                                                    "display_text_range": [0, 279],
                                                    "entities": {
                                                        "hashtags": [],
                                                        "symbols": [],
                                                        "timestamps": [],
                                                        "urls": [],
                                                        "user_mentions": [],
                                                    },
                                                    "favorite_count": 2,
                                                    "favorited": False,
                                                    "full_text": "Seats:T Nagar, Thiruporur, Uthiramerur, Katpadi, Jolarpet, Krishnagiri, Mailam, Mettur, Rasipuram, Thiruchengode, Modakurichi,Dharapuram, Anthiyur, Gudalur, Mettupalayam,Kovai South, Kinathukadavu, Pollachi, Virudachalam, Neyveli, Mailaduthurai,Thirumayam, Vasudevanallur,Tenkasi",
                                                    "in_reply_to_screen_name": "muralewrites",
                                                    "in_reply_to_status_id_str": "1955099195922321527",
                                                    "in_reply_to_user_id_str": "11433002",
                                                    "is_quote_status": False,
                                                    "lang": "hi",
                                                    "quote_count": 0,
                                                    "reply_count": 1,
                                                    "retweet_count": 0,
                                                    "retweeted": False,
                                                    "user_id_str": "11433002",
                                                    "id_str": "1955100126663557429",
                                                },
                                            }
                                        },
                                        "tweetDisplayType": "Tweet",
                                        "highlights": {
                                            "textHighlights": [
                                                {"startIndex": 49, "endIndex": 57}
                                            ]
                                        },
                                    },
                                    "clientEventInfo": {
                                        "component": "result",
                                        "element": "tweet",
                                        "details": {
                                            "timelinesDetails": {
                                                "controllerData": "DAACDAAFDAABDAABDAABCgABAAAAAAAAAAAAAAwAAgoAAQAAAAAAAAABCgACPmc3PbTGL24LAAMAAAAISm9sYXJwZXQKAAVFTzdSHzDFNAgABgAAAAEKAAdvYEeIW47v7QAAAAAA"
                                            }
                                        },
                                    },
                                },
                            },
                            {
                                "entryId": "tweet-1954552293644206085",
                                "sortIndex": "1955470777226625022",
                                "content": {
                                    "entryType": "TimelineTimelineItem",
                                    "__typename": "TimelineTimelineItem",
                                    "itemContent": {
                                        "itemType": "TimelineTweet",
                                        "__typename": "TimelineTweet",
                                        "tweet_results": {
                                            "result": {
                                                "__typename": "Tweet",
                                                "rest_id": "1954552293644206085",
                                                "core": {
                                                    "user_results": {
                                                        "result": {
                                                            "__typename": "User",
                                                            "id": "VXNlcjozMjcwOTQ2OTI2",
                                                            "rest_id": "3270946926",
                                                            "affiliates_highlighted_label": {},
                                                            "avatar": {
                                                                "image_url": "https://pbs.twimg.com/profile_images/1559161951841689601/6Ed9Z8CJ_normal.jpg"
                                                            },
                                                            "core": {
                                                                "created_at": "Tue Jul 07 13:31:34 +0000 2015",
                                                                "name": "KVSS",
                                                                "screen_name": "kvsmanian1411",
                                                            },
                                                            "dm_permissions": {
                                                                "can_dm": False
                                                            },
                                                            "has_graduated_access": True,
                                                            "is_blue_verified": False,
                                                            "legacy": {
                                                                "default_profile": True,
                                                                "default_profile_image": False,
                                                                "description": "Expect respect for  opposite views n FOE of others .",
                                                                "entities": {
                                                                    "description": {
                                                                        "urls": []
                                                                    }
                                                                },
                                                                "fast_followers_count": 0,
                                                                "favourites_count": 30531,
                                                                "followers_count": 344,
                                                                "friends_count": 528,
                                                                "has_custom_timelines": True,
                                                                "is_translator": False,
                                                                "listed_count": 0,
                                                                "media_count": 49,
                                                                "normal_followers_count": 344,
                                                                "pinned_tweet_ids_str": [
                                                                    "1686262554186891264"
                                                                ],
                                                                "possibly_sensitive": False,
                                                                "profile_interstitial_type": "",
                                                                "statuses_count": 63844,
                                                                "translator_type": "none",
                                                                "want_retweets": False,
                                                                "withheld_in_countries": [],
                                                            },
                                                            "location": {
                                                                "location": "India"
                                                            },
                                                            "media_permissions": {
                                                                "can_media_tag": True
                                                            },
                                                            "parody_commentary_fan_label": "None",
                                                            "profile_image_shape": "Circle",
                                                            "privacy": {"protected": False},
                                                            "relationship_perspectives": {
                                                                "following": False
                                                            },
                                                            "tipjar_settings": {},
                                                            "verification": {
                                                                "verified": False
                                                            },
                                                        }
                                                    }
                                                },
                                                "unmention_data": {},
                                                "edit_control": {
                                                    "edit_tweet_ids": [
                                                        "1954552293644206085"
                                                    ],
                                                    "editable_until_msecs": "1754840155000",
                                                    "is_edit_eligible": True,
                                                    "edits_remaining": "5",
                                                },
                                                "is_translatable": False,
                                                "views": {
                                                    "count": "30",
                                                    "state": "EnabledWithCount",
                                                },
                                                "source": '<a href="http://twitter.com/download/android" rel="nofollow">Twitter for Android</a>',
                                                "grok_analysis_button": True,
                                                "legacy": {
                                                    "bookmark_count": 0,
                                                    "bookmarked": False,
                                                    "created_at": "Sun Aug 10 14:35:55 +0000 2025",
                                                    "conversation_id_str": "1954552293644206085",
                                                    "display_text_range": [0, 253],
                                                    "entities": {
                                                        "hashtags": [],
                                                        "symbols": [],
                                                        "timestamps": [],
                                                        "urls": [],
                                                        "user_mentions": [
                                                            {
                                                                "id_str": "3300204362",
                                                                "name": "Southern Railway",
                                                                "screen_name": "GMSRailway",
                                                                "indices": [0, 11],
                                                            }
                                                        ],
                                                    },
                                                    "favorite_count": 0,
                                                    "favorited": False,
                                                    "full_text": "@GMSRailway I am right now travelling in  the so called super fast West Coast exp.Train has already run late as usual when it arrived at Salem.Why some stoppages  after Jolarpet can't be eliminated to ensure train  does not reach   Palakkad. at odd hour",
                                                    "in_reply_to_screen_name": "GMSRailway",
                                                    "in_reply_to_user_id_str": "3300204362",
                                                    "is_quote_status": False,
                                                    "lang": "en",
                                                    "quote_count": 0,
                                                    "reply_count": 0,
                                                    "retweet_count": 0,
                                                    "retweeted": False,
                                                    "user_id_str": "3270946926",
                                                    "id_str": "1954552293644206085",
                                                },
                                            }
                                        },
                                        "tweetDisplayType": "Tweet",
                                        "highlights": {
                                            "textHighlights": [
                                                {"startIndex": 169, "endIndex": 177}
                                            ]
                                        },
                                    },
                                    "clientEventInfo": {
                                        "component": "result",
                                        "element": "tweet",
                                        "details": {
                                            "timelinesDetails": {
                                                "controllerData": "DAACDAAFDAABDAABDAABCgABAAAAAAAAAAAAAAwAAgoAAQAAAAAAAAABCgACPmc3PbTGL24LAAMAAAAISm9sYXJwZXQKAAVFTzdSHzDFNAgABgAAAAEKAAdvYEeIW47v7QAAAAAA"
                                            }
                                        },
                                    },
                                },
                            },
                        ],
                    }
                ]
            }
        },
    }

    """
