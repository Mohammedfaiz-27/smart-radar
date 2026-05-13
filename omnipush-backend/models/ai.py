from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from .base import BaseResponse
from .content import Platform


class ContentTone(str, Enum):
    """Content tone options for AI-generated content"""
    # Original tones
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    HUMOROUS = "humorous"
    FORMAL = "formal"
    ENTHUSIASTIC = "enthusiastic"

    # Expanded tones for enhanced content generation
    INSPIRATIONAL = "inspirational"
    INFORMATIVE = "informative"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    EMPATHETIC = "empathetic"
    PERSUASIVE = "persuasive"
    EDUCATIONAL = "educational"
    ENTERTAINING = "entertaining"
    MOTIVATIONAL = "motivational"
    URGENT = "urgent"
    CALM = "calm"
    PLAYFUL = "playful"
    SERIOUS = "serious"
    WITTY = "witty"
    COMPASSIONATE = "compassionate"
    BOLD = "bold"
    CONFIDENT = "confident"
    HUMBLE = "humble"
    AUTHENTIC = "authentic"
    STORYTELLING = "storytelling"
    ANALYTICAL = "analytical"
    EMOTIONAL = "emotional"
    RATIONAL = "rational"
    TRENDY = "trendy"
    NOSTALGIC = "nostalgic"
    FUTURISTIC = "futuristic"
    MINIMALIST = "minimalist"
    LUXURIOUS = "luxurious"
    QUIRKY = "quirky"
    DIPLOMATIC = "diplomatic"
    REBELLIOUS = "rebellious"
    SUPPORTIVE = "supportive"


class ImageStyle(str, Enum):
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ILLUSTRATION = "illustration"
    PHOTOGRAPHY = "photography"
    PAINTING = "painting"
    SKETCH = "sketch"
    MINIMALIST = "minimalist"
    VINTAGE = "vintage"
    MODERN = "modern"
    ABSTRACT = "abstract"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil_painting"


# Request Models
class ContentSuggestionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    platform: Optional[Platform] = None
    tone: ContentTone = ContentTone.PROFESSIONAL
    max_length: Optional[int] = Field(None, ge=1, le=2000)


class OptimizeContentRequest(BaseModel):
    content: str = Field(min_length=1)
    source_platform: Platform
    target_platform: Platform


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000, description="Description for image generation")
    text_overlay: Optional[str] = Field(None, max_length=1000, description="Text to overlay on the image")
    size: Optional[str] = Field("1024x1024", description="Image size (1024x1024, 1792x1024, or 1024x1792)")
    quality: Optional[str] = Field("high", description="Image quality (standard or hd)")
    style: Optional[ImageStyle] = Field(ImageStyle.REALISTIC, description="Style for the generated image")


class EnhanceImagePromptRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000, description="Content to enhance into image prompt")


# Response Models
class ContentSuggestion(BaseModel):
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    hashtags: List[str] = []


class AIUsage(BaseModel):
    tokens_used: int
    monthly_limit: int
    remaining: int


class ContentSuggestionResponse(BaseResponse):
    suggestions: List[ContentSuggestion]
    usage: AIUsage


class OptimizeContentResponse(BaseResponse):
    optimized_content: str
    changes_made: List[str]
    source_platform: Platform
    target_platform: Platform


class ImageGenerationResponse(BaseResponse):
    image_url: str
    s3_url: str
    prompt_used: str
    size: str
    quality: str
    style: str
    revised_prompt: Optional[str] = None
    media_id: str


class EnhanceImagePromptResponse(BaseResponse):
    enhanced_prompt: str
    original_content: str