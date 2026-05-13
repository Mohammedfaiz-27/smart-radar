import os
import asyncio
import aiohttp
from openai import AsyncOpenAI
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import feedparser
import logging
import json
import time
from config.prompts import Prompts

logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self):
        logger.info("Initializing ResearchService")
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.language = "Tamil"
        logger.info("ResearchService initialized successfully")

    async def research_city(self, city: str) -> Dict[str, Any]:
        """Legacy method - research city using both OpenAI and Perplexity APIs"""
        logger.info(f"Starting city research for: {city}")
        start_time = time.time()
        
        try:
            result = await self.research_query(city)
            duration = time.time() - start_time
            logger.info(f"City research completed for '{city}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"City research failed for '{city}' after {duration:.2f} seconds: {e}")
            raise

    async def research_query(self, query: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Enhanced research with incremental updates and fallbacks"""
        logger.info(f"Starting comprehensive research for query: '{query}'")
        overall_start_time = time.time()
        
        # Initialize result structure with all sections
        result = {
            "query": query,
            "about": None,
            "history": None, 
            "current_affairs": None,
            "competitors": None,
            "challenges": None,
            "plus_points": None,
            "negative_points": None,
            
            # Legacy compatibility
            "executive_summary": "",
            "topic_analysis": "",
            "multi_perspective": "",
            "perplexity_research": "",
            "synthesis": "",
            "openai_analysis": ""
        }
        
        # Define research tasks with incremental updates
        research_sections = [
            ("about", self._get_understanding),
            ("history", self._get_history),
            ("current_affairs", self._get_current_affairs),
            ("competitors", self._get_competitors),
            ("challenges", self._get_challenges),
            ("plus_points", self._get_plus_points),
            ("negative_points", self._get_negative_points)
        ]
        
        logger.info(f"Research will cover {len(research_sections)} sections: {[section[0] for section in research_sections]}")
        
        # Execute each section and update incrementally
        for i, (section_name, section_func) in enumerate(research_sections, 1):
            section_start_time = time.time()
            logger.info(f"Starting research section {i}/{len(research_sections)}: '{section_name}' for query: '{query}'")
            
            try:
                if progress_callback:
                    await progress_callback({"section": section_name, "status": "starting", **result})
                    
                section_data = await section_func(query, result.get("about"))
                result[section_name] = section_data
                
                section_duration = time.time() - section_start_time
                logger.info(f"Completed research section '{section_name}' in {section_duration:.2f} seconds")
                
                if progress_callback:
                    await progress_callback({"section": section_name, "status": "completed", **result})
                    
            except Exception as e:
                section_duration = time.time() - section_start_time
                logger.exception(f"Error in research section '{section_name}' after {section_duration:.2f} seconds: {e}")
                result[section_name] = f"Error: {str(e)}"
                
                if progress_callback:
                    await progress_callback({"section": section_name, "status": "error", "error": str(e), **result})
        
        # Update legacy fields for backward compatibility
        logger.info("Updating legacy compatibility fields")
        result["topic_analysis"] = result["about"] or ""
        result["multi_perspective"] = result["competitors"] or ""
        result["perplexity_research"] = result["current_affairs"] or ""
        result["openai_analysis"] = result["about"] or ""
        result["executive_summary"] = result["about"] or ""
        
        overall_duration = time.time() - overall_start_time
        logger.info(f"Completed comprehensive research for query '{query}' in {overall_duration:.2f} seconds")
        
        return result

    async def _get_understanding(self, query: str, context: Optional[str] = None) -> str:
        """Get basic understanding of the query (2-3 sentences)"""
        logger.info(f"Getting basic understanding for query: '{query}'")
        start_time = time.time()
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a knowledgeable assistant. Provide a brief, clear understanding of any topic in 2-3 sentences. Be concise and informative."
                },
                {
                    "role": "user", 
                    "content": f"Explain what '{query}' is in 2-3 sentences. Be clear and concise. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Basic understanding completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Basic understanding failed for '{query}' after {duration:.2f} seconds: {e}")
            raise

    async def _get_history(self, query: str, understanding: Optional[str] = None) -> str:
        """Get detailed history about the query"""
        logger.info(f"Getting detailed history for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are a historical research expert. Provide detailed historical information about topics, including key events, developments, and evolution over time."
                },
                {
                    "role": "user",
                    "content": f"{context}Provide detailed historical information about '{query}'. Include key events, developments, milestones, and how it has evolved over time. Be comprehensive and factual. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"History research completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"History research failed for '{query}' after {duration:.2f} seconds: {e}")
            raise
    
    async def _get_current_affairs(self, query: str, understanding: Optional[str] = None) -> str:
        """Get current affairs and recent developments"""
        logger.info(f"Getting current affairs for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are a current affairs expert. Provide up-to-date information about recent developments, news, and current issues related to any topic."
                },
                {
                    "role": "user",
                    "content": f"{context}Provide detailed current affairs and recent developments about '{query}'. Include recent news, current issues, latest developments, and ongoing trends. Focus on what's happening now. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Current affairs research completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Current affairs research failed for '{query}' after {duration:.2f} seconds: {e}")
            raise
    
    async def _get_competitors(self, query: str, understanding: Optional[str] = None) -> str:
        """Get information about competitors or alternatives"""
        logger.info(f"Getting competitor analysis for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are a competitive analysis expert. Identify and analyze competitors, alternatives, or similar entities in any domain."
                },
                {
                    "role": "user",
                    "content": f"{context}Identify and analyze competitors, alternatives, or similar entities related to '{query}'. Include key players, their strengths, market position, and competitive dynamics. Be comprehensive. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Competitor analysis completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Competitor analysis failed for '{query}' after {duration:.2f} seconds: {e}")
            raise
    
    async def _get_challenges(self, query: str, understanding: Optional[str] = None) -> str:
        """Get information about challenges and problems"""
        logger.info(f"Getting challenges analysis for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying challenges and problems. Analyze any topic to identify key challenges, obstacles, and difficulties."
                },
                {
                    "role": "user",
                    "content": f"{context}Identify and analyze the key challenges, problems, obstacles, and difficulties related to '{query}'. Include current issues, potential problems, and systemic challenges. Be thorough and realistic. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Challenges analysis completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Challenges analysis failed for '{query}' after {duration:.2f} seconds: {e}")
            raise
    
    async def _get_plus_points(self, query: str, understanding: Optional[str] = None) -> str:
        """Get positive aspects and advantages"""
        logger.info(f"Getting positive points analysis for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying positive aspects and advantages. Analyze any topic to highlight strengths, benefits, and positive qualities."
                },
                {
                    "role": "user",
                    "content": f"{context}Identify and analyze the positive aspects, advantages, strengths, and benefits related to '{query}'. Include key strengths, unique advantages, and positive qualities. Be comprehensive and factual. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Positive points analysis completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Positive points analysis failed for '{query}' after {duration:.2f} seconds: {e}")
            raise
    
    async def _get_negative_points(self, query: str, understanding: Optional[str] = None) -> str:
        """Get negative aspects and disadvantages"""
        logger.info(f"Getting negative points analysis for query: '{query}'")
        start_time = time.time()
        
        try:
            context = f"Understanding: {understanding}\n\n" if understanding else ""
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying negative aspects and disadvantages. Analyze any topic to highlight weaknesses, drawbacks, and negative qualities."
                },
                {
                    "role": "user",
                    "content": f"{context}Identify and analyze the negative aspects, disadvantages, weaknesses, and drawbacks related to '{query}'. Include key weaknesses, potential issues, and negative qualities. Be balanced and constructive. Output should be in {self.language} in markdown format."
                }
            ]
            result = await self._call_with_fallback(messages)
            duration = time.time() - start_time
            logger.info(f"Negative points analysis completed for '{query}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Negative points analysis failed for '{query}' after {duration:.2f} seconds: {e}")
            raise

    async def _get_perplexity_research(self, query: str) -> str:
        """Legacy method - Get research data from Perplexity API"""
        logger.info(f"Getting Perplexity research for query: '{query}' (legacy method)")
        return await self._get_current_affairs(query)
        
    async def _get_topic_analysis(self, query: str) -> str:
        """Legacy method - Get topic analysis and decomposition"""
        logger.info(f"Getting topic analysis for query: '{query}' (legacy method)")
        return await self._get_understanding(query)
        
    async def _get_multi_perspective_analysis(self, query: str) -> str:
        """Legacy method - Get multi-perspective analysis"""
        logger.info(f"Getting multi-perspective analysis for query: '{query}' (legacy method)")
        return await self._get_competitors(query)
        
    async def _synthesize_research(self, query: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - Synthesize all research findings"""
        logger.info(f"Starting research synthesis for query: '{query}'")
        start_time = time.time()
        
        try:
            messages = Prompts.get_synthesis_messages(query, research_data)
            content = await self._call_with_fallback(messages)
            
            # Try to parse as JSON for structured output
            try:
                result = json.loads(content)
                duration = time.time() - start_time
                logger.info(f"Research synthesis completed for '{query}' in {duration:.2f} seconds (JSON output)")
                return result
            except json.JSONDecodeError:
                # If not JSON, return as structured text
                result = {
                    "executive_summary": content[:500] + "..." if len(content) > 500 else content,
                    "detailed_synthesis": content
                }
                duration = time.time() - start_time
                logger.info(f"Research synthesis completed for '{query}' in {duration:.2f} seconds (text output)")
                return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Research synthesis failed for '{query}' after {duration:.2f} seconds: {e}")
            raise Exception(f"Synthesis error: {str(e)}")

    async def _get_openai_analysis(self, city: str) -> str:
        """Get city analysis from OpenAI (legacy)"""
        logger.info(f"Getting OpenAI city analysis for: '{city}' (legacy method)")
        start_time = time.time()
        
        try:
            messages = Prompts.get_city_research_messages(city)
            result = await self._call_openai_api(messages)
            duration = time.time() - start_time
            logger.info(f"OpenAI city analysis completed for '{city}' in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"OpenAI city analysis failed for '{city}' after {duration:.2f} seconds: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _call_perplexity_api(self, messages: List[Dict[str, str]]) -> str:
        """Make a call to Perplexity API"""
        if not self.perplexity_api_key:
            logger.error("Perplexity API key not configured")
            raise Exception("Perplexity API key not configured")
            
        logger.info("Making Perplexity API call")
        start_time = time.time()
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "sonar-pro",
                "messages": messages,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data["choices"][0]["message"]["content"]
                        duration = time.time() - start_time
                        logger.info(f"Perplexity API call successful in {duration:.2f} seconds")
                        return result
                    else:
                        error_text = await response.text()
                        duration = time.time() - start_time
                        logger.error(f"Perplexity API error after {duration:.2f} seconds: {response.status} - {error_text}")
                        raise Exception(
                            f"Perplexity API error: {response.status} - {error_text}"
                        )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Perplexity API call failed after {duration:.2f} seconds: {e}")
            raise Exception(f"Perplexity API error: {str(e)}")
    
    async def _call_openai_api(self, messages: List[Dict[str, str]]) -> str:
        """Make a call to OpenAI API"""
        logger.info("Making OpenAI API call")
        start_time = time.time()
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
            )
            result = response.choices[0].message.content
            duration = time.time() - start_time
            logger.info(f"OpenAI API call successful in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"OpenAI API call failed after {duration:.2f} seconds: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _call_with_fallback(self, messages: List[Dict[str, str]]) -> str:
        """Call Perplexity API first, fallback to OpenAI if it fails"""
        logger.info("Starting API call with fallback strategy")
        start_time = time.time()
        
        try:
            # Try Perplexity first
            logger.info("Attempting Perplexity API call first")
            result = await self._call_perplexity_api(messages)
            duration = time.time() - start_time
            logger.info(f"API call with fallback completed successfully using Perplexity in {duration:.2f} seconds")
            return result
        except Exception as perplexity_error:
            logger.warning(f"Perplexity API failed: {perplexity_error}")
            try:
                # Fallback to OpenAI
                logger.info("Falling back to OpenAI API")
                result = await self._call_openai_api(messages)
                duration = time.time() - start_time
                logger.info(f"API call with fallback completed successfully using OpenAI fallback in {duration:.2f} seconds")
                return result
            except Exception as openai_error:
                duration = time.time() - start_time
                logger.error(f"Both APIs failed after {duration:.2f} seconds - Perplexity: {perplexity_error}, OpenAI: {openai_error}")
                raise Exception(f"Both APIs failed - Perplexity: {perplexity_error}, OpenAI: {openai_error}")


async def fetch_news_from_sources(source_type: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch news from various sources based on type"""
    logger.info(f"Starting news fetch from {source_type} sources")
    start_time = time.time()
    
    try:
        if source_type.lower() == 'rss':
            result = await fetch_rss_news(config)
        elif source_type.lower() == 'api':
            result = await fetch_api_news(config)
        elif source_type.lower() == 'webhook':
            # Webhook sources would be handled differently (stored in DB when received)
            logger.info("Webhook sources handled separately - returning empty list")
            result = []
        else:
            logger.warning(f"Unknown source type: {source_type}")
            result = []
        
        duration = time.time() - start_time
        logger.info(f"News fetch from {source_type} sources completed in {duration:.2f} seconds, retrieved {len(result)} items")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"Failed to fetch news from {source_type} after {duration:.2f} seconds: {e}")
        return []


async def fetch_rss_news(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch news from RSS feeds"""
    logger.info("Starting RSS news fetch")
    start_time = time.time()
    
    try:
        rss_urls = config.get('urls', [])
        max_items = config.get('max_items', 10)
        
        logger.info(f"Fetching RSS news from {len(rss_urls)} URLs, max {max_items} items per feed")
        
        all_items = []
        
        for i, url in enumerate(rss_urls, 1):
            feed_start_time = time.time()
            logger.info(f"Processing RSS feed {i}/{len(rss_urls)}: {url}")
            
            try:
                # Use aiohttp to fetch RSS feed
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            feed_items = []
                            for entry in feed.entries[:max_items]:
                                item = {
                                    'title': entry.get('title', 'No title'),
                                    'content': entry.get('summary', entry.get('description', '')),
                                    'url': entry.get('link', ''),
                                    'published_at': None
                                }
                                
                                # Parse published date if available
                                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                    try:
                                        item['published_at'] = datetime(*entry.published_parsed[:6]).isoformat()
                                    except:
                                        pass
                                
                                feed_items.append(item)
                            
                            all_items.extend(feed_items)
                            feed_duration = time.time() - feed_start_time
                            logger.info(f"RSS feed {i}/{len(rss_urls)} processed in {feed_duration:.2f} seconds, got {len(feed_items)} items")
                        else:
                            feed_duration = time.time() - feed_start_time
                            logger.warning(f"Failed to fetch RSS from {url} after {feed_duration:.2f} seconds: {response.status}")
            except Exception as e:
                feed_duration = time.time() - feed_start_time
                logger.exception(f"Error fetching RSS from {url} after {feed_duration:.2f} seconds: {e}")
                continue
        
        overall_duration = time.time() - start_time
        logger.info(f"RSS news fetch completed in {overall_duration:.2f} seconds, total items: {len(all_items)}")
        return all_items
        
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"RSS fetch error after {duration:.2f} seconds: {e}")
        return []


async def fetch_api_news(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch news from API endpoints"""
    logger.info("Starting API news fetch")
    start_time = time.time()
    
    try:
        api_url = config.get('url')
        headers = config.get('headers', {})
        params = config.get('params', {})
        max_items = config.get('max_items', 10)
        
        if not api_url:
            logger.warning("No API URL provided in config")
            return []
        
        logger.info(f"Fetching API news from: {api_url}, max {max_items} items")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract items based on API structure
                    items_key = config.get('items_key', 'items')
                    items_data = data.get(items_key, data if isinstance(data, list) else [])
                    
                    if not isinstance(items_data, list):
                        items_data = [items_data]
                    
                    logger.info(f"Processing {len(items_data)} items from API response")
                    
                    processed_items = []
                    for item_data in items_data[:max_items]:
                        try:
                            item = {
                                'title': item_data.get(config.get('title_field', 'title'), 'No title'),
                                'content': item_data.get(config.get('content_field', 'content'), ''),
                                'url': item_data.get(config.get('url_field', 'url'), ''),
                                'published_at': item_data.get(config.get('date_field', 'published_at'))
                            }
                            
                            # Convert published_at to ISO format if needed
                            if item['published_at']:
                                try:
                                    # Try to parse various date formats
                                    if isinstance(item['published_at'], str):
                                        # Assume it's already in ISO format or similar
                                        pass
                                    elif isinstance(item['published_at'], int):
                                        # Unix timestamp
                                        item['published_at'] = datetime.fromtimestamp(item['published_at']).isoformat()
                                except:
                                    item['published_at'] = None
                            
                            processed_items.append(item)
                        except Exception as e:
                            logger.exception(f"Error processing API item: {e}")
                            continue
                    
                    duration = time.time() - start_time
                    logger.info(f"API news fetch completed in {duration:.2f} seconds, processed {len(processed_items)} items")
                    return processed_items
                else:
                    duration = time.time() - start_time
                    logger.warning(f"API request failed after {duration:.2f} seconds: {response.status}")
                    return []
        
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"API fetch error after {duration:.2f} seconds: {e}")
        return []
