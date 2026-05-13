#!/usr/bin/env python3
"""
Content Adaptation Service
Handles channel-specific content customization using LLM (Gemini Flash by default) for efficient batch processing.
Groups up to 10 channels at once to optimize API calls and reduce processing time.
Supports both Gemini and GPT models with configurable provider selection.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from uuid import UUID
from services.llm_service import llm_service, LLMProvider, LLMProfile
from config.tone_characteristics import get_tone_characteristics
from utils.tamil_text_cleaner import safe_clean_tamil_content, has_orphaned_tamil_marks

logger = logging.getLogger(__name__)

@dataclass
class ChannelConfig:
    """Channel configuration for content adaptation"""
    id: str
    platform: str
    account_name: str
    content_tone: str
    custom_instructions: Optional[str] = None
    has_image: bool = False  # Whether newscard will have an image (affects content length)
    
@dataclass
class ContentAdaptation:
    """Adapted content for a specific channel"""
    channel_id: str
    adapted_content: str
    hashtags: List[str]
    success: bool
    headline: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class BatchAdaptationResult:
    """Result of batch content adaptation"""
    adaptations: List[ContentAdaptation]
    total_channels: int
    success_count: int
    failure_count: int
    processing_time: float

def normalize_tamil_transliteration(text: str) -> str:
    """
    Normalize common Tamil transliteration variations to a standard form.
    Handles variations like: thi/ti, dhu/du, kha/ka, etc.
    """
    text = text.lower().strip()

    # Common Tamil transliteration variations (normalize to shorter form)
    replacements = {
        'thi': 'ti',
        'dhi': 'di',
        'kha': 'ka',
        'gha': 'ga',
        'bha': 'ba',
        'dha': 'da',
        'tha': 'ta',  # Note: 'tha' is different from 'ta' in Tamil, but LLMs often confuse them
    }

    for variant, standard in replacements.items():
        text = text.replace(variant, standard)

    return text

def fuzzy_match_channel_name(llm_name: str, available_names: List[str]) -> Optional[str]:
    """
    Find the best matching channel name using fuzzy matching for Tamil transliterations.
    Returns the matched name from available_names, or None if no match found.
    """
    normalized_llm = normalize_tamil_transliteration(llm_name)

    # Try exact match first (after normalization)
    for name in available_names:
        if normalize_tamil_transliteration(name) == normalized_llm:
            return name

    # Try substring match (in case of extra prefixes/suffixes)
    for name in available_names:
        norm_name = normalize_tamil_transliteration(name)
        if norm_name in normalized_llm or normalized_llm in norm_name:
            # Check if it's a significant match (>80% overlap)
            overlap = min(len(norm_name), len(normalized_llm))
            max_len = max(len(norm_name), len(normalized_llm))
            if overlap / max_len > 0.8:
                return name

    return None

class ContentAdaptationService:
    """Service for adapting content to different channel styles using LLM (Gemini by default)"""

    def __init__(self):
        """Initialize content adaptation service with LLM support"""
        # Use shared llm_service which defaults to Gemini Flash
        pass

    async def adapt_content_batch(
        self,
        original_content: str,
        channels: List[ChannelConfig],
        max_batch_size: int = 10,
        provider: Optional[LLMProvider] = None,
        include_headline: bool = False,
        extract_district: bool = False
    ) -> Tuple[List[BatchAdaptationResult], Optional[str]]:
        """
        Adapt content for multiple channels in batches

        Args:
            original_content: The original content to adapt
            channels: List of channel configurations
            max_batch_size: Maximum channels to process in one batch
            provider: LLM provider to use (None = default to Gemini Flash)
            include_headline: Whether to generate headlines (30-50 chars) for newscard templates
            extract_district: Whether to extract district/city name from content (only used once)

        Returns:
            Tuple of (List of batch adaptation results, extracted district or None)
        """
        # Check if LLM service is available (will check Gemini by default)
        if provider == LLMProvider.GEMINI or provider is None:
            # For Gemini, we don't need profile check - it's created on demand
            pass
        elif not llm_service.is_available(LLMProfile.DEFAULT):
            logger.error("LLM service not available")
            return []
            
        if not channels:
            logger.warning("No channels provided for content adaptation")
            return []
            
        # If content is empty, return empty adaptations without AI processing
        if not original_content or not original_content.strip():
            logger.info("Original content is empty, returning empty adaptations")

            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content="",
                    hashtags=[],
                    success=True,
                    headline=None,
                    error_message=None
                )
                for channel in channels
            ]
            
            return ([BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=len(channels),
                failure_count=0,
                processing_time=0.0
            )], None)

        results = []
        extracted_district = None

        # Process channels in batches
        for i in range(0, len(channels), max_batch_size):
            batch = channels[i:i + max_batch_size]
            # Only extract district in first batch
            should_extract_district = extract_district and i == 0
            batch_result, district = await self._process_batch(
                original_content,
                batch,
                provider=provider,
                include_headline=include_headline,
                extract_district=should_extract_district
            )
            results.append(batch_result)

            # Capture district from first batch
            if district and not extracted_district:
                extracted_district = district

            # Small delay between batches to avoid rate limiting
            if i + max_batch_size < len(channels):
                await asyncio.sleep(1)

        return (results, extracted_district)

    async def adapt_content_multi_page_news(
        self,
        original_content: str,
        channels: List[ChannelConfig],
        provider: Optional[LLMProvider] = None,
        include_headline: bool = True,
        extract_district: bool = False,
        batch_size: int = 20,
        source_image_url: Optional[str] = None
    ) -> Tuple[List[BatchAdaptationResult], Optional[str]]:
        """
        Adapt news content for multiple channels using Tamil multi-page news prompt.
        Processes channels in batches for optimal performance and quality.

        Args:
            original_content: The original news content to adapt
            channels: List of channel configurations
            provider: LLM provider to use (None = default to Gemini Flash)
            include_headline: Whether to generate headlines (30-50 chars) for newscard templates
            extract_district: Whether to extract district/city name from content
            batch_size: Number of accounts to process per LLM call (default: 20)
            source_image_url: Optional image URL for vision-enabled LLM (repost flow only)

        Returns:
            Tuple of (List of batch adaptation results, extracted district or None)
        """
        # Check if LLM service is available
        if provider == LLMProvider.GEMINI or provider is None:
            pass  # Gemini created on demand
        elif not llm_service.is_available(LLMProfile.DEFAULT):
            logger.error("LLM service not available")
            return ([], None)

        if not channels:
            logger.warning("No channels provided for content adaptation")
            return ([], None)

        # If content is empty, return empty adaptations without AI processing
        if not original_content or not original_content.strip():
            logger.info("Original content is empty, returning empty adaptations")
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content="",
                    hashtags=[],
                    success=True,
                    headline=None,
                    error_message=None
                )
                for channel in channels
            ]
            return ([BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=len(channels),
                failure_count=0,
                processing_time=0.0
            )], None)

        # Process channels in batches
        total_channels = len(channels)
        num_batches = (total_channels + batch_size - 1) // batch_size
        logger.info(f"Processing {total_channels} channels in {num_batches} batch(es) of up to {batch_size} accounts each")

        results = []
        extracted_district = None

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_channels)
            batch_channels = channels[start_idx:end_idx]

            logger.info(f"Processing batch {batch_idx + 1}/{num_batches}: {len(batch_channels)} channels")

            # IMPORTANT: Extract district only in FIRST batch
            # District extraction is CONTENT-ORIENTED (what district is the news about),
            # not account-oriented. We only need to extract it ONCE from the content,
            # regardless of how many batches we have.
            should_extract_district = extract_district and batch_idx == 0

            # Process this batch
            batch_result, district = await self._process_multi_page_batch(
                original_content=original_content,
                channels=batch_channels,
                provider=provider,
                include_headline=include_headline,
                extract_district=should_extract_district,
                source_image_url=source_image_url
            )

            results.append(batch_result)

            # Capture district from first batch
            if district and not extracted_district:
                extracted_district = district

            # Small delay between batches to avoid rate limiting
            if batch_idx + 1 < num_batches:
                await asyncio.sleep(1)

        logger.info(f"Multi-page news adaptation complete: {len(results)} batch(es) processed")
        return (results, extracted_district)

    async def _process_multi_page_batch(
        self,
        original_content: str,
        channels: List[ChannelConfig],
        provider: Optional[LLMProvider] = None,
        include_headline: bool = True,
        extract_district: bool = False,
        source_image_url: Optional[str] = None
    ) -> Tuple[BatchAdaptationResult, Optional[str]]:
        """
        Process a single batch of channels using multi-page news prompt.

        Args:
            extract_district: If True, the LLM prompt will include district extraction instructions.
                             District is CONTENT-ORIENTED (what district is the news about),
                             not account-oriented. Should only be True for the first batch.
            source_image_url: Optional image URL for vision-enabled LLM processing
        """
        start_time = datetime.now()

        try:
            # Build account metadata from ChannelConfig objects
            # IMPORTANT: Deduplicate by account_name since one account_name can be used
            # on multiple platforms (e.g., "krishnagiriseithigal" on Instagram, Facebook, WhatsApp)
            seen_account_names = set()
            accounts = []
            for channel in channels:
                # Skip if we've already added this account_name
                cleaned_account_name = channel.account_name.replace(" ", "").lower().strip()
                if cleaned_account_name in seen_account_names:
                    continue

                seen_account_names.add(cleaned_account_name)
                account = {
                    "id": channel.id,
                    "name": cleaned_account_name,
                    "platform": channel.platform,
                    "tone": channel.content_tone or "professional",
                    "custom_instructions": channel.custom_instructions
                }
                accounts.append(account)

            logger.info(f"Deduplicated {len(channels)} channels to {len(accounts)} unique account names")

            # Import Prompts to use get_multi_page_news_messages
            from config.prompts import Prompts

            # Get the multi-page news messages with optional district extraction and image analysis
            # NOTE: District extraction is CONTENT-ORIENTED (what district is the news about),
            # not account-oriented. We only need to extract it once, from the first batch.
            messages = Prompts.get_multi_page_news_messages(
                raw_content=original_content,
                accounts=accounts,
                extract_district=extract_district,  # Pass flag to modify prompt
                has_image=bool(source_image_url)  # Indicate if image is present for vision analysis
            )

            # Call LLM API (single call for this batch)
            response = await self._call_llm_api_for_multi_page(messages, provider=provider, image_url=source_image_url)

            # Parse the response in multi-page format
            # If extract_district=True: {District: "...", Pages: [{Page, HL, Cnt, Tags}]}
            # If extract_district=False: [{Page, HL, Cnt, Tags}]
            adaptations, district = self._parse_multi_page_response(
                response,
                channels,
                extract_district=extract_district
            )

            processing_time = (datetime.now() - start_time).total_seconds()
            success_count = sum(1 for a in adaptations if a.success)
            failure_count = len(adaptations) - success_count

            logger.info(f"Batch processing complete: {success_count}/{len(channels)} successful in {processing_time:.2f}s")

            return (BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=success_count,
                failure_count=failure_count,
                processing_time=processing_time
            ), district)

        except Exception as e:
            logger.exception(f"Multi-page batch processing failed: {e}")

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content=original_content,  # Fallback to original
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message=str(e)
                )
                for channel in channels
            ]

            processing_time = (datetime.now() - start_time).total_seconds()

            return (BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=0,
                failure_count=len(channels),
                processing_time=processing_time
            ), None)

    async def _process_batch(
        self,
        original_content: str,
        channels: List[ChannelConfig],
        provider: Optional[LLMProvider] = None,
        include_headline: bool = False,
        extract_district: bool = False
    ) -> Tuple[BatchAdaptationResult, Optional[str]]:
        """Process a single batch of channels"""
        start_time = datetime.now()

        try:
            # Create the prompt for batch processing
            prompt = self._create_batch_prompt(original_content, channels, include_headline=include_headline, extract_district=extract_district)

            # Call LLM API (defaults to Gemini Flash)
            response = await self._call_llm_api(prompt, provider=provider)

            # Parse the response
            adaptations, district = self._parse_batch_response(response, channels, extract_district=extract_district)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            success_count = sum(1 for a in adaptations if a.success)
            failure_count = len(adaptations) - success_count

            logger.info(f"Batch processing complete: {success_count}/{len(channels)} successful")

            return (BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=success_count,
                failure_count=failure_count,
                processing_time=processing_time
            ), district)
            
        except Exception as e:
            logger.exception(f"Batch processing failed: {e}")

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content=original_content,  # Fallback to original
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message=str(e)
                )
                for channel in channels
            ]

            processing_time = (datetime.now() - start_time).total_seconds()

            return (BatchAdaptationResult(
                adaptations=adaptations,
                total_channels=len(channels),
                success_count=0,
                failure_count=len(channels),
                processing_time=processing_time
            ), None)

    def _create_batch_prompt(self, original_content: str, channels: List[ChannelConfig], include_headline: bool = False, extract_district: bool = False) -> str:
        """Create a prompt for batch processing multiple channels"""

        # - Custom Instructions: {channel.custom_instructions or 'None'}
        channel_specs = []
        for i, channel in enumerate(channels, 1):
            # Get tone characteristics for rich context
            tone_chars = get_tone_characteristics(channel.content_tone)

            # Add content length restriction for templates with images
            length_instruction = ""
            if channel.has_image:
                length_instruction = "- IMPORTANT: Keep content under 250 characters (newscard has image, limited text space)"

            spec = f"""
