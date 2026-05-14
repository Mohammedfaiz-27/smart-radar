"""
Business logic for response generation and logging
"""
import os
import json
import logging
import traceback
from typing import Optional
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import pathlib
import aiohttp
import asyncio
from openai import AsyncOpenAI

# Load environment variables from .env file with explicit path
env_path = pathlib.Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup logging
logger = logging.getLogger(__name__)

from app.core.database import get_database
from app.models.response_log import ResponseLogCreate, ResponseLogResponse
from app.services.posts_table_service import PostsTableService

class ResponseService:
    def __init__(self):
        self._db = None
        self._collection = None
        self.post_service = PostsTableService()
        # Narrative service removed
        
        # Initialize OpenAI API (primary) and Gemini (fallback)
        openai_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"Debug: OPENAI_API_KEY loaded = {'Yes' if openai_key else 'No'}")
        
        if openai_key:
            self.openai_client = AsyncOpenAI(api_key=openai_key)
            logger.info("✅ OpenAI API configured successfully")
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        # Initialize Gemini as fallback
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        logger.info(f"Debug: GEMINI_API_KEY loaded = {'Yes' if gemini_key else 'No'}")
        
        if gemini_key:
            genai.configure(api_key=gemini_key)
            logger.info("✅ Gemini API configured as fallback")
            
            # Configure safety settings to be more permissive
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # Create model with enhanced configuration for better reliability
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash-lite',  # Use flash-lite for maximum speed
                safety_settings=safety_settings
            )
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not found in environment variables")
    
    pass

    async def generate_response(self,
                              original_post_id: str,
                              tone: str = "Professional",
                              language: str = "Tamil",
                              user_id: str = "default") -> dict:
        """Generate AI-powered strategic responses using Gemini 2.5 Pro"""
        
        # Initialize the service
        await self.post_service.initialize()
        
        # Get original post from posts_table
        logger.info(f"🔍 Looking for post ID: {original_post_id}")
        logger.info(f"🔍 Post ID type: {type(original_post_id)}")
        logger.info(f"🔍 Post ID length: {len(original_post_id)}")
        
        original_post = await self.post_service.get_post(original_post_id)
        logger.info(f"📊 Posts table result: {original_post is not None}")

        if not original_post:
            logger.error(f"❌ Post {original_post_id} not found")
            raise ValueError("Original post not found")

        # Generate response using Gemini REST API (primary) with OpenAI fallback
        try:
            response_options = await self._generate_gemini_rest_primary(original_post, tone, language)
            
            return {
                "option1": response_options.get("option1", ""),
                "option2": response_options.get("option2", ""),
                "option3": response_options.get("option3", ""),
                "original_post_id": original_post_id,
                "tone": tone,
                "language": language
            }
        except Exception as e:
            raise ValueError(f"Failed to generate response: {str(e)}")

    async def log_response(self,
                          original_post_id: str,
                          generated_text: str,
                          tone: str = "Professional",
                          language: str = "Tamil",
                          user_id: str = "default") -> ResponseLogResponse:
        """Log a generated response"""
        
        # Initialize the service
        await self.post_service.initialize()
        
        # Get original post from posts_table
        original_post = await self.post_service.get_post(original_post_id)
        if not original_post:
            raise ValueError("Original post not found")

        platform = getattr(original_post, 'platform', 'unknown')
        if hasattr(platform, 'value'):
            platform = platform.value

        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO response_logs
                    (original_post_id, source_platform, narrative_used_id,
                     generated_response_text, responded_by_user, responded_at)
                VALUES ($1,$2,$3,$4,$5,$6)
                RETURNING *
                """,
                original_post_id, str(platform), "",
                generated_text, user_id, datetime.utcnow(),
            )

        await self.post_service.mark_as_responded(original_post_id)
        return ResponseLogResponse(
            id=str(row["id"]),
            original_post_id=str(row["original_post_id"]),
            source_platform=row["source_platform"],
            narrative_used_id=row["narrative_used_id"] or "",
            generated_response_text=row["generated_response_text"],
            responded_by_user=row["responded_by_user"],
            responded_at=row["responded_at"],
        )

    async def _generate_ai_response(self, original_post, tone="Professional", language="Tamil") -> dict:
        """Generate AI response using Gemini 2.5 Pro with Election Commission Official Prompt"""

        # Extract post data - handle both object and dict post formats
        if isinstance(original_post, dict):
            post_platform = original_post.get('platform', 'Unknown')
            post_author = original_post.get('author_username', 'Unknown')
            post_content = original_post.get('post_text', '') or original_post.get('content', '')
            post_sentiment = original_post.get('sentiment_label', 'neutral')
            post_sentiment_score = original_post.get('sentiment_score', 0.0)
        else:
            post_platform = getattr(original_post, 'platform', 'Unknown')
            post_author = getattr(original_post, 'author_username', 'Unknown')
            post_content = getattr(original_post, 'post_text', '') or getattr(original_post, 'content', '')
            post_sentiment = getattr(original_post, 'sentiment', 'neutral')
            post_sentiment_score = getattr(original_post, 'sentiment_score', 0.0)

        # Construct the Election Commission Official Prompt
        prompt = f"""Persona
