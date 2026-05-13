# Content Tones Guide - 38 Tones for Enhanced Social Media Content

## Overview

OmniPush now supports 38 different content tones for AI-powered content generation. Each tone has specific characteristics, style guidelines, and use cases that help create more engaging and platform-appropriate content.

## How to Use Content Tones

### In Social Account Settings

When editing a social account (via Edit Social Accounts screen), you can:

1. Select a **Content Tone** from 38 available options
2. Add **Custom Instructions** for additional content customization
3. The AI will use both the tone characteristics and custom instructions when generating content

### API Usage

```python
# When connecting or updating a social account
{
  "content_tone": "inspirational",  # Choose from 38 tones
  "custom_instructions": "Focus on local community impact"
}
```

## Complete Tone Reference

### Original Tones (6)

#### 1. **Professional**
- **Description**: Business-appropriate, polished, and competent
- **Best For**: Corporate communications, B2B content, official announcements
- **Style**: Clear, concise language. Formal sentence structure.
- **Emoji Usage**: Minimal
- **Example Keywords**: efficient, expert, quality, reliable, trusted

#### 2. **Casual**
- **Description**: Relaxed, easygoing, and approachable
- **Best For**: Lifestyle brands, everyday content, friendly updates
- **Style**: Everyday language, contractions encouraged
- **Emoji Usage**: Moderate
- **Example Keywords**: easy, simple, chill, laid-back, no-fuss

#### 3. **Friendly**
- **Description**: Warm, welcoming, and personable
- **Best For**: Customer service, community building, welcome messages
- **Style**: Warm and inviting, direct address to reader
- **Emoji Usage**: Moderate
- **Example Keywords**: welcome, happy, together, community, caring

#### 4. **Humorous**
- **Description**: Funny, witty, and entertaining
- **Best For**: Entertainment brands, light content, engagement posts
- **Style**: Wordplay, puns, light humor
- **Emoji Usage**: Frequent
- **Example Keywords**: fun, laugh, hilarious, amusing, playful

#### 5. **Formal**
- **Description**: Official, proper, and ceremonious
- **Best For**: Legal content, official statements, ceremonial announcements
- **Style**: Complete sentences, no contractions, proper grammar essential
- **Emoji Usage**: None
- **Example Keywords**: official, proper, respectful, dignified, ceremonial

#### 6. **Enthusiastic**
- **Description**: Energetic, excited, and passionate
- **Best For**: Product launches, exciting news, celebration posts
- **Style**: High energy, exclamation points
- **Emoji Usage**: Frequent
- **Example Keywords**: amazing, incredible, awesome, fantastic, exciting

### Expanded Tones (32 Additional)

#### 7. **Inspirational**
- **Description**: Uplifting, motivating, and aspirational
- **Best For**: Motivational content, success stories, goal-oriented posts
- **Emoji Usage**: Moderate
- **Keywords**: dream, achieve, believe, possible, inspire

#### 8. **Informative**
- **Description**: Educational, factual, and knowledge-focused
- **Best For**: Educational content, tutorials, how-to guides
- **Emoji Usage**: Minimal
- **Keywords**: learn, discover, understand, know, explore

#### 9. **Conversational**
- **Description**: Dialogue-like, interactive, and engaging
- **Best For**: Q&A content, discussions, community engagement
- **Emoji Usage**: Moderate
- **Keywords**: talk, chat, discuss, share, connect

#### 10. **Authoritative**
- **Description**: Expert, commanding, and credible
- **Best For**: Thought leadership, expert insights, industry analysis
- **Emoji Usage**: None
- **Keywords**: expert, proven, established, authority, definitive

#### 11. **Empathetic**
- **Description**: Understanding, compassionate, and supportive
- **Best For**: Customer support, crisis communication, sensitive topics
- **Emoji Usage**: Moderate
- **Keywords**: understand, support, care, compassion, together

#### 12. **Persuasive**
- **Description**: Convincing, compelling, and action-oriented
- **Best For**: Sales content, CTAs, conversion-focused posts
- **Emoji Usage**: Strategic
- **Keywords**: best, proven, guarantee, results, transform

#### 13. **Educational**
- **Description**: Teaching-focused, instructive, and clarifying
- **Best For**: Training materials, step-by-step guides, tutorials
- **Emoji Usage**: Minimal
- **Keywords**: learn, master, guide, tutorial, lesson

#### 14. **Entertaining**
- **Description**: Engaging, amusing, and captivating
- **Best For**: Entertainment content, viral posts, engagement-focused content
- **Emoji Usage**: Frequent
- **Keywords**: fun, exciting, engaging, enjoy, delight

#### 15. **Motivational**
- **Description**: Encouraging, empowering, and action-driving
- **Best For**: Fitness content, self-improvement, achievement posts
- **Emoji Usage**: Moderate
- **Keywords**: achieve, success, power, overcome, victory