Channel {i} (ID: {channel.id}):
- Platform: {channel.platform}
- Account: {channel.account_name}
- Tone: {channel.content_tone}
- Tone Description: {tone_chars.get('description', '')}
- Style Guidelines: {tone_chars.get('style_guidelines', '')}
- Key Words to Use: {', '.join(tone_chars.get('keywords', [])[:5])}
- Emoji Usage: {tone_chars.get('emoji_usage', 'moderate')}
{f"- Custom Instructions: {channel.custom_instructions}" if channel.custom_instructions else ""}
{length_instruction}

Custom instructions should be used as instructions and not to be taken as the content.

You should always respond in Tamil. Since the audience is Tamil speaking.
"""
            channel_specs.append(spec)
        
        prompt = f"""
You are a social media content adaptation expert. Adapt the following content for multiple social media channels, ensuring each adaptation matches the specific channel's tone and requirements.

**CRITICAL - TAMIL TEXT GENERATION RULES**:
Tamil is written with consonants (க, ச, ப, ம, etc.) followed by vowel signs (ா, ி, ு, ே, ை, ொ, etc.).

CORRECT Tamil structure:
- ப + ொ = பொ (consonant PA + vowel sign O)
- ம + ா = மா (consonant MA + vowel sign AA)
- Example words: பொன்னேரி, மாநகராட்சி, செயல்திறன்