You are the official communication channel for the Election Commission of India, Tamil Nadu. Your voice is authoritative, impartial, and formal. Your primary objective is to disseminate accurate information, clarify electoral procedures, and ensure adherence to the Model Code of Conduct. You do not engage in political debates or take sides. Your communication is always factual, transparent, and in the public interest.

CRITICAL PRELIMINARY STEP: Information Verification
Before you draft a response, you MUST perform an internal information verification based on the post in question. Access your knowledge base for the following:
1. Identify the Core Issue: What is the central claim, question, or allegation in the post concerning the election process, a candidate's/party's action, or the ECI's conduct?
2. Consult Official ECI Records & Rules: Cross-reference the issue with the Representation of the People Act, 1951, the Model Code of Conduct (MCC), official ECI circulars, press releases, and historical electoral data.
3. Formulate a Factual Statement: Prepare a clear, neutral, and verifiable statement of fact based on the official rules and records that directly addresses the issue raised in the post.

Communication Protocol (You MUST use your verified information to execute this structure)
1. Official Opening: Begin with a formal and direct statement that acknowledges the subject matter without validating any misinformation (e.g., "It has come to the notice of the Election Commission...", "For the information of the public and all stakeholders...").
2. Factual Clarification: State the verified fact or the relevant rule from the ECI's regulations. Use precise, unambiguous, and official language. If applicable, cite the specific rule or section of the Model Code of Conduct.
3. Provide Context and Guidance: Briefly explain the regulation or process to ensure public understanding and transparency. Frame the information to educate the public on their rights and the responsibilities of political parties and candidates.
4. Concluding Directive: Conclude with a formal directive, a reminder to political parties and the public to uphold electoral laws, or a link to official ECI resources for further information. The conclusion should reinforce the ECI's commitment to free and fair elections.

Your Task
You are to draft a response to the following post. Generate three distinct response options adhering strictly to your Persona and the Communication Protocol, using the facts you have verified.

CONTEXT (The post to respond to):
Platform: {post_platform}
Author: {post_author}
Content: {post_content}