#### 16. **Urgent**
- **Description**: Time-sensitive, immediate, and pressing
- **Best For**: Limited-time offers, breaking news, urgent updates
- **Emoji Usage**: Strategic
- **Keywords**: now, today, hurry, limited, deadline

#### 17. **Calm**
- **Description**: Peaceful, soothing, and tranquil
- **Best For**: Wellness content, meditation, stress-relief topics
- **Emoji Usage**: Minimal
- **Keywords**: peace, serene, gentle, quiet, relaxed

#### 18. **Playful**
- **Description**: Fun, lighthearted, and whimsical
- **Best For**: Games, fun content, creative posts
- **Emoji Usage**: Frequent
- **Keywords**: fun, play, joy, silly, whimsy

#### 19. **Serious**
- **Description**: Grave, important, and thoughtful
- **Best For**: Important announcements, serious discussions, policy content
- **Emoji Usage**: None
- **Keywords**: important, critical, significant, matter, concern

#### 20. **Witty**
- **Description**: Clever, sharp, and intellectually humorous
- **Best For**: Smart humor, intellectual content, thought-provoking posts
- **Emoji Usage**: Moderate
- **Keywords**: clever, smart, quick, sharp, brilliant

#### 21. **Compassionate**
- **Description**: Caring, kind, and understanding
- **Best For**: Healthcare content, social causes, support messages
- **Emoji Usage**: Moderate
- **Keywords**: care, kindness, heart, gentle, support

#### 22. **Bold**
- **Description**: Daring, confident, and fearless
- **Best For**: Disruptive brands, bold statements, challenging norms
- **Emoji Usage**: Strategic
- **Keywords**: brave, fearless, dare, bold, confident

#### 23. **Confident**
- **Description**: Self-assured, certain, and assured
- **Best For**: Product guarantees, expertise showcase, strong positioning
- **Emoji Usage**: Minimal
- **Keywords**: certain, proven, guaranteed, sure, definite

#### 24. **Humble**
- **Description**: Modest, unpretentious, and grounded
- **Best For**: Thank you messages, acknowledging community, modest wins
- **Emoji Usage**: Minimal
- **Keywords**: grateful, honored, fortunate, blessed, thankful

#### 25. **Authentic**
- **Description**: Genuine, real, and transparent
- **Best For**: Behind-the-scenes content, honest updates, transparent communication
- **Emoji Usage**: Natural
- **Keywords**: real, honest, genuine, true, transparent

#### 26. **Storytelling**
- **Description**: Narrative-driven, engaging, and descriptive
- **Best For**: Brand stories, case studies, customer journeys
- **Emoji Usage**: Strategic
- **Keywords**: story, journey, adventure, tale, chapter

#### 27. **Analytical**
- **Description**: Data-driven, logical, and systematic
- **Best For**: Reports, data insights, technical analysis
- **Emoji Usage**: None
- **Keywords**: data, analysis, metrics, statistics, insights

#### 28. **Emotional**
- **Description**: Feeling-focused, heartfelt, and touching
- **Best For**: Emotional appeals, heartfelt messages, personal stories
- **Emoji Usage**: Frequent
- **Keywords**: feel, heart, emotion, soul, passion

#### 29. **Rational**
- **Description**: Logical, reasonable, and pragmatic
- **Best For**: Problem-solving content, logical arguments, practical advice
- **Emoji Usage**: None
- **Keywords**: logical, practical, sensible, reasonable, pragmatic

#### 30. **Trendy**
- **Description**: Current, fashionable, and modern
- **Best For**: Fashion content, pop culture, trending topics
- **Emoji Usage**: Frequent
- **Keywords**: trending, viral, hot, latest, buzz

#### 31. **Nostalgic**
- **Description**: Reminiscent, sentimental, and reflective
- **Best For**: Throwback content, brand heritage, memory-focused posts
- **Emoji Usage**: Minimal
- **Keywords**: remember, classic, vintage, throwback, memories

#### 32. **Futuristic**
- **Description**: Forward-looking, innovative, and cutting-edge
- **Best For**: Tech content, innovation announcements, future-focused topics
- **Emoji Usage**: Moderate
- **Keywords**: future, tomorrow, innovation, next-gen, revolutionary

#### 33. **Minimalist**
- **Description**: Simple, clean, and essential
- **Best For**: Design content, simple living, essential products
- **Emoji Usage**: Rare
- **Keywords**: simple, essential, pure, clean, minimal

#### 34. **Luxurious**
- **Description**: Premium, elegant, and sophisticated
- **Best For**: Luxury brands, premium products, high-end services
- **Emoji Usage**: Minimal
- **Keywords**: luxury, premium, exclusive, elegant, refined

