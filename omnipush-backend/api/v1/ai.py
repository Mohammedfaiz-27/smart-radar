from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
import logging
from openai import AsyncOpenAI
from typing import List, Dict, Any
import re
from services.s3_service import s3_service

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.config import settings
from models.auth import JWTPayload
from models.ai import (
    ContentSuggestionRequest,
    OptimizeContentRequest,
    ImageGenerationRequest,
    EnhanceImagePromptRequest,
    ContentSuggestionResponse,
    OptimizeContentResponse,
    ImageGenerationResponse,
    EnhanceImagePromptResponse,
    ContentSuggestion,
    AIUsage,
    ContentTone,
    ImageStyle
)
from models.content import Platform

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI assistant"])

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


async def get_ai_usage_for_tenant(tenant_id: str, ctx: TenantContext) -> AIUsage:
    """Get current AI usage for tenant this month"""
    try:
        # Get current month start
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count AI-generated content this month
        # This would include AI text generation and AI image generation
        ai_text_count = 0  # Would query AI usage logs
        
        ai_images_response = ctx.table('media').select('id', count='exact').not_.is_(
            'generation_prompt', 'null'
        ).gte('created_at', current_month.isoformat()).execute()
        
        ai_images_count = ai_images_response.count or 0
        
        # Calculate tokens used (rough estimate)
        tokens_used = (ai_text_count * 150) + (ai_images_count * 50)  # Rough estimates
        
        # Get tenant subscription to determine limits
        tenant_response = ctx.db.client.table('tenants').select(
            'subscription_tier'
        ).eq('id', tenant_id).maybe_single().execute()
        
        subscription_tier = tenant_response.data.get('subscription_tier', 'basic') if tenant_response.data else 'basic'
        
        # Set limits based on subscription tier
        if subscription_tier == 'basic':
            monthly_limit = 1000
        elif subscription_tier == 'pro':
            monthly_limit = 10000
        else:  # enterprise
            monthly_limit = 100000
        
        return AIUsage(
            tokens_used=tokens_used,
            monthly_limit=monthly_limit,
            remaining=max(0, monthly_limit - tokens_used)
        )
        
    except Exception as e:
        logger.exception(f"Failed to get AI usage: {e}")
        # Return default values on error
        return AIUsage(
            tokens_used=0,
            monthly_limit=1000,
            remaining=1000
        )


def get_platform_specific_guidelines(platform: Platform) -> str:
    """Get platform-specific content guidelines"""
    guidelines = {
        Platform.FACEBOOK: {
            "max_length": 2000,
            "style": "Friendly, conversational tone. Use emojis sparingly. Focus on storytelling.",
            "features": "Can include longer content, multiple images, links work well."
        },
        Platform.INSTAGRAM: {
            "max_length": 2200,
            "style": "Visual-first, lifestyle-focused. Use relevant hashtags (5-10). Engage with community.",
            "features": "Stories, Reels, carousel posts. Strong visual component required."
        },
        Platform.TWITTER: {
            "max_length": 280,
            "style": "Concise, witty, timely. Use hashtags strategically (1-2). Be conversational.",
            "features": "Threading for longer thoughts. Replies and retweets for engagement."
        },
        Platform.LINKEDIN: {
            "max_length": 3000,
            "style": "Professional, industry-focused. Share insights and expertise. Use professional tone.",
            "features": "Document posts, industry discussions, professional networking."
        },
        Platform.YOUTUBE: {
            "max_length": 5000,
            "style": "Descriptive, SEO-optimized. Include timestamps, clear CTAs.",
            "features": "Video descriptions, community posts, playlist organization."
        },
        Platform.TIKTOK: {
            "max_length": 300,
            "style": "Fun, trendy, authentic. Use trending sounds and hashtags.",
            "features": "Short-form video focus, trends, challenges, effects."
        },
        Platform.PINTEREST: {
            "max_length": 500,
            "style": "Descriptive, keyword-rich. Focus on inspiration and utility.",
            "features": "Pin descriptions, board organization, seasonal content."
        }
    }
    
    return guidelines.get(platform, guidelines[Platform.FACEBOOK])