FINAL INSTRUCTIONS:
1. Your tone MUST be Professional and Governmental.
2. The language must be {language}, using formal, official terminology suitable for a government body.
3. Each response must be clear, concise, and suitable for an official public announcement. Do NOT use any emojis.
4. CRITICAL OUTPUT FORMAT: You MUST return ONLY a valid JSON object. No other text before or after. Example format:
{{"option1": "Response text here", "option2": "Response text here", "option3": "Response text here"}}
Do NOT use markdown formatting, do NOT use ```json```, just return the plain JSON object."""

        try:
            # Log the prompt being sent for debugging
            logger.info(f"=== GENERATING RESPONSE ===")
            post_id = original_post.get('id', 'Unknown') if isinstance(original_post, dict) else getattr(original_post, 'id', 'Unknown')
            logger.info(f"Post ID: {post_id}")
            logger.info(f"Tone: {tone}, Language: {language}")
            logger.info(f"Post Content: {post_content}")
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            # Call Gemini 2.5 Pro with retry logic for DNS issues
            logger.info("Calling Gemini 2.5 Pro API...")
            
            if not self.model:
                logger.error("Gemini model not initialized - missing API key")
                raise ValueError("Gemini API not configured")
            
            # Retry logic for DNS resolution issues with increased timeout
            max_retries = 3
            retry_delay = 2.0
            request_timeout = 60.0  # 60 second timeout per request
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Gemini API attempt {attempt + 1}/{max_retries} (timeout: {request_timeout}s)")
                    
                    # Use asyncio.wait_for to timeout individual requests quickly
                    import asyncio
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self.model.generate_content, prompt),
                        timeout=request_timeout
                    )
                    logger.info("Gemini API call successful")
                    break
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Gemini API attempt {attempt + 1} timed out after {request_timeout}s")
                    if attempt < max_retries - 1:
                        logger.info(f"Timeout detected, retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                        request_timeout *= 1.2  # Slightly increase timeout each attempt
                        continue
                    else:
                        logger.error("All Gemini API retry attempts failed due to timeouts")
                        raise asyncio.TimeoutError("Gemini API requests timed out after all retry attempts")
                        
                except Exception as api_error:
                    logger.warning(f"Gemini API attempt {attempt + 1} failed: {str(api_error)}")
                    
                    # Check if it's a DNS resolution error or timeout
                    if any(error_type in str(api_error).lower() for error_type in ["dns", "timeout", "connection", "network"]):
                        if attempt < max_retries - 1:
                            logger.info(f"Network/timeout issue detected, retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5  # Exponential backoff
                            continue
                        else:
                            logger.error("All Gemini API retry attempts failed due to network/timeout issues")
                            # Try direct REST API as fallback
                            logger.info("Attempting direct REST API fallback...")
                            try:
                                return await self._gemini_rest_api_fallback(prompt)
                            except Exception as rest_error:
                                logger.error(f"REST API fallback also failed: {rest_error}")
                                raise api_error
                    else:
                        # For other errors, try REST API fallback immediately
                        logger.info("Attempting direct REST API fallback for non-network error...")
                        try:
                            return await self._gemini_rest_api_fallback(prompt)
                        except Exception as rest_error:
                            logger.error(f"REST API fallback failed: {rest_error}")
                            raise api_error
            
            # Log raw response
            raw_response = response.text.strip()
            logger.info(f"Raw Gemini response: {raw_response}")
            
            # Parse JSON response
            response_text = raw_response
            
            # Clean up response text - handle various markdown formats
            original_text = response_text
            
            # Remove ```json``` blocks
            if response_text.startswith('```json') and response_text.endswith('```'):
                response_text = response_text[7:-3].strip()
                logger.info("Removed ```json``` formatting")
            # Remove ``` blocks
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text[3:-3].strip()
                logger.info("Removed ``` formatting")
            # Find JSON object within text
            elif '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                response_text = response_text[start:end]
                logger.info("Extracted JSON object from response text")
            
            # Remove any leading/trailing whitespace and newlines
            response_text = response_text.strip()
            
            logger.info(f"Cleaned response text: {response_text}")
            
            # Parse JSON
            response_json = json.loads(response_text)
            logger.info(f"Successfully parsed JSON: {response_json}")
            
            # Validate that we have the required keys
            if not all(key in response_json for key in ["option1", "option2", "option3"]):
                logger.error(f"Missing required keys in response: {list(response_json.keys())}")
                raise ValueError("Invalid response format from AI")
            
            logger.info("=== RESPONSE GENERATION SUCCESSFUL ===")
            return response_json
            
        except json.JSONDecodeError as e:
            # Fallback responses if JSON parsing fails
            logger.error(f"=== JSON DECODE ERROR ===")
            logger.error(f"Error: {str(e)}")
            logger.error(f"Raw response that failed to parse: {raw_response if 'raw_response' in locals() else 'No response captured'}")
            logger.warning("Using Tamil fallback responses due to JSON parse failure")
            
            if language.lower() == 'tamil':
                return {
                    "option1": "உங்கள் கருத்தைப் பகிர்ந்ததற்கு நன்றி. எங்கள் கட்சி 75 ஆண்டுகளாக உண்மையான வேலையுடன் மக்களுக்கு சேவை செய்து வருகிறது, வெற்று வாக்குறுதிகளுடன் அல்ல.",
                    "option2": "ஆட்சி பற்றி பேசுபவர் யார் - முதலில் ஒரு தேர்தலில் வெற்றி பெறுங்கள், பின்னர் இந்த உரையாடலை நாம் நடத்தலாம்.",
                    "option3": "நீங்கள் சமூக ஊடக நாடகத்தில் பிஸியாக இருக்கும்போது, எங்கள் அமைச்சர்கள் மக்கள் நலனுக்காக இரவு பகல் உழைத்துக் கொண்டிருக்கிறார்கள்."
                }
            else:
                return {
                    "option1": "Thank you for sharing your perspective. Our party has been serving the people for 75 years with real work, not empty promises.",
                    "option2": "Look who's talking about governance - win an election first, then we can have this conversation.",
                    "option3": "While you're busy with social media drama, our ministers are working day and night for the people's welfare."
                }
        except Exception as e:
            # Final fallback with detailed error logging
            import traceback
            logger.error(f"=== GENERAL EXCEPTION ===")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            logger.error(f"Exception args: {e.args if hasattr(e, 'args') else 'No args'}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            post_id = original_post.get('id', 'Unknown') if isinstance(original_post, dict) else getattr(original_post, 'id', 'Unknown')
            logger.error(f"Post ID being processed: {post_id}")
            logger.error(f"Post content being processed: {post_content}")
            logger.warning("Using intelligent fallback responses based on post content")
            
            # Generate context-aware fallback responses based on post content
            fallback_responses = self._generate_intelligent_fallback(post_content, tone, language)
            return fallback_responses

    async def _get_cluster_name(self, cluster_id: str) -> str:
        """Fetch cluster name from database to use as organization context."""
        try:
            pool = get_database()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT name FROM clusters WHERE id = $1::uuid", cluster_id
                )
            return row["name"] if row else ""
        except Exception:
            return ""

    async def _generate_gemini_rest_primary(self, original_post, tone="Professional", language="Tamil") -> dict:
        """Generate AI response using Gemini REST API (primary method) with OpenAI fallback"""

        # Extract post data
        if isinstance(original_post, dict):
            post_platform = original_post.get('platform', 'Unknown')
            post_author = original_post.get('author_username', 'Unknown')
            post_content = original_post.get('post_text', '') or original_post.get('content', '')
            cluster_id = original_post.get('cluster_id', '')
        else:
            post_platform = getattr(original_post, 'platform', 'Unknown')
            if hasattr(post_platform, 'value'):
                post_platform = post_platform.value
            post_author = getattr(original_post, 'author_username', 'Unknown')
            post_content = getattr(original_post, 'post_text', '') or getattr(original_post, 'content', '')
            cluster_id = str(getattr(original_post, 'cluster_id', '') or '')

        # Get organization name from cluster
        org_name = await self._get_cluster_name(cluster_id) if cluster_id else ""

        # Build tone instruction
        tone_map = {
            "professional": "formal, measured, and authoritative — acknowledge concerns directly and offer a clear resolution path",
            "empathetic": "warm, understanding, and human — show genuine care and commit to resolving the issue",
            "assertive": "confident and direct — stand by the brand while addressing the concern firmly",
            "apologetic": "sincere and remorseful — take ownership of the issue and promise concrete action",
            "informative": "helpful and factual — provide clear information and next steps to resolve the issue",
        }
        tone_instruction = tone_map.get(tone.lower().split()[0], tone_map["professional"])

        org_context = f"You represent **{org_name}**. " if org_name else "You represent the organization being mentioned. "

        prompt = f"""You are a social media manager responding to a post on behalf of your organization.