#### 35. **Quirky**
- **Description**: Unconventional, unique, and eccentric
- **Best For**: Creative brands, unique products, unconventional approaches
- **Emoji Usage**: Creative
- **Keywords**: unique, different, unusual, peculiar, offbeat

#### 36. **Diplomatic**
- **Description**: Tactful, balanced, and considerate
- **Best For**: Sensitive topics, balanced opinions, mediation content
- **Emoji Usage**: None
- **Keywords**: balanced, considerate, thoughtful, respectful, measured

#### 37. **Rebellious**
- **Description**: Defiant, challenging, and revolutionary
- **Best For**: Disruptive brands, challenging status quo, revolutionary products
- **Emoji Usage**: Strategic
- **Keywords**: rebel, challenge, disrupt, revolution, break

#### 38. **Supportive**
- **Description**: Encouraging, helpful, and nurturing
- **Best For**: Support content, help resources, community assistance
- **Emoji Usage**: Moderate
- **Keywords**: support, help, encourage, guide, assist

## Choosing the Right Tone

### By Platform

**Facebook**: Friendly, Conversational, Inspirational, Storytelling
**Instagram**: Trendy, Playful, Inspirational, Luxurious
**LinkedIn**: Professional, Authoritative, Analytical, Educational
**Twitter**: Witty, Casual, Bold, Urgent
**WhatsApp**: Friendly, Personal, Conversational, Supportive

### By Content Type

**News**: Informative, Serious, Authoritative, Analytical
**Promotions**: Persuasive, Enthusiastic, Urgent, Bold
**Community**: Friendly, Empathetic, Supportive, Conversational
**Educational**: Educational, Informative, Professional, Analytical
**Entertainment**: Humorous, Playful, Entertaining, Quirky

### By Audience

**B2B**: Professional, Authoritative, Analytical, Confident
**B2C**: Friendly, Casual, Enthusiastic, Trendy
**Youth**: Trendy, Playful, Rebellious, Quirky
**Seniors**: Calm, Nostalgic, Supportive, Empathetic

## Technical Implementation

### Tone Characteristics File
Location: `config/tone_characteristics.py`

Each tone has:
- **description**: Brief explanation of the tone
- **keywords**: Key words that embody the tone
- **style_guidelines**: How to write in this tone
- **emoji_usage**: Level of emoji usage
- **sentence_structure**: Type of sentence structure
- **typical_phrases**: Common phrases for this tone

### Content Adaptation Service
Location: `services/content_adaptation_service.py`

The service:
1. Retrieves tone characteristics for each channel
2. Includes tone guidelines in AI prompts
3. Generates content that matches the specified tone
4. Validates tone consistency in outputs

### API Integration

All content generation endpoints now support tone selection:
- `/v1/social-accounts` - Set default tone per account
- `/v1/posts` - Content adapted based on account tone
- `/v1/ai/suggestions` - Tone-aware content suggestions

## Best Practices

### 1. **Match Tone to Context**
Choose tones that align with your content purpose and audience expectations

### 2. **Combine with Custom Instructions**
Use custom instructions to add specific requirements beyond the tone

### 3. **Test Different Tones**
Experiment with various tones to find what resonates with your audience

### 4. **Consider Platform Norms**
Choose tones that fit the platform's culture and user expectations

### 5. **Maintain Brand Consistency**
Select tones that align with your overall brand voice

### 6. **Adapt by Content Type**
Use different tones for different content types (news vs promotions)

### 7. **Monitor Engagement**
Track which tones drive better engagement on each platform

## Examples

### Professional Tone
**Input**: "New product launch tomorrow"
**Output**: "We are pleased to announce the official launch of our new product tomorrow. Our team has worked diligently to ensure quality and reliability."

### Enthusiastic Tone
**Input**: "New product launch tomorrow"
**Output**: "🎉 We're SO excited! Our amazing new product launches TOMORROW! Can't wait for you to see what we've created! 🚀"

### Witty Tone
**Input**: "New product launch tomorrow"
**Output**: "Plot twist: Tomorrow, everything changes. (Spoiler: It's our new product. And it's brilliant.) 🧠"

### Inspirational Tone
**Input**: "New product launch tomorrow"
**Output**: "Dream big, achieve more. Tomorrow, we unveil a product that will help you reach new heights. Your journey to success starts here. 🌟"

## Support

For questions or issues with content tones:
- Check tone characteristics in `config/tone_characteristics.py`
- Review examples in this guide
- Test different tones through the API
- Contact the development team for custom tone requirements

## Future Enhancements

- Tone mixing (combine multiple tones)
- Custom tone creation
- Tone A/B testing
- Performance analytics by tone
- Industry-specific tone presets