WRONG - NEVER do this:
- ொன்னேரி (starts with orphaned vowel sign)
- ாநகராட்சி (starts with orphaned vowel sign)
- ெயல்திறன் (starts with orphaned vowel sign)

**Every Tamil word MUST start with a consonant, NEVER a vowel sign!**

Output Language: Tamil (தமிழ்)

ORIGINAL CONTENT:
{original_content}

CHANNELS TO ADAPT FOR:
{''.join(channel_specs)}

INSTRUCTIONS:
1. **FIRST AND FOREMOST**: Generate ONLY valid Tamil text
   - Every word starts with a consonant (க-ஹ range)
   - Vowel signs (ா, ி, ீ, ு, ூ, ெ, ே, ை, ொ, ோ, ௌ) come AFTER consonants
   - Double-check every Tamil word before including it

2. Adapt the content for each channel according to its specified tone characteristics
   - Use the tone description to understand the overall feel
   - Follow the style guidelines precisely
   - Incorporate the suggested keywords naturally
   - Apply appropriate emoji usage level (none/minimal/moderate/frequent/strategic)

3. Keep the core message intact while adjusting style, language, and presentation

4. Add appropriate hashtags for each platform (3-5 hashtags max)

5. Ensure content is suitable for the specific platform's audience and format

6. If custom instructions are provided, follow them carefully and prioritize them