async def generate_content_with_openai(
    prompt: str,
    platform: Platform = None,
    tone: ContentTone = ContentTone.PROFESSIONAL,
    max_length: int = None
) -> List[ContentSuggestion]:
    """Generate content suggestions using OpenAI"""
    
    if not openai_client:
        # Return mock suggestions if OpenAI is not configured
        return generate_mock_content_suggestions(prompt, platform, tone)
    
    try:
        # Build system message with guidelines
        system_message = f"You are a social media content creator. Generate engaging content with a {tone.value} tone."
        
        if platform:
            guidelines = get_platform_specific_guidelines(platform)
            system_message += f"\n\nPlatform: {platform.value}\n"
            system_message += f"Style guidelines: {guidelines['style']}\n"
            system_message += f"Features: {guidelines['features']}\n"
            if max_length:
                system_message += f"Max length: {max_length} characters\n"
            else:
                system_message += f"Recommended max length: {guidelines['max_length']} characters\n"
        
        system_message += "\n\nGenerate 3 different variations of the content. Each should be unique and engaging."
        
        # Generate content using OpenAI
        response = await openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Create social media content about: {prompt}"}
            ],
            max_tokens=1000,
            temperature=0.7,
            n=1
        )
        
        generated_text = response.choices[0].message.content.strip()
        
        # Parse the response into individual suggestions
        suggestions = []
        variations = generated_text.split('\n\n')
        
        for i, variation in enumerate(variations[:3]):
            if variation.strip():
                # Clean up the variation text
                clean_text = variation.strip()
                if clean_text.startswith(f"{i+1}."):
                    clean_text = clean_text[2:].strip()
                elif clean_text.startswith(f"Variation {i+1}:"):
                    clean_text = clean_text[len(f"Variation {i+1}:"):].strip()
                
                suggestions.append(ContentSuggestion(
                    text=clean_text,
                    platform=platform,
                    tone=tone,
                    estimated_engagement=0.7 + (i * 0.1)  # Mock engagement score
                ))
        
        # If we don't have 3 suggestions, create additional ones
        while len(suggestions) < 3:
            suggestions.append(ContentSuggestion(
                text=f"Engaging content about {prompt} with {tone.value} tone",
                platform=platform,
                tone=tone,
                estimated_engagement=0.5
            ))
        
        return suggestions
        
    except Exception as e:
        logger.exception(f"OpenAI API error: {e}")
        # Fallback to mock suggestions
        return generate_mock_content_suggestions(prompt, platform, tone)


def generate_mock_content_suggestions(
    prompt: str,
    platform: Platform = None,
    tone: ContentTone = ContentTone.PROFESSIONAL
) -> List[ContentSuggestion]:
    """Generate mock content suggestions when OpenAI is not available"""
    
    # Template-based content generation for demo
    templates = {
        ContentTone.PROFESSIONAL: [
            "Excited to share insights about {topic}. This represents a significant step forward in our industry. #Innovation #Growth",
            "Key takeaway from recent developments in {topic}: the importance of strategic thinking and execution. What are your thoughts?",
            "Breaking down the latest trends in {topic} and what they mean for businesses moving forward. #Strategy #Insights"
        ],
        ContentTone.CASUAL: [
            "Just discovered something cool about {topic}! 🤔 Anyone else finding this as interesting as I am? #TrendingNow",
            "Quick thought on {topic} - it's amazing how much this has evolved lately! What's your take? 💭",
            "Can we talk about {topic} for a sec? The possibilities here are endless! ✨ #Excited"
        ],
        ContentTone.ENTHUSIASTIC: [
            "🚀 AMAZING developments in {topic}! This is exactly what we needed to see! Who else is pumped about this? #GameChanger",
            "I can't contain my excitement about {topic}! 🎉 This is revolutionary and I'm here for ALL of it! #Innovation",
            "WOW! The progress in {topic} is absolutely incredible! 🔥 The future is looking brighter than ever! #Amazing"
        ]
    }
    
    suggestions = []
    template_list = templates.get(tone, templates[ContentTone.PROFESSIONAL])
    
    for i, template in enumerate(template_list):
        content = template.format(topic=prompt)
        
        # Adjust for platform if specified
        if platform == Platform.TWITTER and len(content) > 280:
            content = content[:250] + "... 🧵"
        elif platform == Platform.INSTAGRAM:
            content += "\n\n#instadaily #contentcreator"
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', content)
        
        suggestions.append(ContentSuggestion(
            content=content,
            confidence=0.80 + (i * 0.05),
            hashtags=hashtags
        ))
    
    return suggestions


