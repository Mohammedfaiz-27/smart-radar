"""
Content Tone Characteristics
Comprehensive mapping of content tones to their attributes for AI content generation
"""

from typing import Dict, List

# Mapping from old tone keys (stored in database) to new display names
TONE_MAPPING: Dict[str, str] = {
    'professional': 'Official Admin',
    'casual': 'Casual/Breeze',
    'friendly': 'Community Friendly',
    'humorous': 'Youth/Fun',
    'formal': 'Formal News',
    'enthusiastic': 'Fast News',
    'inspirational': 'Cultural Pride',
    'informative': 'Standard News',
    'conversational': 'Raw Local Slang',
    'authoritative': 'Official News',
    'empathetic': 'Village Hospitality',
    'persuasive': 'Market/Busy',
    'educational': 'Agri/Rural News',
    'entertaining': 'Cinema/Social',
    'motivational': 'Spiritual Connect',
    'urgent': 'Urgent Alert',
    'calm': 'Divine/Formal',
    'playful': 'Youth Gossip',
    'serious': 'Formal District News',
    'compassionate': 'Community Connect',
    'bold': 'Nellai Slang (Heavy)',
    'confident': 'Metro City Vibe',
    'humble': 'Agri Formal',
    'authentic': 'Coastal/Pearl City',
    'storytelling': 'Commuter/Travel',
    'analytical': 'Business/Trade',
    'emotional': 'Nanjil Emotion',
    'rational': 'Industrial News',
    'trendy': 'Kongu Trendy',
    'futuristic': 'Transit/Hub News',
    'minimalist': 'Daily Digest',
    'diplomatic': 'Horticulture/Border',
    'supportive': 'Disaster/Infra Alert'
}