7. Custom instructions should be used as instructions and not to be taken as the content

8. Content may contain Tamil Nadu cities and places. Use proper Tamil spelling:
   - Ponneri = பொன்னேரி (NOT ொன்னேரி)
   - Municipality = நகராட்சி or மாநகராட்சி (NOT ாநகராட்சி)
   - Efficiency = செயல்திறன் (NOT ெயல்திறன்)

9. The tone should be clearly reflected in word choice, sentence structure, and overall presentation{"" if not extract_district else '''

10. IMPORTANT: Extract the district or city name from the content
    - Identify the Tamil Nadu district or city mentioned in the content
    - Return ONLY the district/city name in Tamil
    - If no specific district/city is found, return: தமிழ்நாடு
    - Common districts: சென்னை, காஞ்சிபுரம், திருவள்ளூர், பொன்னேரி, etc.'''}{"" if not include_headline else f'''

{('11' if extract_district else '10')}. IMPORTANT: Generate a compelling headline for each channel (30-50 characters maximum)
    - Make it attention-grabbing and concise
    - Apply the same tone as the content adaptation
    - Follow custom instructions for style
    - Ensure it captures the essence of the news/content
    - **VERIFY**: Headline starts with Tamil consonant, not vowel sign'''}

**VALIDATION CHECKLIST** (verify before responding):
□ No Tamil word starts with vowel signs (ா, ி, ீ, ு, ூ, ெ, ே, ை, ொ, ோ, ௌ)
□ All Tamil words start with consonants (க, ச, ட, த, ப, ம, ய, ர, ல, வ, etc.)
□ Consonant + vowel sign order is correct throughout

RESPONSE FORMAT (JSON):
{{{"" if not extract_district else '''
  "district": "பொன்னேரி",  # Extracted district/city in Tamil, or தமிழ்நாடு if not found'''}
  "adaptations": [
    {{
      "channel_id": "channel_id_1",
      "adapted_content": "Content adapted for channel 1...",
      "hashtags": ["#tag1", "#tag2", "#tag3"]{"" if not include_headline else ''',
      "headline": "Short headline (30-50 chars)"'''}
    }},
    {{
      "channel_id": "channel_id_2",
      "adapted_content": "Content adapted for channel 2...",
      "hashtags": ["#tag1", "#tag2"]{"" if not include_headline else ''',
      "headline": "Short headline (30-50 chars)"'''}
    }}
  ]
}}