@router.post("/content-suggestions", response_model=ContentSuggestionResponse)
async def generate_content_suggestions(
    request: ContentSuggestionRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate AI-powered content suggestions"""
    try:
        # Check AI usage limits
        ai_usage = await get_ai_usage_for_tenant(current_user.tenant_id, ctx)
        
        if ai_usage.remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI usage limit reached for this month"
            )
        
        # Generate content suggestions
        suggestions = await generate_content_with_openai(
            prompt=request.prompt,
            platform=request.platform,
            tone=request.tone,
            max_length=request.max_length
        )
        
        # Update usage (in production, you'd track this properly)
        estimated_tokens = len(request.prompt) * 2  # Rough estimate
        ai_usage.tokens_used += estimated_tokens
        ai_usage.remaining = max(0, ai_usage.remaining - estimated_tokens)
        
        return ContentSuggestionResponse(
            suggestions=suggestions,
            usage=ai_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate content suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate content suggestions"
        )


@router.post("/optimize-content", response_model=OptimizeContentResponse)
async def optimize_content_for_platform(
    request: OptimizeContentRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Optimize content for a specific platform"""
    try:
        # Get platform-specific guidelines
        source_guidelines = get_platform_specific_guidelines(request.source_platform)
        target_guidelines = get_platform_specific_guidelines(request.target_platform)
        
        if openai_client:
            try:
                # Use OpenAI to optimize content
                system_message = f"""
                You are optimizing social media content from {request.source_platform.value} for {request.target_platform.value}.
                
                Source platform style: {source_guidelines['style']}
                Target platform style: {target_guidelines['style']}
                Target max length: {target_guidelines['max_length']} characters
                Target features: {target_guidelines['features']}
                
                Optimize the content while maintaining its core message and intent.
                Return only the optimized content, followed by a list of changes made.
                """
                
                response = await openai_client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Optimize this content: {request.content}"}
                    ],
                    max_tokens=500,
                    temperature=0.5
                )
                
                result = response.choices[0].message.content.strip()
                
                # Parse optimized content and changes
                if "\n\nChanges made:" in result:
                    optimized_content, changes_text = result.split("\n\nChanges made:", 1)
                    changes_made = [change.strip("- ").strip() for change in changes_text.split('\n') if change.strip()]
                else:
                    optimized_content = result
                    changes_made = ["Optimized for platform-specific style and requirements"]
                
            except Exception as e:
                logger.exception(f"OpenAI optimization failed: {e}")
                # Fallback optimization
                optimized_content = request.content[:target_guidelines['max_length']]
                changes_made = ["Content truncated to fit platform requirements"]
        else:
            # Fallback optimization without OpenAI
            optimized_content = request.content[:target_guidelines['max_length']]
            changes_made = ["Content truncated to fit platform requirements"]
        
        return OptimizeContentResponse(
            optimized_content=optimized_content,
            changes_made=changes_made,
            source_platform=request.source_platform,
            target_platform=request.target_platform
        )
        
    except Exception as e:
        logger.exception(f"Failed to optimize content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize content"
        )


def optimize_content_rules_based(
    content: str,
    source_platform: Platform,
    target_platform: Platform,
    source_guidelines: Dict[str, Any],
    target_guidelines: Dict[str, Any]
) -> tuple[str, List[str]]:
    """Rule-based content optimization"""
    
    optimized = content
    changes = []
    
    # Length optimization
    max_length = target_guidelines['max_length']
    if len(optimized) > max_length:
        # Truncate and add appropriate ending
        if target_platform == Platform.TWITTER:
            optimized = optimized[:270] + "... 🧵"
            changes.append("Truncated content to fit Twitter character limit")
        else:
            optimized = optimized[:max_length-10] + "..."
            changes.append(f"Shortened content for {target_platform.value}")
    
    # Platform-specific optimizations
    if target_platform == Platform.INSTAGRAM:
        if not re.search(r'#\w+', optimized):
            optimized += "\n\n#inspiration #contentcreator #instadaily"
            changes.append("Added Instagram hashtags")
    
    elif target_platform == Platform.TWITTER:
        # Make it more conversational
        if not optimized.endswith('?') and len(optimized) < 200:
            optimized += " What do you think?"
            changes.append("Added engagement question for Twitter")
    
    elif target_platform == Platform.LINKEDIN:
        if not optimized.startswith(('Excited to', 'Thrilled to', 'Pleased to')):
            optimized = "Excited to share: " + optimized
            changes.append("Added professional opening for LinkedIn")
    
    elif target_platform == Platform.FACEBOOK:
        if '🤔' not in optimized and '💭' not in optimized:
            optimized += " 💭"
            changes.append("Added emoji for Facebook engagement")
    
    # Remove platform-specific elements that don't work elsewhere
    if source_platform == Platform.TWITTER and target_platform != Platform.TWITTER:
        if optimized.endswith("🧵"):
            optimized = optimized[:-2].strip()
            changes.append("Removed Twitter thread indicator")
    
    if not changes:
        changes.append("Optimized content style for target platform")
    
    return optimized, changes


