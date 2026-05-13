# AI Prompt Testing Tool Documentation

This directory contains testing tools for the various AI prompts and content generation features in the OmniPush backend.

## Files

- `test_ai_prompts.py` - Interactive testing tool with menu system
- `test_ai_prompts_simple.py` - Command-line testing tool for automation

## Available AI Features to Test

### 1. Content Suggestions
Generate social media content suggestions for different platforms with various tones (professional, casual, enthusiastic).

### 2. Content Optimization
Optimize content when switching between platforms (e.g., Facebook to Twitter).

### 3. Content Moderation
Check content for appropriateness, hate speech, violence, spam, etc.

### 4. City Research
Generate comprehensive research about cities including demographics, economy, culture (outputs in Tamil).

### 5. Channel Adaptation
Adapt content for specific social media channels with platform-specific tone and style.

### 6. News to Post Conversion
Convert news articles into engaging social media posts.

### 7. Image Prompt Enhancement
Enhance simple descriptions into detailed prompts for AI image generation (DALL-E 3).

### 8. Multi-Perspective Analysis
Analyze topics from multiple perspectives (academic, business, historical, social, critical).

### 9. Batch Channel Adaptation
Adapt content for multiple channels simultaneously in a single operation.

## Usage

### Interactive Mode (test_ai_prompts.py)

```bash
# Run the interactive tool
uv run python test_ai_prompts.py

# You'll get a menu to choose which test to run
# Follow the prompts to enter your test content
```

### Command-Line Mode (test_ai_prompts_simple.py)

```bash
# Run all tests with default content
uv run python test_ai_prompts_simple.py

# Test specific features with custom content
uv run python test_ai_prompts_simple.py suggestions "Your content here"
uv run python test_ai_prompts_simple.py optimize "Content to optimize"
uv run python test_ai_prompts_simple.py moderation "Content to check"
uv run python test_ai_prompts_simple.py city "Chennai"
uv run python test_ai_prompts_simple.py adapt "Breaking news content"
uv run python test_ai_prompts_simple.py news "Article headline"
uv run python test_ai_prompts_simple.py image "sunset over mountains"
uv run python test_ai_prompts_simple.py multi "artificial intelligence"
uv run python test_ai_prompts_simple.py batch "Content for all platforms"
```

### Command Aliases

- `suggestions`, `suggest` - Content suggestions
- `optimize`, `opt` - Content optimization
- `moderation`, `moderate`, `mod` - Content moderation
- `city`, `research` - City research
- `adapt`, `adaptation` - Channel adaptation
- `news`, `news2post` - News to post conversion
- `image`, `img` - Image prompt enhancement
- `multi`, `perspective` - Multi-perspective analysis
- `batch`, `batch-adapt` - Batch adaptation

## Examples

### Test Content Suggestions for a Product Launch
```bash
uv run python test_ai_prompts_simple.py suggestions "Launching our new eco-friendly water bottle"
```

### Optimize Long Content for Twitter
```bash
uv run python test_ai_prompts_simple.py optimize "We are absolutely thrilled to announce that after months of hard work and dedication, our team has finally launched the most innovative product in the market that will revolutionize how people think about sustainability"
```

### Check Content for Moderation Issues
```bash
uv run python test_ai_prompts_simple.py moderation "Check out this amazing offer - click here now!"
```

### Generate Research About a City
```bash
uv run python test_ai_prompts_simple.py city "Mumbai"
```

### Adapt Content for Instagram
```bash
uv run python test_ai_prompts_simple.py adapt "Breaking: Scientists discover new renewable energy source"
```

### Convert News to Social Post
```bash
uv run python test_ai_prompts_simple.py news "Tech giant announces 50% reduction in carbon emissions through new green data centers"
```

### Enhance Image Generation Prompt
```bash
uv run python test_ai_prompts_simple.py image "corporate team meeting"
```

### Multi-Perspective Analysis
```bash
uv run python test_ai_prompts_simple.py multi "impact of remote work on productivity"
```

### Batch Adapt for All Platforms
```bash
uv run python test_ai_prompts_simple.py batch "We just hit 1 million users! Thank you for your amazing support!"
```

## Configuration

### Environment Variables

Make sure your `.env` file contains:
```
OPENAI_API_KEY=your_api_key_here
```

If the OpenAI API key is not configured, the tools will:
- Show the prompts that would be sent
- Use fallback/mock implementations where available
- Display rule-based results for moderation

## Output

The testing tools will display:
1. The prompts being sent to the AI
2. The AI's response (if API is configured)
3. Any relevant metadata (character counts, confidence scores, etc.)

## Platform Guidelines

The tools use platform-specific guidelines for content optimization:

- **Facebook**: 2000 chars, friendly/conversational, storytelling focus
- **Instagram**: 2200 chars, visual-first, 5-10 hashtags
- **Twitter**: 280 chars, concise/witty, 1-2 hashtags
- **LinkedIn**: 3000 chars, professional, industry-focused
- **WhatsApp**: 500 chars, personal, intimate tone

## Prompt Sources

The testing tools use prompts from:
- `/config/prompts.py` - Centralized prompt configurations
- `/api/v1/ai.py` - AI endpoint implementations
- `/services/content_service.py` - Content generation services
- `/services/moderation_service.py` - Content moderation
- `/services/content_adaptation_service.py` - Channel adaptation

## Troubleshooting

### Import Errors
If you get import errors, make sure you're in the backend directory:
```bash
cd omnipush-backend
```

### Missing Dependencies
Install required packages:
```bash
uv add rich openai
```

### API Errors
- Check your OpenAI API key is valid
- Ensure you have sufficient API credits
- Check network connectivity

## Extending the Tests

To add new test cases:

1. Add a new test method to the tester class
2. Define the prompt structure
3. Add command-line handling in the main function
4. Document the new test in this file

Example:
```python
async def test_new_feature(self, content: str = "default"):
    """Test new AI feature"""
    prompt = f"Your prompt here: {content}"
    # Implementation...
```