{org_context}Your job is to craft a response that is relevant, genuine, and directly addresses the specific content of the post below.

POST DETAILS:
Platform: {post_platform}
Author: @{post_author}
Post Content: {post_content}

RESPONSE REQUIREMENTS:
1. Read the post carefully and understand EXACTLY what the person is saying, asking, or complaining about.
2. Your response must directly address the specific issue raised in this post — do NOT give a generic reply.
3. Tone: Be {tone_instruction}.
4. Language: Write entirely in {language}.
5. Keep each response concise (2-4 sentences), suitable for a social media reply.
6. Do NOT use emojis.
7. Generate 3 distinct response options — each should approach the issue differently (e.g., one focused on empathy, one on resolution, one on information).

CRITICAL OUTPUT FORMAT: Return ONLY a valid JSON object, no other text:
{{"option1": "response text", "option2": "response text", "option3": "response text"}}"""

        post_id = original_post.get('id', 'Unknown') if isinstance(original_post, dict) else getattr(original_post, 'id', 'Unknown')
        logger.info(f"=== GENERATING RESPONSE (GEMINI REST PRIMARY) ===")
        logger.info(f"Post ID: {post_id}, Org: {org_name}, Tone: {tone}, Language: {language}")
        logger.info(f"Post Content: {post_content}")

        try:
            logger.info("🔄 Attempting Gemini REST API (primary method)...")
            return await self._gemini_rest_api_direct(prompt)
        except Exception as gemini_error:
            logger.warning(f"Gemini REST API failed: {gemini_error}")
            logger.info("🔄 Falling back to OpenAI API...")
            try:
                return await self._generate_openai_response(original_post, tone, language)
            except Exception as openai_error:
                logger.error(f"OpenAI API also failed: {openai_error}")
                return self._generate_intelligent_fallback(post_content, tone, language)

    async def _gemini_rest_api_direct(self, prompt: str) -> dict:
        """
        Direct REST API call to Gemini using aiohttp (network-friendly approach)
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found for REST API")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "topP": 0.95,
                "topK": 20,
                "maxOutputTokens": 1024
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }

        logger.info("Making direct Gemini REST API call...")

        timeout = aiohttp.ClientTimeout(total=15)  # 15 second timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract text from response
                        if 'candidates' in data and len(data['candidates']) > 0:
                            candidate = data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                raw_text = candidate['content']['parts'][0]['text'].strip()
                                logger.info(f"Gemini REST raw response: {raw_text}")
                                
                                # Parse JSON response
                                response_text = raw_text
                                
                                # Clean up response text - handle various markdown formats
                                if response_text.startswith('```json') and response_text.endswith('```'):
                                    response_text = response_text[7:-3].strip()
                                elif response_text.startswith('```') and response_text.endswith('```'):
                                    response_text = response_text[3:-3].strip()
                                elif '{' in response_text and '}' in response_text:
                                    start = response_text.find('{')
                                    end = response_text.rfind('}') + 1
                                    response_text = response_text[start:end]
                                
                                response_text = response_text.strip()
                                logger.info(f"Cleaned Gemini response: {response_text}")
                                
                                # Parse JSON
                                response_json = json.loads(response_text)
                                
                                # Validate that we have the required keys
                                if not all(key in response_json for key in ["option1", "option2", "option3"]):
                                    logger.error(f"Missing required keys in Gemini REST response: {list(response_json.keys())}")
                                    raise ValueError("Invalid response format from Gemini REST API")
                                
                                logger.info("✅ Gemini REST API call successful!")
                                return response_json
                            else:
                                raise ValueError("No content in Gemini REST API response")
                        else:
                            raise ValueError("No candidates in Gemini REST API response")
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini REST API error {response.status}: {error_text}")
                        raise ValueError(f"Gemini REST API returned status {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("Gemini REST API call timed out")
            raise ValueError("Gemini REST API timeout")
        except json.JSONDecodeError as e:
            logger.error(f"Gemini REST API JSON parse error: {e}")
            raise ValueError(f"Gemini REST API JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Gemini REST API call failed: {e}")
            raise ValueError(f"Gemini REST API call failed: {e}")

    async def _generate_openai_response(self, original_post, tone="Professional", language="Tamil") -> dict:
        """Generate AI response using OpenAI API (fallback method)"""

        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        # Extract post data
        if isinstance(original_post, dict):
            post_platform = original_post.get('platform', 'Unknown')
            post_author = original_post.get('author_username', 'Unknown')
            post_content = original_post.get('post_text', '') or original_post.get('content', '')
            cluster_id = original_post.get('cluster_id', '')
        else:
            post_platform = getattr(original_post, 'platform', 'Unknown')
            if hasattr(post_platform, 'value'):
                post_platform = post_platform.value
            post_author = getattr(original_post, 'author_username', 'Unknown')
            post_content = getattr(original_post, 'post_text', '') or getattr(original_post, 'content', '')
            cluster_id = str(getattr(original_post, 'cluster_id', '') or '')

        org_name = await self._get_cluster_name(cluster_id) if cluster_id else ""
        org_context = f"You represent **{org_name}**. " if org_name else "You represent the organization being mentioned. "

        tone_map = {
            "professional": "formal, measured, and authoritative",
            "empathetic": "warm, understanding, and human",
            "assertive": "confident and direct",
            "apologetic": "sincere and remorseful",
            "informative": "helpful and factual",
        }
        tone_instruction = tone_map.get(tone.lower().split()[0], tone_map["professional"])

        prompt = f"""You are a social media manager responding to a post on behalf of your organization.

{org_context}Craft a response that directly addresses what this specific post says.

POST DETAILS:
Platform: {post_platform}
Author: @{post_author}
Post Content: {post_content}

RESPONSE REQUIREMENTS:
1. Directly address the specific issue in this post — no generic replies.
2. Tone: Be {tone_instruction}.
3. Language: Write entirely in {language}.
4. Keep each response concise (2-4 sentences), suitable for a social media reply.
5. No emojis. Generate 3 distinct response options.

Return ONLY valid JSON:
{{"option1": "response text", "option2": "response text", "option3": "response text"}}"""

        post_id = original_post.get('id', 'Unknown') if isinstance(original_post, dict) else getattr(original_post, 'id', 'Unknown')
        logger.info(f"=== GENERATING RESPONSE (OPENAI) === Post: {post_id}, Org: {org_name}")

        try:
            logger.info("🔄 Calling OpenAI API...")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 Omni for better quality
                messages=[
                    {"role": "system", "content": "You are the official Election Commission of India, Tamil Nadu. Return only valid JSON as specified."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000,
                timeout=15.0  # 15 second timeout
            )
            
            raw_response = response.choices[0].message.content.strip()
            logger.info(f"Raw OpenAI response: {raw_response}")
            
            # Parse JSON response
            response_text = raw_response
            
            # Clean up response text - handle various markdown formats
            if response_text.startswith('```json') and response_text.endswith('```'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text[3:-3].strip()
            elif '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                response_text = response_text[start:end]
            
            response_text = response_text.strip()
            logger.info(f"Cleaned response text: {response_text}")
            
            # Parse JSON
            response_json = json.loads(response_text)
            
            # Validate that we have the required keys
            if not all(key in response_json for key in ["option1", "option2", "option3"]):
                logger.error(f"Missing required keys in OpenAI response: {list(response_json.keys())}")
                raise ValueError("Invalid response format from OpenAI")
            
            logger.info("✅ OpenAI response generation successful!")
            return response_json
            
        except Exception as e:
            logger.error(f"OpenAI API failed: {e}")
            logger.info("🔄 Falling back to Gemini REST API...")
            
            # Fallback to Gemini
            try:
                return await self._generate_ai_response_rest_first(original_post, tone, language)
            except Exception as fallback_error:
                logger.error(f"All AI APIs failed: {fallback_error}")
                logger.warning("Using intelligent fallback responses")
                return self._generate_intelligent_fallback(post_content, tone, language)

    async def _generate_ai_response_rest_first(self, original_post, tone="Sarcastic", language="Tamil") -> dict:
        """Generate AI response using REST API first, then fallback to Python library if needed"""
        
        # Extract post data - handle both object and dict post formats
        if isinstance(original_post, dict):
            post_platform = original_post.get('platform', 'Unknown')
            post_author = original_post.get('author_username', 'Unknown')
            post_content = original_post.get('post_text', '') or original_post.get('content', '')
            post_sentiment = original_post.get('sentiment_label', 'neutral')
            post_sentiment_score = original_post.get('sentiment_score', 0.0)
        else:
            post_platform = getattr(original_post, 'platform', 'Unknown')
            post_author = getattr(original_post, 'author_username', 'Unknown')
            post_content = getattr(original_post, 'post_text', '') or getattr(original_post, 'content', '')
            post_sentiment = getattr(original_post, 'sentiment', 'neutral')
            post_sentiment_score = getattr(original_post, 'sentiment_score', 0.0)
        
        # Construct the Master Strategist Prompt v17.0
        prompt = f"""
Persona
You are the official communication channel for the Election Commission of India, Tamil Nadu. Your voice is authoritative, impartial, and formal. Your primary objective is to disseminate accurate information, clarify electoral procedures, and ensure adherence to the Model Code of Conduct. You do not engage in political debates or take sides. Your communication is always factual, transparent, and in the public interest.
CRITICAL PRELIMINARY STEP: Information Verification
Before you draft a response, you MUST perform an internal information verification based on the post in question. Access your knowledge base for the following:
Identify the Core Issue: What is the central claim, question, or allegation in the post concerning the election process, a candidate's/party's action, or the ECI's conduct?
Consult Official ECI Records & Rules: Cross-reference the issue with the Representation of the People Act, 1951, the Model Code of Conduct (MCC), official ECI circulars, press releases, and historical electoral data.
Formulate a Factual Statement: Prepare a clear, neutral, and verifiable statement of fact based on the official rules and records that directly addresses the issue raised in the post.
Communication Protocol (You MUST use your verified information to execute this structure)
Official Opening: Begin with a formal and direct statement that acknowledges the subject matter without validating any misinformation (e.g., "It has come to the notice of the Election Commission...", "For the information of the public and all stakeholders...").
Factual Clarification: State the verified fact or the relevant rule from the ECI's regulations. Use precise, unambiguous, and official language. If applicable, cite the specific rule or section of the Model Code of Conduct.
Provide Context and Guidance: Briefly explain the regulation or process to ensure public understanding and transparency. Frame the information to educate the public on their rights and the responsibilities of political parties and candidates.
Concluding Directive: Conclude with a formal directive, a reminder to political parties and the public to uphold electoral laws, or a link to official ECI resources for further information. The conclusion should reinforce the ECI's commitment to free and fair elections.
Your Task
You are to draft a response to the following post. Generate three distinct response options adhering strictly to your Persona and the Communication Protocol, using the facts you have verified.
CONTEXT (The post to respond to):
Platform: {post_platform}
Author: {post_author}
Content: {post_content}
FINAL INSTRUCTIONS:
Your tone MUST be Professional and Governmental.
The language must be {language}, using formal, official terminology suitable for a government body.
Each response must be clear, concise, and suitable for an official public announcement. Do NOT use any emojis.
CRITICAL OUTPUT FORMAT: You MUST return ONLY a valid JSON object. No other text before or after. Example format:
{{"option1": "Response text here", "option2": "Response text here", "option3": "Response text here"}}
Do NOT use markdown formatting, do NOT use json, just return the plain JSON object."""

        post_id = original_post.get('id', 'Unknown') if isinstance(original_post, dict) else getattr(original_post, 'id', 'Unknown')
        logger.info(f"=== GENERATING RESPONSE (REST API FIRST) ===")
        logger.info(f"Post ID: {post_id}")
        logger.info(f"Tone: {tone}, Language: {language}")
        logger.info(f"Post Content: {post_content}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        # Try REST API first
        try:
            logger.info("🔄 Attempting Gemini REST API (primary method)...")
            return await self._gemini_rest_api_fallback(prompt)
        except Exception as rest_error:
            logger.warning(f"REST API failed: {rest_error}")
            logger.info("🔄 Falling back to Python library...")
            
            # Fallback to Python library
            try:
                return await self._generate_ai_response(original_post, tone, language)
            except Exception as lib_error:
                logger.error(f"Python library also failed: {lib_error}")
                logger.warning("Using intelligent fallback responses")
                return self._generate_intelligent_fallback(post_content, tone, language)

    async def _gemini_rest_api_fallback(self, prompt: str) -> dict:
        """
        Direct REST API call to Gemini when the Python library fails
        """
        import aiohttp
        import asyncio
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found for REST API fallback")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ],
            "generationConfig": {
                "temperature": 0.8,
                "topK": 20,
                "topP": 0.95,
                "maxOutputTokens": 1024
            }
        }

        logger.info("Making direct REST API call to Gemini...")

        timeout = aiohttp.ClientTimeout(total=20)  # 20 second timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract text from response
                        if 'candidates' in data and len(data['candidates']) > 0:
                            candidate = data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                raw_text = candidate['content']['parts'][0]['text'].strip()
                                logger.info(f"REST API raw response: {raw_text}")
                                
                                # Parse JSON response same as before
                                response_text = raw_text
                                
                                # Clean up response text - handle various markdown formats
                                if response_text.startswith('```json') and response_text.endswith('```'):
                                    response_text = response_text[7:-3].strip()
                                elif response_text.startswith('```') and response_text.endswith('```'):
                                    response_text = response_text[3:-3].strip()
                                elif '{' in response_text and '}' in response_text:
                                    start = response_text.find('{')
                                    end = response_text.rfind('}') + 1
                                    response_text = response_text[start:end]
                                
                                response_text = response_text.strip()
                                
                                # Parse JSON
                                import json
                                response_json = json.loads(response_text)
                                
                                # Validate that we have the required keys
                                if not all(key in response_json for key in ["option1", "option2", "option3"]):
                                    logger.error(f"Missing required keys in REST API response: {list(response_json.keys())}")
                                    raise ValueError("Invalid response format from REST API")
                                
                                logger.info("✅ REST API call successful!")
                                return response_json
                            else:
                                raise ValueError("No content in REST API response")
                        else:
                            raise ValueError("No candidates in REST API response")
                    else:
                        error_text = await response.text()
                        logger.error(f"REST API error {response.status}: {error_text}")
                        raise ValueError(f"REST API returned status {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("REST API call timed out")
            raise ValueError("REST API timeout")
        except json.JSONDecodeError as e:
            logger.error(f"REST API JSON parse error: {e}")
            raise ValueError(f"REST API JSON parse error: {e}")
        except Exception as e:
            logger.error(f"REST API call failed: {e}")
            raise ValueError(f"REST API call failed: {e}")

    def _generate_intelligent_fallback(self, post_content: str, tone: str, language: str) -> dict:
        """Fallback responses when AI APIs are unavailable — generic acknowledgements only."""
        content_preview = (post_content or "")[:120]
        if language.lower() == 'tamil':
            return {
                "option1": f"உங்கள் கருத்தை பகிர்ந்ததற்கு நன்றி. இந்த விஷயத்தை நாங்கள் கவனத்தில் எடுத்துக்கொள்கிறோம்.",
                "option2": f"உங்கள் அனுபவம் பற்றி அறிந்ததில் வருந்துகிறோம். விரைவில் தொடர்பு கொள்கிறோம்.",
                "option3": f"உங்கள் கோரிக்கை பதிவு செய்யப்பட்டுள்ளது. சிறந்த சேவை அளிக்க முயல்வோம்.",
            }
        else:
            return {
                "option1": "Thank you for reaching out. We've noted your concern and will look into this promptly.",
                "option2": "We're sorry to hear about your experience. Our team will get in touch with you shortly.",
                "option3": "Your feedback has been registered. We're committed to resolving this for you.",
            }