# Tone characteristics for content generation
TONE_CHARACTERISTICS: Dict[str, Dict[str, any]] = {
    "Official Admin": {
        "description": "Business-appropriate, polished, and competent",
        "keywords": [
            "efficient",
            "expert",
            "quality",
            "reliable",
            "trusted"
        ],
        "style_guidelines": "Use clear, concise language. Avoid slang and colloquialisms.",
        "emoji_usage": "minimal",
        "sentence_structure": "formal",
        "typical_phrases": [
            "We're pleased to",
            "Our team",
            "Industry-leading",
            "Excellence in"
        ]
    },
    "Casual/Breeze": {
        "description": "Relaxed, easygoing, and approachable",
        "keywords": [
            "easy",
            "simple",
            "chill",
            "laid-back",
            "no-fuss"
        ],
        "style_guidelines": "Use everyday language. Contractions are fine.",
        "emoji_usage": "moderate",
        "sentence_structure": "informal",
        "typical_phrases": [
            "Hey",
            "Check it out",
            "Pretty cool",
            "You'll love this"
        ]
    },
    "Community Friendly": {
        "description": "Warm, welcoming, and personable",
        "keywords": [
            "welcome",
            "happy",
            "together",
            "community",
            "caring"
        ],
        "style_guidelines": "Be warm and inviting. Address reader directly.",
        "emoji_usage": "moderate",
        "sentence_structure": "conversational",
        "typical_phrases": [
            "We're here for you",
            "Let's",
            "Together we",
            "Welcome to"
        ]
    },
    "Youth/Fun": {
        "description": "Funny, witty, and entertaining",
        "keywords": [
            "fun",
            "laugh",
            "hilarious",
            "amusing",
            "playful"
        ],
        "style_guidelines": "Use wordplay, puns, and light humor. Keep it tasteful.",
        "emoji_usage": "frequent",
        "sentence_structure": "playful",
        "typical_phrases": [
            "You won't believe",
            "Plot twist",
            "Fun fact",
            "Here's a funny thing"
        ]
    },
    "Formal News": {
        "description": "Official, proper, and ceremonious",
        "keywords": [
            "official",
            "proper",
            "respectful",
            "dignified",
            "ceremonial"
        ],
        "style_guidelines": "Use complete sentences. No contractions. Proper grammar essential.",
        "emoji_usage": "none",
        "sentence_structure": "complex",
        "typical_phrases": [
            "It is our pleasure",
            "We cordially",
            "Respectfully",
            "Kindly note"
        ]
    },
    "Fast News": {
        "description": "Energetic, excited, and passionate",
        "keywords": [
            "amazing",
            "incredible",
            "awesome",
            "fantastic",
            "exciting"
        ],
        "style_guidelines": "Show energy and excitement. Use exclamation points.",
        "emoji_usage": "frequent",
        "sentence_structure": "energetic",
        "typical_phrases": [
            "We're thrilled!",
            "Can't wait!",
            "So excited!",
            "This is amazing!"
        ]
    },
    "Cultural Pride": {
        "description": "Uplifting, motivating, and aspirational",
        "keywords": [
            "dream",
            "achieve",
            "believe",
            "possible",
            "inspire"
        ],
        "style_guidelines": "Focus on possibilities and potential. Use aspirational language.",
        "emoji_usage": "moderate",
        "sentence_structure": "motivational",
        "typical_phrases": [
            "You can",
            "Believe in",
            "Dream big",
            "Make it happen"
        ]
    },
    "Standard News": {
        "description": "Educational, factual, and knowledge-focused",
        "keywords": [
            "learn",
            "discover",
            "understand",
            "know",
            "explore"
        ],
        "style_guidelines": "Present facts clearly. Use data and statistics.",
        "emoji_usage": "minimal",
        "sentence_structure": "clear",
        "typical_phrases": [
            "Did you know",
            "According to",
            "Research shows",
            "Here's what"
        ]
    },
    "Raw Local Slang": {
        "description": "Dialogue-like, interactive, and engaging",
        "keywords": [
            "talk",
            "chat",
            "discuss",
            "share",
            "connect"
        ],
        "style_guidelines": "Write as if speaking directly. Use questions.",
        "emoji_usage": "moderate",
        "sentence_structure": "natural",
        "typical_phrases": [
            "What do you think?",
            "Let's talk about",
            "Have you ever",
            "Tell us"
        ]
    },
    "Official News": {
        "description": "Expert, commanding, and credible",
        "keywords": [
            "expert",
            "proven",
            "established",
            "authority",
            "definitive"
        ],
        "style_guidelines": "Demonstrate expertise. Use data and credentials.",
        "emoji_usage": "none",
        "sentence_structure": "assertive",
        "typical_phrases": [
            "Research proves",
            "As experts",
            "The data shows",
            "Our analysis"
        ]
    },
    "Village Hospitality": {
        "description": "Understanding, compassionate, and supportive",
        "keywords": [
            "understand",
            "support",
            "care",
            "compassion",
            "together"
        ],
        "style_guidelines": "Show understanding. Acknowledge feelings.",
        "emoji_usage": "moderate",
        "sentence_structure": "supportive",
        "typical_phrases": [
            "We understand",
            "You're not alone",
            "We're here",
            "It's okay to"
        ]
    },
    "Market/Busy": {
        "description": "Convincing, compelling, and action-oriented",
        "keywords": [
            "best",
            "proven",
            "guarantee",
            "results",
            "transform"
        ],
        "style_guidelines": "Focus on benefits. Use strong call-to-actions.",
        "emoji_usage": "strategic",
        "sentence_structure": "compelling",
        "typical_phrases": [
            "Discover how",
            "Transform your",
            "Don't miss",
            "Join thousands"
        ]
    },
    "Agri/Rural News": {
        "description": "Teaching-focused, instructive, and clarifying",
        "keywords": [
            "learn",
            "master",
            "guide",
            "tutorial",
            "lesson"
        ],
        "style_guidelines": "Break down complex topics. Use step-by-step approach.",
        "emoji_usage": "minimal",
        "sentence_structure": "instructive",
        "typical_phrases": [
            "Here's how",
            "Step by step",
            "Learn to",
            "Master the"
        ]
    },
    "Cinema/Social": {
        "description": "Engaging, amusing, and captivating",
        "keywords": [
            "fun",
            "exciting",
            "engaging",
            "enjoy",
            "delight"
        ],
        "style_guidelines": "Keep it lively and interesting. Use storytelling.",
        "emoji_usage": "frequent",
        "sentence_structure": "dynamic",
        "typical_phrases": [
            "Get ready for",
            "You'll love",
            "Here's something fun",
            "Enjoy the"
        ]
    },
    "Spiritual Connect": {
        "description": "Encouraging, empowering, and action-driving",
        "keywords": [
            "achieve",
            "success",
            "power",
            "overcome",
            "victory"
        ],
        "style_guidelines": "Emphasize potential and capability. Use power words.",
        "emoji_usage": "moderate",
        "sentence_structure": "empowering",
        "typical_phrases": [
            "You've got this",
            "Take action",
            "Start today",
            "Your journey"
        ]
    },
    "Urgent Alert": {
        "description": "Time-sensitive, immediate, and pressing",
        "keywords": [
            "now",
            "today",
            "hurry",
            "limited",
            "deadline"
        ],
        "style_guidelines": "Create sense of immediacy. Use time-bound language.",
        "emoji_usage": "strategic",
        "sentence_structure": "direct",
        "typical_phrases": [
            "Act now",
            "Limited time",
            "Don't wait",
            "Expires soon"
        ]
    },
    "Divine/Formal": {
        "description": "Peaceful, soothing, and tranquil",
        "keywords": [
            "peace",
            "serene",
            "gentle",
            "quiet",
            "relaxed"
        ],
        "style_guidelines": "Use soft language. Avoid urgency or pressure.",
        "emoji_usage": "minimal",
        "sentence_structure": "flowing",
        "typical_phrases": [
            "Take a moment",
            "Breathe",
            "Gently",
            "In your own time"
        ]
    },
    "Youth Gossip": {
        "description": "Fun, lighthearted, and whimsical",
        "keywords": [
            "fun",
            "play",
            "joy",
            "silly",
            "whimsy"
        ],
        "style_guidelines": "Be creative and fun. Don't take it too seriously.",
        "emoji_usage": "frequent",
        "sentence_structure": "whimsical",
        "typical_phrases": [
            "Let's play",
            "Just for fun",
            "Silly but",
            "Ooh, shiny"
        ]
    },
    "Formal District News": {
        "description": "Grave, important, and thoughtful",
        "keywords": [
            "important",
            "critical",
            "significant",
            "matter",
            "concern"
        ],
        "style_guidelines": "Address important topics with gravity. Be respectful.",
        "emoji_usage": "none",
        "sentence_structure": "formal",
        "typical_phrases": [
            "It's important",
            "We must consider",
            "Take note",
            "Critically"
        ]
    },
    "witty": {
        "description": "Clever, sharp, and intellectually humorous",
        "keywords": [
            "clever",
            "smart",
            "quick",
            "sharp",
            "brilliant"
        ],
        "style_guidelines": "Use wordplay and clever observations. Be subtle.",
        "emoji_usage": "moderate",
        "sentence_structure": "clever",
        "typical_phrases": [
            "Interestingly enough",
            "Plot twist",
            "Here's a thought",
            "Fun fact"
        ]
    },
    "Community Connect": {
        "description": "Caring, kind, and understanding",
        "keywords": [
            "care",
            "kindness",
            "heart",
            "gentle",
            "support"
        ],
        "style_guidelines": "Show genuine concern. Use inclusive language.",
        "emoji_usage": "moderate",
        "sentence_structure": "gentle",
        "typical_phrases": [
            "We care",
            "With kindness",
            "Together in this",
            "Support each other"
        ]
    },
    "Nellai Slang (Heavy)": {
        "description": "Daring, confident, and fearless",
        "keywords": [
            "brave",
            "fearless",
            "dare",
            "bold",
            "confident"
        ],
        "style_guidelines": "Make strong statements. Don't hedge or qualify.",
        "emoji_usage": "strategic",
        "sentence_structure": "assertive",
        "typical_phrases": [
            "We dare",
            "Break the rules",
            "Fearlessly",
            "No compromise"
        ]
    },
    "Metro City Vibe": {
        "description": "Self-assured, certain, and assured",
        "keywords": [
            "certain",
            "proven",
            "guaranteed",
            "sure",
            "definite"
        ],
        "style_guidelines": "State things with certainty. Avoid qualifiers.",
        "emoji_usage": "minimal",
        "sentence_structure": "definitive",
        "typical_phrases": [
            "We guarantee",
            "Absolutely",
            "Without doubt",
            "Proven to"
        ]
    },
    "Agri Formal": {
        "description": "Modest, unpretentious, and grounded",
        "keywords": [
            "grateful",
            "honored",
            "fortunate",
            "blessed",
            "thankful"
        ],
        "style_guidelines": "Acknowledge others. Downplay achievements.",
        "emoji_usage": "minimal",
        "sentence_structure": "modest",
        "typical_phrases": [
            "We're grateful",
            "Honored to",
            "Thanks to you",
            "Humbly"
        ]
    },
    "Coastal/Pearl City": {
        "description": "Genuine, real, and transparent",
        "keywords": [
            "real",
            "honest",
            "genuine",
            "true",
            "transparent"
        ],
        "style_guidelines": "Be transparent and honest. Show vulnerability.",
        "emoji_usage": "natural",
        "sentence_structure": "genuine",
        "typical_phrases": [
            "To be honest",
            "Real talk",
            "Authentically",
            "No filter"
        ]
    },
    "Commuter/Travel": {
        "description": "Narrative-driven, engaging, and descriptive",
        "keywords": [
            "story",
            "journey",
            "adventure",
            "tale",
            "chapter"
        ],
        "style_guidelines": "Use narrative structure. Create scenes and characters.",
        "emoji_usage": "strategic",
        "sentence_structure": "narrative",
        "typical_phrases": [
            "Once upon",
            "Our journey",
            "The story goes",
            "Chapter"
        ]
    },
    "Business/Trade": {
        "description": "Data-driven, logical, and systematic",
        "keywords": [
            "data",
            "analysis",
            "metrics",
            "statistics",
            "insights"
        ],
        "style_guidelines": "Focus on facts and data. Use logical progression.",
        "emoji_usage": "none",
        "sentence_structure": "logical",
        "typical_phrases": [
            "Data shows",
            "Analysis reveals",
            "According to metrics",
            "The numbers"
        ]
    },
    "Nanjil Emotion": {
        "description": "Feeling-focused, heartfelt, and touching",
        "keywords": [
            "feel",
            "heart",
            "emotion",
            "soul",
            "passion"
        ],
        "style_guidelines": "Appeal to emotions. Use sensory language.",
        "emoji_usage": "frequent",
        "sentence_structure": "emotive",
        "typical_phrases": [
            "Feel the",
            "From the heart",
            "Touches our soul",
            "Emotional journey"
        ]
    },
    "Industrial News": {
        "description": "Logical, reasonable, and pragmatic",
        "keywords": [
            "logical",
            "practical",
            "sensible",
            "reasonable",
            "pragmatic"
        ],
        "style_guidelines": "Use logical arguments. Focus on practical benefits.",
        "emoji_usage": "none",
        "sentence_structure": "logical",
        "typical_phrases": [
            "It makes sense",
            "Logically",
            "Practically speaking",
            "The reasonable"
        ]
    },
    "Kongu Trendy": {
        "description": "Current, fashionable, and modern",
        "keywords": [
            "trending",
            "viral",
            "hot",
            "latest",
            "buzz"
        ],
        "style_guidelines": "Use current slang and trends. Reference pop culture.",
        "emoji_usage": "frequent",
        "sentence_structure": "modern",
        "typical_phrases": [
            "What's trending",
            "All the buzz",
            "Going viral",
            "Hot right now"
        ]
    },
    "nostalgic": {
        "description": "Reminiscent, sentimental, and reflective",
        "keywords": [
            "remember",
            "classic",
            "vintage",
            "throwback",
            "memories"
        ],
        "style_guidelines": "Reference the past. Evoke memories.",
        "emoji_usage": "minimal",
        "sentence_structure": "reflective",
        "typical_phrases": [
            "Remember when",
            "Back in the day",
            "Classic",
            "Those were the days"
        ]
    },
    "Transit/Hub News": {
        "description": "Forward-looking, innovative, and cutting-edge",
        "keywords": [
            "future",
            "tomorrow",
            "innovation",
            "next-gen",
            "revolutionary"
        ],
        "style_guidelines": "Focus on what's next. Use tech-forward language.",
        "emoji_usage": "moderate",
        "sentence_structure": "forward",
        "typical_phrases": [
            "The future is",
            "Next generation",
            "Tomorrow's",
            "Revolutionary"
        ]
    },
    "Daily Digest": {
        "description": "Simple, clean, and essential",
        "keywords": [
            "simple",
            "essential",
            "pure",
            "clean",
            "minimal"
        ],
        "style_guidelines": "Use concise language. Focus on essentials only.",
        "emoji_usage": "rare",
        "sentence_structure": "concise",
        "typical_phrases": [
            "Simply",
            "Just",
            "Essential",
            "Pure and simple"
        ]
    },
    "luxurious": {
        "description": "Premium, elegant, and sophisticated",
        "keywords": [
            "luxury",
            "premium",
            "exclusive",
            "elegant",
            "refined"
        ],
        "style_guidelines": "Use sophisticated language. Emphasize quality and exclusivity.",
        "emoji_usage": "minimal",
        "sentence_structure": "refined",
        "typical_phrases": [
            "Exquisite",
            "Premium quality",
            "Exclusively",
            "Refined elegance"
        ]
    },
    "quirky": {
        "description": "Unconventional, unique, and eccentric",
        "keywords": [
            "unique",
            "different",
            "unusual",
            "peculiar",
            "offbeat"
        ],
        "style_guidelines": "Be unconventional. Don't follow typical patterns.",
        "emoji_usage": "creative",
        "sentence_structure": "unconventional",
        "typical_phrases": [
            "Here's something different",
            "Quirky but cool",
            "Unusually",
            "Offbeat"
        ]
    },
    "Horticulture/Border": {
        "description": "Tactful, balanced, and considerate",
        "keywords": [
            "balanced",
            "considerate",
            "thoughtful",
            "respectful",
            "measured"
        ],
        "style_guidelines": "Present all sides. Use diplomatic language.",
        "emoji_usage": "none",
        "sentence_structure": "balanced",
        "typical_phrases": [
            "On one hand",
            "Considering all",
            "Respectfully",
            "Balanced view"
        ]
    },
    "rebellious": {
        "description": "Defiant, challenging, and revolutionary",
        "keywords": [
            "rebel",
            "challenge",
            "disrupt",
            "revolution",
            "break"
        ],
        "style_guidelines": "Challenge norms. Use provocative language.",
        "emoji_usage": "strategic",
        "sentence_structure": "challenging",
        "typical_phrases": [
            "Break the rules",
            "Challenge everything",
            "Rebel against",
            "Disrupt the"
        ]
    },
    "Disaster/Infra Alert": {
        "description": "Encouraging, helpful, and nurturing",
        "keywords": [
            "support",
            "help",
            "encourage",
            "guide",
            "assist"
        ],
        "style_guidelines": "Offer help and encouragement. Be resourceful.",
        "emoji_usage": "moderate",
        "sentence_structure": "helpful",
        "typical_phrases": [
            "We're here to help",
            "Let us support",
            "We've got you",
            "Together we'll"
        ]
    }
}


