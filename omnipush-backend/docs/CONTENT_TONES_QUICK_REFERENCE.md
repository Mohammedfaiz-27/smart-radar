# Content Tones - Quick Reference

## All 38 Available Tones

| # | Tone | Description | Emoji Usage | Best For |
|---|------|-------------|-------------|----------|
| 1 | professional | Business-appropriate, polished, and competent | minimal | Corporate communications, B2B |
| 2 | casual | Relaxed, easygoing, and approachable | moderate | Lifestyle brands, everyday content |
| 3 | friendly | Warm, welcoming, and personable | moderate | Customer service, community building |
| 4 | humorous | Funny, witty, and entertaining | frequent | Entertainment brands, engagement |
| 5 | formal | Official, proper, and ceremonious | none | Legal content, official statements |
| 6 | enthusiastic | Energetic, excited, and passionate | frequent | Product launches, celebrations |
| 7 | inspirational | Uplifting, motivating, and aspirational | moderate | Motivational content, success stories |
| 8 | informative | Educational, factual, and knowledge-focused | minimal | Tutorials, how-to guides |
| 9 | conversational | Dialogue-like, interactive, and engaging | moderate | Q&A content, discussions |
| 10 | authoritative | Expert, commanding, and credible | none | Thought leadership, expert insights |
| 11 | empathetic | Understanding, compassionate, and supportive | moderate | Customer support, sensitive topics |
| 12 | persuasive | Convincing, compelling, and action-oriented | strategic | Sales content, CTAs |
| 13 | educational | Teaching-focused, instructive, and clarifying | minimal | Training materials, guides |
| 14 | entertaining | Engaging, amusing, and captivating | frequent | Entertainment content, viral posts |
| 15 | motivational | Encouraging, empowering, and action-driving | moderate | Fitness, self-improvement |
| 16 | urgent | Time-sensitive, immediate, and pressing | strategic | Limited offers, breaking news |
| 17 | calm | Peaceful, soothing, and tranquil | minimal | Wellness content, meditation |
| 18 | playful | Fun, lighthearted, and whimsical | frequent | Games, fun content |
| 19 | serious | Grave, important, and thoughtful | none | Important announcements |
| 20 | witty | Clever, sharp, and intellectually humorous | moderate | Smart humor, thought-provoking |
| 21 | compassionate | Caring, kind, and understanding | moderate | Healthcare, social causes |
| 22 | bold | Daring, confident, and fearless | strategic | Disruptive brands, bold statements |
| 23 | confident | Self-assured, certain, and assured | minimal | Product guarantees, expertise |
| 24 | humble | Modest, unpretentious, and grounded | minimal | Thank you messages, acknowledgments |
| 25 | authentic | Genuine, real, and transparent | natural | Behind-the-scenes, honest updates |
| 26 | storytelling | Narrative-driven, engaging, and descriptive | strategic | Brand stories, case studies |
| 27 | analytical | Data-driven, logical, and systematic | none | Reports, data insights |
| 28 | emotional | Feeling-focused, heartfelt, and touching | frequent | Emotional appeals, personal stories |
| 29 | rational | Logical, reasonable, and pragmatic | none | Problem-solving, logical arguments |
| 30 | trendy | Current, fashionable, and modern | frequent | Fashion, pop culture |
| 31 | nostalgic | Reminiscent, sentimental, and reflective | minimal | Throwback content, brand heritage |
| 32 | futuristic | Forward-looking, innovative, and cutting-edge | moderate | Tech content, innovation |
| 33 | minimalist | Simple, clean, and essential | rare | Design content, simple living |
| 34 | luxurious | Premium, elegant, and sophisticated | minimal | Luxury brands, premium products |
| 35 | quirky | Unconventional, unique, and eccentric | creative | Creative brands, unique products |
| 36 | diplomatic | Tactful, balanced, and considerate | none | Sensitive topics, balanced opinions |
| 37 | rebellious | Defiant, challenging, and revolutionary | strategic | Disruptive brands, challenging norms |
| 38 | supportive | Encouraging, helpful, and nurturing | moderate | Support content, help resources |

## Emoji Usage Levels

