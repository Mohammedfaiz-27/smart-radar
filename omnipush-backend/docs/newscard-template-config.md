# News Card Template Configuration

This document explains the configuration options for news card generation in the OmniPush backend.

## Environment Variables

### Template Generation Mode

Add these environment variables to your `.env` file:

```bash
# Option 1: Use LLM to generate new templates (default: false)
ENABLE_LLM_HTML_GENERATION=true

# Option 2: Use the exact sample_newscard.html template (default: false)  
USE_EXACT_NEWSCARD_TEMPLATE=true
```

**Note:** If both are set to `true`, `USE_EXACT_NEWSCARD_TEMPLATE` takes precedence.

## Template Modes

### 1. Exact Template Mode (`USE_EXACT_NEWSCARD_TEMPLATE=true`)
- Uses the exact `sample_newscard.html` template
- Content is automatically fitted to the limited space (max 200 characters)
- Tone-based styling is applied based on social channel
- Channel-specific content adaptation
- Template colors change based on tone settings

### 2. LLM Generation Mode (`ENABLE_LLM_HTML_GENERATION=true`)
- Uses OpenAI to generate new HTML templates
- More creative and varied designs
- Still applies content adaptation and tone settings
- Uses `sample_newscard.html` as reference for the LLM

### 3. Fallback Mode (both `false`)
- Uses basic template generation
- Simple, consistent design
- No advanced tone or channel adaptation

## Content Adaptation

When calling the news card generation API, you can provide a `content_adaptation` object:

```json
{
  "content_adaptation": {
    "channel_name": "facebook",
    "tone": "professional",
    "style": "modern",
    "color_scheme": "default",
    "custom_instructions": "Make it suitable for Tamil audience"
  }
}
```

## Channel-Specific Tone Settings

The system automatically applies channel-specific tones:

- **Facebook**: Conversational, community-focused
- **Instagram**: Visual, trendy with emojis
- **Twitter**: Concise, punchy
- **LinkedIn**: Professional, business-oriented  
- **WhatsApp**: Personal, intimate

## Content Fitting

In exact template mode, content is automatically:
- Trimmed to fit within 200 characters
- Split at sentence boundaries when possible
- Truncated with "..." if needed
- Optimized for the newscard display area

## Tone-Based Styling

Available tones with corresponding color schemes:

- **Professional**: Blues and grays (#1a365d, #2d3748)
- **Casual**: Warm oranges and reds (#742a2a, #c53030)
- **Modern**: Purples (#553c9a, #805ad5)
- **Energetic**: Bright oranges (#c05621, #dd6b20)
- **Calm**: Soothing grays (#2d3748, #4a5568)

## API Response

The news card generation API returns additional metadata:

```json
{
  "url": "https://...",
  "filename": "screenshot_20250824_143022_123.png",
  "path": "/path/to/file",
  "s3_key": "tenant_id/screenshots/filename.png",
  "template_mode": "exact_template|llm_generated|fallback",
  "llm_generated": false,
  "exact_template_used": true,
  "content_adapted": true,
  "tone_applied": "professional"
}
```

## File Requirements

- Ensure `sample_newscard.html` exists in the backend root directory
- Template uses 1080x1080 dimensions optimized for social media
- Font size automatically adjusts via JavaScript in the template

## Usage Examples

### Enable Exact Template Mode
```bash
USE_EXACT_NEWSCARD_TEMPLATE=true
ENABLE_LLM_HTML_GENERATION=false
```

### Enable LLM Generation Mode  
```bash
USE_EXACT_NEWSCARD_TEMPLATE=false
ENABLE_LLM_HTML_GENERATION=true
```

### Use Fallback Mode
```bash
USE_EXACT_NEWSCARD_TEMPLATE=false
ENABLE_LLM_HTML_GENERATION=false
```