def get_tone_characteristics(tone: str) -> Dict[str, any]:
    """
    Get characteristics for a specific tone

    Args:
        tone: The tone identifier (e.g., 'professional', 'casual') - can be old or new format

    Returns:
        Dictionary containing tone characteristics
    """
    # Map old tone key to new display name if needed
    mapped_tone = TONE_MAPPING.get(tone.lower(), tone)

    # Get characteristics using the mapped name
    return TONE_CHARACTERISTICS.get(mapped_tone, TONE_CHARACTERISTICS.get("Official News", {}))


def get_all_tones() -> List[str]:
    """Get list of all available tones"""
    return list(TONE_CHARACTERISTICS.keys())


def get_tone_description(tone: str) -> str:
    """Get brief description of a tone"""
    characteristics = get_tone_characteristics(tone)
    return characteristics.get("description", "")


def get_tone_style_guide(tone: str) -> str:
    """Get style guidelines for a tone"""
    characteristics = get_tone_characteristics(tone)
    return characteristics.get("style_guidelines", "")


def format_tone_for_prompt(tone: str) -> str:
    """
    Format tone characteristics into a prompt-friendly string

    Args:
        tone: The tone identifier

    Returns:
        Formatted string describing the tone for use in AI prompts
    """
    characteristics = get_tone_characteristics(tone)

    prompt_parts = [
        f"Tone: {tone.upper()}",
        f"Description: {characteristics['description']}",
        f"Style Guidelines: {characteristics['style_guidelines']}",
        f"Key Words: {', '.join(characteristics['keywords'][:5])}",
        f"Emoji Usage: {characteristics['emoji_usage']}",
    ]

    if characteristics.get('typical_phrases'):
        prompt_parts.append(f"Typical Phrases: {', '.join(characteristics['typical_phrases'][:3])}")

    return "\n".join(prompt_parts)