- **none**: No emojis
- **rare**: 1 emoji max
- **minimal**: 1-2 emojis
- **moderate**: 2-4 emojis
- **frequent**: 4+ emojis
- **strategic**: Emojis placed for maximum impact
- **natural**: Emojis used naturally as in conversation
- **creative**: Unique or unconventional emoji usage

## Platform Recommendations

### Facebook
`friendly` `conversational` `inspirational` `storytelling` `empathetic`

### Instagram
`trendy` `playful` `inspirational` `luxurious` `entertaining`

### LinkedIn
`professional` `authoritative` `analytical` `educational` `confident`

### Twitter/X
`witty` `casual` `bold` `urgent` `conversational`

### WhatsApp
`friendly` `conversational` `supportive` `casual` `empathetic`

## Content Type Recommendations

### News Posts
`informative` `serious` `authoritative` `analytical` `professional`

### Promotional Content
`persuasive` `enthusiastic` `urgent` `bold` `confident`

### Community Engagement
`friendly` `empathetic` `supportive` `conversational` `warm`

### Educational Content
`educational` `informative` `professional` `analytical` `clear`

### Entertainment Posts
`humorous` `playful` `entertaining` `quirky` `witty`

## API Usage

### Setting Tone on Social Account
```json
POST /v1/social-accounts/connect
{
  "platform": "whatsapp",
  "account_name": "Community Channel",
  "content_tone": "friendly",
  "custom_instructions": "Focus on local community news"
}
```

### Updating Account Tone
```json
PATCH /v1/social-accounts/{account_id}
{
  "content_tone": "inspirational",
  "custom_instructions": "Add motivational elements"
}
```

### Getting AI Suggestions with Tone
```json
POST /v1/ai/suggestions
{
  "prompt": "New community center opening",
  "platform": "facebook",
  "tone": "enthusiastic"
}
```

## Tone Combinations (Future Feature)

Potential tone combinations for mixed styles:
- `professional` + `friendly` = Professional yet approachable
- `informative` + `entertaining` = Edutainment
- `inspirational` + `analytical` = Data-driven motivation
- `casual` + `authoritative` = Expert but accessible

## Quick Selection Guide

**Need to sound professional?** → `professional`, `formal`, `authoritative`

**Want more engagement?** → `conversational`, `friendly`, `playful`

**Selling something?** → `persuasive`, `urgent`, `confident`

**Sharing knowledge?** → `educational`, `informative`, `analytical`

**Building community?** → `friendly`, `empathetic`, `supportive`

**Being creative?** → `quirky`, `playful`, `entertaining`

**Showing expertise?** → `authoritative`, `analytical`, `professional`

**Connecting emotionally?** → `emotional`, `inspirational`, `compassionate`

## Testing Tones

Use the test endpoint to see how different tones affect your content:

```bash
curl -X POST http://localhost:8000/v1/ai/suggestions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "prompt": "Your content here",
    "platform": "facebook",
    "tone": "inspirational"
  }'
```

## Programmatic Access

```python
from config.tone_characteristics import (
    get_all_tones,
    get_tone_characteristics,
    get_tone_description
)

# Get all available tones
all_tones = get_all_tones()
print(f"Total tones: {len(all_tones)}")  # 38

# Get characteristics for a specific tone
tone_info = get_tone_characteristics("inspirational")
print(tone_info["description"])
print(tone_info["keywords"])

# Get just the description
desc = get_tone_description("witty")
print(desc)  # "Clever, sharp, and intellectually humorous"
```

## Migration Notes

If you were using one of the original 6 tones:
- ✅ `professional`, `casual`, `friendly`, `humorous`, `formal`, `enthusiastic` - No changes needed
- All existing code and data will continue to work
- New tones add more options without breaking existing functionality

## Performance Tips

1. Choose one primary tone per social account for consistency
2. Use custom instructions for specific requirements
3. Test different tones to find what resonates with your audience
4. Monitor engagement metrics by tone
5. Adjust tones based on content type and platform

## Support

- 📖 Full Guide: `docs/CONTENT_TONES_GUIDE.md`
- 🔧 Implementation: `config/tone_characteristics.py`
- 💬 API Reference: API documentation
- 🐛 Issues: Submit via GitHub