Please provide only the JSON response without any additional text.

Some of the place names in Tamil. Use these place names if they are present in the content:
Kavundampalayam - கவுண்டம்பாளையம்
Mettupalayam - மேட்டுப்பாளையம்
Kinathukadavu - கிணத்துக்கடவு
Pollachi - பொள்ளாச்சி
"""
        
        return prompt.strip()

    async def _call_llm_api(self, prompt: str, provider: Optional[LLMProvider] = None) -> str:
        """Make call to LLM API (defaults to Gemini Flash)"""
        try:
            # Enhanced system message with Tamil generation rules
            system_msg = """You are a social media content adaptation expert specializing in Tamil language.

**CRITICAL - TAMIL TEXT RULES**:
Tamil words MUST start with consonants (க, ச, ட, த, ப, ம, ய, ர, ல, வ, etc.).
NEVER start words with vowel signs (ா, ி, ீ, ு, ூ, ெ, ே, ை, ொ, ோ, ௌ).

✅ CORRECT: பொன்னேரி, மாநகராட்சி, செயல்திறன்
❌ WRONG: ொன்னேரி, ாநகராட்சி, ெயல்திறன்

For the given content, convert it to the tone and style of the channel. If same tone is given for all, randomize the outputs.
Always respond with valid JSON.
VERIFY all Tamil words start with consonants before responding."""

            response = await llm_service.generate(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                profile=LLMProfile.DEFAULT,
                provider=provider,  # None = uses default (Gemini Flash)
                temperature=0.7,
                max_tokens=3000,  # Increased from 2000 to allow longer content
                service_name="content_adaptation_service"
            )

            return response

        except Exception as e:
            logger.exception(f"LLM API call failed: {e}")
            raise

    def _parse_batch_response(
        self,
        response: str,
        channels: List[ChannelConfig],
        extract_district: bool = False
    ) -> Tuple[List[ContentAdaptation], Optional[str]]:
        """Parse the batch response from OpenAI"""
        adaptations = []
        district = None

        try:
            # Strip markdown code fences if present (```json ... ```)
            response_clean = response.strip()
            if response_clean.startswith('```'):
                # Remove opening fence (```json or ```)
                lines = response_clean.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove closing fence
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response_clean = '\n'.join(lines).strip()

            # Parse JSON response
            data = json.loads(response_clean)

            # Extract district if requested
            if extract_district and 'district' in data:
                district = data.get('district', '').strip()
                if district:
                    # Clean Tamil text in extracted district
                    district = safe_clean_tamil_content(district, "llm_extracted_district")
                    # Validate and fallback
                    if has_orphaned_tamil_marks(district) or len(district) > 50:
                        logger.warning(f"⚠️ LLM generated invalid district: {district}, using fallback")
                        district = "தமிழ்நாடு"
                    else:
                        logger.info(f"✓ Extracted district from content: {district}")
                else:
                    district = "தமிழ்நாடு"

            response_adaptations = data.get('adaptations', [])
            
            # Create a mapping for quick lookup
            response_map = {
                item['channel_id']: item 
                for item in response_adaptations
            }
            
            # Create adaptation objects for each channel
            for channel in channels:
                if channel.id in response_map:
                    item = response_map[channel.id]
                    # Clean Tamil text in LLM-generated content
                    adapted_content = item.get('adapted_content', '')
                    headline = item.get('headline')

                    if adapted_content:
                        adapted_content = safe_clean_tamil_content(adapted_content, f"llm_adapted_content_{channel.id}")

                        # Check for Tamil corruption
                        if has_orphaned_tamil_marks(adapted_content):
                            logger.warning(f"⚠️ LLM generated corrupted Tamil content for channel {channel.id}")
                            # Mark as failed so it can be retried
                            adaptation = ContentAdaptation(
                                channel_id=channel.id,
                                adapted_content='',
                                hashtags=[],
                                success=False,
                                headline=None,
                                error_message="Tamil text corruption detected (orphaned vowel signs)"
                            )
                            adaptations.append(adaptation)
                            continue

                    if headline:
                        headline = safe_clean_tamil_content(headline, f"llm_headline_{channel.id}")
                        if has_orphaned_tamil_marks(headline):
                            logger.warning(f"⚠️ LLM generated corrupted Tamil headline for channel {channel.id}")
                            headline = None  # Discard corrupted headline

                    adaptation = ContentAdaptation(
                        channel_id=channel.id,
                        adapted_content=adapted_content,
                        hashtags=item.get('hashtags', []),
                        success=bool(adapted_content.strip()),
                        headline=headline,  # Extract headline if present
                        error_message=None if adapted_content.strip() else "Empty content returned"
                    )
                else:
                    # Channel not found in response
                    adaptation = ContentAdaptation(
                        channel_id=channel.id,
                        adapted_content='',
                        hashtags=[],
                        success=False,
                        headline=None,
                        error_message="Channel not found in API response"
                    )
                
                adaptations.append(adaptation)
                
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse JSON response: {e}")
            logger.exception(f"Response content: {response}")

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content='',
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message="Failed to parse API response"
                )
                for channel in channels
            ]

        except Exception as e:
            logger.exception(f"Unexpected error parsing response: {e}")

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content='',
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message=f"Parsing error: {str(e)}"
                )
                for channel in channels
            ]

        return (adaptations, district)

    async def _call_llm_api_for_multi_page(self, messages: List[Dict[str, str]], provider: Optional[LLMProvider] = None, image_url: Optional[str] = None) -> str:
        """
        Make call to LLM API for multi-page news generation (defaults to Gemini Flash)
        Supports vision-enabled models when image_url is provided

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            provider: Optional LLM provider override
            image_url: Optional image URL for vision-enabled models
        """
        try:
            # Use system message from the messages array
            response = await llm_service.generate(
                messages=messages,
                profile=LLMProfile.DEFAULT,
                provider=provider,  # None = uses default (Gemini Flash)
                temperature=0.7,
                max_tokens=8000,  # Increased for multiple pages with Tamil content (uses more tokens)
                service_name="content_adaptation_multi_page_news",
                image_url=image_url  # Pass image for vision models
            )

            return response

        except Exception as e:
            logger.exception(f"LLM API call failed for multi-page news: {e}")
            raise

    def _parse_multi_page_response(
        self,
        response: str,
        channels: List[ChannelConfig],
        extract_district: bool = False
    ) -> Tuple[List[ContentAdaptation], Optional[str]]:
        """
        Parse the multi-page news response from LLM.

        Expected formats:
        - Without district:
          [{Page: "Account Name", HL: "headline", Cnt: "content", Tags: "#tag1 #tag2"}]

        - With district (3 cases):
          1. Specific district/city: {District: "சென்னை", Pages: [...]}
          2. State-level news: {is_state_news: true, Pages: [...]} → district = "தமிழ்நாடு"
          3. National-level news: {is_national_news: true, Pages: [...]} → district = "இந்தியா"
        """
        adaptations = []
        district = None

        try:
            # Strip markdown code fences if present (```json ... ```)
            response_clean = response.strip()
            if response_clean.startswith('```'):
                lines = response_clean.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response_clean = '\n'.join(lines).strip()

            # Check for truncated JSON response (basic validation)
            if response_clean and not (response_clean.endswith(']') or response_clean.endswith('}')):
                logger.warning(f"⚠️ Response appears truncated (doesn't end with ] or }}): ...{response_clean[-100:]}")
                raise ValueError("Truncated JSON response detected - likely hit token limit")

            # Parse JSON response
            data = json.loads(response_clean)

            # Log parsed response for debugging (use INFO to help troubleshoot name matching issues)
            logger.info(f"LLM Response type: {type(data).__name__}, keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

            # Handle different response formats
            if isinstance(data, list):
                # Old format: direct list
                response_items = data
            elif isinstance(data, dict):
                # Check for district extraction format
                if extract_district and 'Pages' in data:
                    # Handle three cases:
                    # 1. District name found: {District: "சென்னை", Pages: [...]}
                    # 2. State-level news: {is_state_news: true, Pages: [...]}
                    # 3. National-level news: {is_national_news: true, Pages: [...]}

                    if 'District' in data:
                        # Case 1: Specific district/city found
                        district = data.get('District', '').strip()
                        if district:
                            if district == 'is_state_news':
                                district = "தமிழ்நாடு"
                                logger.info(f"✓ State-level news detected, using district: {district}")
                            elif district == 'is_national_news':
                                district = "இந்தியா"
                                logger.info(f"✓ National-level news detected, using district: {district}")
                            else:
                                # Clean Tamil text in extracted district
                                district = safe_clean_tamil_content(district, "llm_extracted_district")
                                # Validate and fallback
                                if has_orphaned_tamil_marks(district) or len(district) > 100:
                                    logger.warning(f"⚠️ LLM generated invalid district: {district}, using state fallback")
                                    district = "தமிழ்நாடு"
                                else:
                                    logger.info(f"✓ Extracted specific district from content: {district}")
                        else:
                            district = "தமிழ்நாடு"

                    elif data.get('is_state_news') is True:
                        # Case 2: State-level news → use தமிழ்நாடு
                        district = "தமிழ்நாடு"
                        logger.info(f"✓ State-level news detected, using district: {district}")

                    elif data.get('is_national_news') is True:
                        # Case 3: National-level news → use இந்தியா
                        district = "இந்தியா"
                        logger.info(f"✓ National-level news detected, using district: {district}")

                    else:
                        # Fallback if none of the keys are present
                        # district = "தமிழ்நாடு"
                        district = "இந்தியா"
                        logger.warning(f"⚠️ No district extraction keys found, using fallback: {district}")

                    response_items = data.get('Pages', [])
                elif 'adaptations' in data:
                    # Handle if LLM returns {"adaptations": [...]} format
                    response_items = data['adaptations']
                elif 'Pages' in data:
                    # Has Pages but no District
                    response_items = data['Pages']
                else:
                    # Unknown dict format
                    logger.warning(f"Unexpected response format: {type(data)}, keys: {data.keys()}")
                    response_items = []
            else:
                # Unexpected type
                logger.warning(f"Unexpected response type: {type(data)}")
                response_items = []

            # Create multiple mappings for robust name matching
            # Map account_name to LIST of channels (since one account_name can be used for multiple platforms)
            from collections import defaultdict
            # Normalized match (lowercase + trimmed + no spaces)
            name_to_channels_normalized = defaultdict(list)
            for channel in channels:
                normalized_name = channel.account_name.replace(" ", "").lower().strip()
                name_to_channels_normalized[normalized_name].append(channel)

            # Track which channels we've processed
            processed_channel_ids = set()

            # Log expected channel names for debugging
            expected_names = list(name_to_channels_normalized.keys())
            logger.info(f"Expected channel names ({len(expected_names)}): {expected_names}")

            # Log received items from LLM
            received_page_names = [item.get('Page', '').strip() for item in response_items]
            logger.info(f"Received Page names from LLM ({len(received_page_names)}): {received_page_names}")

            # Process each item in the response
            for item in response_items:
                page_name = item.get('Page', '').strip()  # Trim spaces
                headline = item.get('HL', '')
                content = item.get('Cnt', '')
                tags_str = item.get('Tags', '')

                logger.debug(f"Processing LLM response item: Page='{page_name}'")

                # Find matching channels by name
                # Use normalized matching since LLM returns normalized names (lowercase, no spaces)
                normalized_page = page_name.replace(" ", "").lower().strip()
                matching_channels = name_to_channels_normalized.get(normalized_page, [])

                if matching_channels:
                    logger.info(f"Matched '{page_name}' to {len(matching_channels)} channel(s)")
                else:
                    # Try fuzzy matching for Tamil transliteration variations (thi/ti, etc.)
                    fuzzy_matched = fuzzy_match_channel_name(normalized_page, expected_names)
                    if fuzzy_matched:
                        matching_channels = name_to_channels_normalized.get(fuzzy_matched, [])
                        if matching_channels:
                            logger.info(f"✓ Fuzzy matched '{page_name}' → '{fuzzy_matched}' to {len(matching_channels)} channel(s)")

                if not matching_channels:
                    logger.error(f"❌ Could not find channels for Page: '{page_name}' (normalized: '{normalized_page}')")
                    logger.error(f"   Available normalized channels: {expected_names}")
                    continue

                # Parse tags from string to list
                hashtags = []
                if tags_str:
                    # Split by spaces and filter out empty strings
                    hashtags = [tag.strip() for tag in tags_str.split() if tag.strip().startswith('#')]

                # Create adaptations for ALL matching channels (same account_name on different platforms)
                for channel in matching_channels:
                    # Clean Tamil text in LLM-generated content
                    cleaned_content = content
                    if content:
                        cleaned_content = safe_clean_tamil_content(content, f"llm_multi_page_content_{channel.id}")
                        # Check for Tamil corruption
                        if has_orphaned_tamil_marks(cleaned_content):
                            logger.warning(f"⚠️ LLM generated corrupted Tamil content for {page_name} (channel {channel.id})")
                            adaptation = ContentAdaptation(
                                channel_id=channel.id,
                                adapted_content='',
                                hashtags=[],
                                success=False,
                                headline=None,
                                error_message="Tamil text corruption detected (orphaned vowel signs)"
                            )
                            adaptations.append(adaptation)
                            processed_channel_ids.add(channel.id)
                            continue

                    cleaned_headline = headline
                    if headline:
                        cleaned_headline = safe_clean_tamil_content(headline, f"llm_multi_page_headline_{channel.id}")
                        if has_orphaned_tamil_marks(cleaned_headline):
                            logger.warning(f"⚠️ LLM generated corrupted Tamil headline for {page_name} (channel {channel.id})")
                            cleaned_headline = None  # Discard corrupted headline

                    # Create adaptation object for this channel
                    adaptation = ContentAdaptation(
                        channel_id=channel.id,
                        adapted_content=cleaned_content,
                        hashtags=hashtags,
                        success=bool(cleaned_content.strip()),
                        headline=cleaned_headline,
                        error_message=None if cleaned_content.strip() else "Empty content returned"
                    )
                    adaptations.append(adaptation)
                    processed_channel_ids.add(channel.id)

                # Log how many channels were mapped
                logger.info(f"✓ Mapped '{page_name}' to {len(matching_channels)} channel(s): {[c.id for c in matching_channels]}")

            # Add failed adaptations for any channels that weren't in the response
            for channel in channels:
                if channel.id not in processed_channel_ids:
                    adaptation = ContentAdaptation(
                        channel_id=channel.id,
                        adapted_content='',
                        hashtags=[],
                        success=False,
                        headline=None,
                        error_message="Channel not found in API response"
                    )
                    adaptations.append(adaptation)

        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response[:500]}")  # Log first 500 chars

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content='',
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message="Failed to parse API response"
                )
                for channel in channels
            ]

        except Exception as e:
            logger.exception(f"Unexpected error parsing multi-page response: {e}")

            # Return failed adaptations for all channels
            adaptations = [
                ContentAdaptation(
                    channel_id=channel.id,
                    adapted_content='',
                    hashtags=[],
                    success=False,
                    headline=None,
                    error_message=f"Parsing error: {str(e)}"
                )
                for channel in channels
            ]

        return (adaptations, district)

    async def get_channel_configs(
        self, 
        db_client, 
        social_account_ids: List[str], 
        tenant_id: str
    ) -> List[ChannelConfig]:
        """
        Fetch channel configurations from database
        
        Args:
            db_client: Supabase client
            social_account_ids: List of social account IDs
            tenant_id: Tenant ID for filtering
            
        Returns:
            List of channel configurations
        """
        try:
            # Handle both SupabaseClient wrapper and raw Supabase client
            if hasattr(db_client, 'client'):
                # It's a SupabaseClient wrapper
                client = db_client.client
            elif hasattr(db_client, 'table'):
                # It's a raw Supabase client
                client = db_client
            else:
                raise AttributeError("Invalid database client: missing 'table' or 'client' attribute")
            
            response = client.table('social_accounts').select(
                'id, platform, account_name, content_tone, custom_instructions'
            ).in_('id', social_account_ids).eq('tenant_id', tenant_id).eq('status', 'connected').execute()
            
            channels = []
            for account in response.data or []:
                channel = ChannelConfig(
                    id=account['id'],
                    platform=account['platform'],
                    account_name=account['account_name'],
                    content_tone=account.get('content_tone', 'professional'),
                    custom_instructions=account.get('custom_instructions')
                )
                channels.append(channel)
            
            logger.info(f"Loaded {len(channels)} channel configurations")
            return channels
            
        except Exception as e:
            logger.exception(f"Failed to load channel configurations: {e}")
            return []

    async def track_adaptation_result(
        self,
        db_client,
        post_id: str,
        channel_id: str,
        adaptation: ContentAdaptation,
        tenant_id: str
    ):
        """Track adaptation results in database for analytics"""
        try:
            # Skip tracking for preview posts (non-UUID post_id like "preview")
            try:
                UUID(post_id)
            except (ValueError, AttributeError):
                logger.debug(f"Skipping adaptation tracking for non-UUID post_id: {post_id}")
                return

            # Handle both SupabaseClient wrapper and raw Supabase client
            if hasattr(db_client, 'client'):
                # It's a SupabaseClient wrapper
                client = db_client.client
            elif hasattr(db_client, 'table'):
                # It's a raw Supabase client
                client = db_client
            else:
                raise AttributeError("Invalid database client: missing 'table' or 'client' attribute")

            tracking_data = {
                'post_id': post_id,
                'channel_id': channel_id,
                'tenant_id': tenant_id,
                'success': adaptation.success,
                'adapted_content_length': len(adaptation.adapted_content) if adaptation.adapted_content else 0,
                'hashtag_count': len(adaptation.hashtags) if adaptation.hashtags else 0,
                'error_message': adaptation.error_message
            }

            # Insert into a tracking table (you might need to create this table)
            client.table('content_adaptations').insert(tracking_data).execute()

        except Exception as e:
            logger.exception(f"Failed to track adaptation result: {e}")