@router.get("/usage")
async def get_ai_usage(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get current AI usage statistics for the tenant"""
    try:
        ai_usage = await get_ai_usage_for_tenant(current_user.tenant_id, ctx)
        
        # Calculate usage percentage
        usage_percentage = (ai_usage.tokens_used / ai_usage.monthly_limit * 100) if ai_usage.monthly_limit > 0 else 0
        
        return {
            "usage": ai_usage,
            "usage_percentage": round(usage_percentage, 2),
            "days_remaining_in_month": (datetime.utcnow().replace(month=datetime.utcnow().month + 1, day=1) - datetime.utcnow()).days,
            "features_available": {
                "content_suggestions": ai_usage.remaining > 0,
                "content_optimization": ai_usage.remaining > 0,
                "ai_image_generation": ai_usage.remaining > 0
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to get AI usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI usage"
        )


@router.post("/enhance-image-prompt", response_model=EnhanceImagePromptResponse)
async def enhance_image_prompt(
    request: EnhanceImagePromptRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Enhance content text into a detailed image generation prompt"""
    try:
        if not openai_client:
            # Fallback enhancement without OpenAI
            enhanced_prompt = f"Create a visually appealing, professional image that represents: {request.content}. Use modern design principles, good lighting, and engaging composition."
            return EnhanceImagePromptResponse(
                enhanced_prompt=enhanced_prompt,
                original_content=request.content
            )
        
        # Check AI usage limits
        ai_usage = await get_ai_usage_for_tenant(current_user.tenant_id, ctx)
        
        if ai_usage.remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI usage limit reached for this month"
            )
        
        # Use OpenAI to enhance the prompt
        system_message = """You are an expert at creating detailed, visually compelling prompts for AI image generation. 
        Given user content, create a detailed image generation prompt that will produce a high-quality, engaging image.

        Guidelines:
        - Make the prompt visually specific and detailed
        - Include style, mood, lighting, and composition suggestions
        - Focus on creating professional, eye-catching imagery
        - Keep the core message of the original content
        - Aim for prompts that work well with DALL-E 3
        - Make it suitable for social media posts
        
        Return only the enhanced image prompt, nothing else."""
        
        response = await openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Enhance this content into a detailed image generation prompt: {request.content}"}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        enhanced_prompt = response.choices[0].message.content.strip()
        
        # Update AI usage
        estimated_tokens = len(request.content) + len(enhanced_prompt)
        ai_usage.tokens_used += estimated_tokens
        
        return EnhanceImagePromptResponse(
            enhanced_prompt=enhanced_prompt,
            original_content=request.content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to enhance image prompt: {e}")
        # Fallback enhancement
        enhanced_prompt = f"Create a visually appealing, professional image that represents: {request.content}. Use modern design principles, good lighting, and engaging composition."
        return EnhanceImagePromptResponse(
            enhanced_prompt=enhanced_prompt,
            original_content=request.content
        )


@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_ai_image(
    request: ImageGenerationRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate AI image using OpenAI DALL-E"""
    try:
        if not openai_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI image generation is not available. OpenAI API key is not configured."
            )
        
        # Check AI usage limits
        ai_usage = await get_ai_usage_for_tenant(current_user.tenant_id, ctx)
        
        if ai_usage.remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI usage limit reached for this month"
            )
        
        # Prepare the prompt for image generation with style
        style_instructions = {
            ImageStyle.REALISTIC: "Create a photorealistic, highly detailed image",
            ImageStyle.CARTOON: "Create a cartoon-style, animated illustration",
            ImageStyle.ILLUSTRATION: "Create a digital illustration with clean lines and vibrant colors",
            ImageStyle.PHOTOGRAPHY: "Create a professional photograph with excellent composition and lighting",
            ImageStyle.PAINTING: "Create an artistic painting with visible brush strokes and rich textures",
            ImageStyle.SKETCH: "Create a hand-drawn sketch with pencil or charcoal techniques",
            ImageStyle.MINIMALIST: "Create a clean, minimalist design with simple shapes and limited colors",
            ImageStyle.VINTAGE: "Create a vintage-style image with retro colors and classic aesthetics",
            ImageStyle.MODERN: "Create a modern, contemporary design with sleek elements",
            ImageStyle.ABSTRACT: "Create an abstract artistic interpretation with creative shapes and forms",
            ImageStyle.WATERCOLOR: "Create a watercolor painting with soft, flowing colors and artistic brush effects",
            ImageStyle.OIL_PAINTING: "Create an oil painting with rich textures, deep colors, and classic artistic techniques"
        }
        
        style_instruction = style_instructions.get(request.style, style_instructions[ImageStyle.REALISTIC])
        image_prompt = f"{style_instruction}. {request.prompt}"
        
        # If text overlay is requested, modify the prompt to include text
        if request.text_overlay:
            image_prompt = f"{image_prompt}. Include the text '{request.text_overlay}' prominently displayed in the image"
        
        # Generate image using OpenAI DALL-E
        response = await openai_client.images.generate(
            model= "dall-e-3", #"gpt-image-1",
            prompt=image_prompt,
            size=request.size,
            quality=request.quality,
            n=1
        )
        
        # Get the generated image URL and revised prompt
        image_url = response.data[0].url
        revised_prompt = getattr(response.data[0], 'revised_prompt', None)
        
        # Download and upload to S3
        filename = f"ai-generated-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
        s3_result = await s3_service.download_and_upload_image(
            image_url,
            filename,
            current_user.tenant_id
        )
        
        # Save to media database
        media_data = {
            "file_name": s3_result["filename"],
            "file_path": s3_result["key"],
            "file_size": s3_result["size"],
            "media_type": "image",
            "mime_type": s3_result["content_type"],
            "tenant_id": current_user.tenant_id,
            # "uploaded_by": current_user.sub,  # sub contains the user_id #TODO: Fix it
            # "generation_prompt": image_prompt,
            # "ai_model": "dall-e-3",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into media table
        media_response = ctx.table('media').insert(media_data).execute()
        media_id = media_response.data[0]['id']
        
        # Update AI usage
        estimated_tokens = 100  # Rough estimate for image generation
        ai_usage.tokens_used += estimated_tokens
        ai_usage.remaining = max(0, ai_usage.remaining - estimated_tokens)
        
        return ImageGenerationResponse(
            image_url=image_url,
            s3_url=s3_result["url"],
            prompt_used=image_prompt,
            size=request.size,
            quality=request.quality,
            style=request.style.value,
            revised_prompt=revised_prompt,
            media_id=media_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate AI image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI image: {str(e)}"
        )


@router.post("/content-ideas")
async def generate_content_ideas(
    topic: str,
    count: int = 10,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate content ideas for a given topic"""
    try:
        # Check AI usage
        ai_usage = await get_ai_usage_for_tenant(current_user.tenant_id, ctx)
        
        if ai_usage.remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI usage limit reached"
            )
        
        # Generate content ideas (mock implementation)
        ideas = [
            f"5 ways {topic} is changing the industry",
            f"Behind the scenes: How we approach {topic}",
            f"Common myths about {topic} debunked",
            f"The future of {topic}: What to expect",
            f"{topic} tips for beginners",
            f"Case study: Success story with {topic}",
            f"Quick wins you can achieve with {topic}",
            f"Expert insights on {topic} trends",
            f"Tools and resources for {topic}",
            f"Mistakes to avoid when dealing with {topic}"
        ]
        
        return {
            "topic": topic,
            "ideas": ideas[:count],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate content ideas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate content ideas"
        )