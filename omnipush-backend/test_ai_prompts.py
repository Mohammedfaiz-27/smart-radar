#!/usr/bin/env python
"""
AI Prompt Testing Tool for OmniPush Backend
============================================
This tool allows testing various AI prompts and content generation features
available in the OmniPush backend.

Usage:
    python test_ai_prompts.py
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax

# Load environment variables
load_dotenv()

# Import backend services and models
from config.prompts import Prompts
from services.content_service import ContentService
from services.moderation_service import ModerationService
from services.news_service import NewsService
from services.content_adaptation_service import ContentAdaptationService
from models.content import Platform
from models.ai import ContentTone

console = Console()

class AIPromptTester:
    """Test various AI prompts and content generation features"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.content_service = ContentService()
        self.moderation_service = ModerationService()
        self.adaptation_service = ContentAdaptationService()

    async def test_content_suggestions(self):
        """Test AI content suggestions generation"""
        console.print("\n[bold cyan]Testing Content Suggestions[/bold cyan]")

        content = Prompt.ask("Enter content topic/prompt")
        platform = Prompt.ask("Platform", choices=["facebook", "instagram", "twitter", "linkedin", "youtube"], default="facebook")
        tone = Prompt.ask("Tone", choices=["professional", "casual", "enthusiastic"], default="professional")

        if not self.client:
            console.print("[yellow]OpenAI client not configured, using mock data[/yellow]")
            return

        # Build prompt
        system_message = f"You are a social media content creator. Generate engaging content with a {tone} tone."

        guidelines = self._get_platform_guidelines(platform)
        system_message += f"\n\nPlatform: {platform}\n"
        system_message += f"Style guidelines: {guidelines['style']}\n"
        system_message += f"Features: {guidelines['features']}\n"
        system_message += f"Max length: {guidelines['max_length']} characters\n"
        system_message += "\n\nGenerate 3 different variations of the content. Each should be unique and engaging."

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Create social media content about: {content}"}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            result = response.choices[0].message.content
            console.print(Panel(result, title=f"Generated Content for {platform.upper()}", border_style="green"))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    async def test_content_optimization(self):
        """Test content optimization for different platforms"""
        console.print("\n[bold cyan]Testing Content Optimization[/bold cyan]")

        content = Prompt.ask("Enter content to optimize")
        source_platform = Prompt.ask("Source platform", choices=["facebook", "instagram", "twitter", "linkedin"], default="facebook")
        target_platform = Prompt.ask("Target platform", choices=["facebook", "instagram", "twitter", "linkedin"], default="twitter")

        if not self.client:
            console.print("[yellow]OpenAI client not configured[/yellow]")
            return

        source_guidelines = self._get_platform_guidelines(source_platform)
        target_guidelines = self._get_platform_guidelines(target_platform)

        system_message = f"""
        You are optimizing social media content from {source_platform} for {target_platform}.

        Source platform style: {source_guidelines['style']}
        Target platform style: {target_guidelines['style']}
        Target max length: {target_guidelines['max_length']} characters
        Target features: {target_guidelines['features']}

        Optimize the content while maintaining its core message and intent.
        Return only the optimized content, followed by a list of changes made.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Optimize this content: {content}"}
                ],
                max_tokens=500,
                temperature=0.5
            )

            result = response.choices[0].message.content
            console.print(Panel(result, title=f"Optimized for {target_platform.upper()}", border_style="green"))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    async def test_moderation(self):
        """Test content moderation"""
        console.print("\n[bold cyan]Testing Content Moderation[/bold cyan]")

        content = Prompt.ask("Enter content to moderate")

        if not self.client:
            console.print("[yellow]Using rule-based moderation (OpenAI not configured)[/yellow]")
            # Simple rule-based check
            inappropriate_words = ['hate', 'violence', 'abuse', 'spam']
            is_appropriate = not any(word in content.lower() for word in inappropriate_words)

            result = {
                "is_appropriate": is_appropriate,
                "confidence": 0.8,
                "issues": [] if is_appropriate else ["Potentially inappropriate content detected"],
                "suggestions": [] if is_appropriate else ["Consider rephrasing the content"]
            }
        else:
            prompt = f"""
            Analyze the following social media post for appropriateness:

            "{content}"

            Determine if it contains:
            - Hate speech or discrimination
            - Violence or harmful content
            - Spam or misleading information
            - Inappropriate language
            - Copyright violations

            Return a JSON response with:
            {{
                "is_appropriate": true/false,
                "confidence": 0.0-1.0,
                "issues": ["list of issues found"],
                "suggestions": ["list of suggestions for improvement"]
            }}
            """

            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a content moderation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )

                result = json.loads(response.choices[0].message.content)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return

        # Display results
        status = "[green]✓ Appropriate[/green]" if result['is_appropriate'] else "[red]✗ Not Appropriate[/red]"
        console.print(f"\nStatus: {status}")
        console.print(f"Confidence: {result['confidence']*100:.1f}%")

        if result.get('issues'):
            console.print("\n[yellow]Issues Found:[/yellow]")
            for issue in result['issues']:
                console.print(f"  • {issue}")

        if result.get('suggestions'):
            console.print("\n[cyan]Suggestions:[/cyan]")
            for suggestion in result['suggestions']:
                console.print(f"  • {suggestion}")

    async def test_city_research(self):
        """Test city research prompt"""
        console.print("\n[bold cyan]Testing City Research[/bold cyan]")

        city = Prompt.ask("Enter city name")

        messages = Prompts.get_city_research_messages(city)

        if not self.client:
            console.print("[yellow]OpenAI not configured, showing prompt only[/yellow]")
            console.print("\n[bold]System Prompt:[/bold]")
            console.print(messages[0]['content'])
            console.print("\n[bold]User Prompt:[/bold]")
            console.print(messages[1]['content'])
            return

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=1500
            )

            result = response.choices[0].message.content
            console.print(Panel(Markdown(result), title=f"Research: {city}", border_style="green"))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    async def test_channel_adaptation(self):
        """Test channel-specific content adaptation"""
        console.print("\n[bold cyan]Testing Channel Adaptation[/bold cyan]")

        content = Prompt.ask("Enter original content")
        channel = Prompt.ask("Target channel", choices=["facebook", "instagram", "twitter", "linkedin", "whatsapp"], default="instagram")

        # Get channel-specific settings
        channel_settings = Prompts.get_channel_tone_settings(channel)
        adaptation_prompt = Prompts.get_channel_adaptation_prompt(content, channel)

        console.print(f"\n[bold]Channel Settings for {channel.upper()}:[/bold]")
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        for key, value in channel_settings.items():
            table.add_row(key.title(), value)
        console.print(table)

        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": Prompts.CHANNEL_TONE_SYSTEM},
                        {"role": "user", "content": adaptation_prompt}
                    ],
                    max_tokens=500,
                    temperature=0.6
                )

                result = response.choices[0].message.content
                console.print(Panel(result, title=f"Adapted for {channel.upper()}", border_style="green"))

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("\n[bold]Adaptation Prompt:[/bold]")
            console.print(adaptation_prompt)

    async def test_news_to_post(self):
        """Test news article to social post conversion"""
        console.print("\n[bold cyan]Testing News to Post Conversion[/bold cyan]")

        article_title = Prompt.ask("Enter article title")
        article_content = Prompt.ask("Enter article content/summary")

        prompt = f"""
        Create an engaging social media post from this news article:

        Title: {article_title}
        Content: {article_content}

        Requirements:
        - Make it engaging and shareable
        - Include relevant emojis
        - Add 2-3 relevant hashtags
        - Keep it under 280 characters for cross-platform compatibility
        - Focus on the key takeaway or most interesting aspect
        """

        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a social media content creator specializing in news content."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )

                result = response.choices[0].message.content
                console.print(Panel(result, title="Generated Post", border_style="green"))
                console.print(f"[dim]Character count: {len(result)}[/dim]")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("\n[bold]Prompt that would be sent:[/bold]")
            console.print(prompt)

    async def test_image_prompt_enhancement(self):
        """Test image prompt enhancement for AI image generation"""
        console.print("\n[bold cyan]Testing Image Prompt Enhancement[/bold cyan]")

        content = Prompt.ask("Enter content/concept for image")
        style = Prompt.ask("Style", choices=["realistic", "cartoon", "illustration", "photography", "painting", "minimalist"], default="realistic")

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

        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Style: {style}\n\nEnhance this into an image prompt: {content}"}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )

                enhanced_prompt = response.choices[0].message.content
                console.print(Panel(enhanced_prompt, title="Enhanced Image Prompt", border_style="green"))

                # Show how it would be used with DALL-E
                console.print("\n[dim]This prompt would be sent to DALL-E 3 for image generation[/dim]")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("\n[bold]Enhancement System Prompt:[/bold]")
            console.print(system_message)

    async def test_multi_perspective_analysis(self):
        """Test multi-perspective research analysis"""
        console.print("\n[bold cyan]Testing Multi-Perspective Analysis[/bold cyan]")

        topic = Prompt.ask("Enter research topic")

        messages = Prompts.get_multi_perspective_messages(topic)

        if not self.client:
            console.print("[yellow]OpenAI not configured, showing prompts only[/yellow]")
            console.print("\n[bold]System Prompt:[/bold]")
            console.print(messages[0]['content'])
            console.print("\n[bold]User Prompt:[/bold]")
            console.print(messages[1]['content'])
            return

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=2000,
                temperature=0.6
            )

            result = response.choices[0].message.content
            console.print(Panel(Markdown(result), title=f"Multi-Perspective: {topic}", border_style="green"))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    async def test_batch_adaptation(self):
        """Test batch content adaptation for multiple channels"""
        console.print("\n[bold cyan]Testing Batch Channel Adaptation[/bold cyan]")

        content = Prompt.ask("Enter original content")

        channels = ["facebook", "instagram", "twitter", "linkedin", "whatsapp"]
        console.print(f"\nAdapting content for: {', '.join(channels)}")

        prompt = f"""
        Adapt the following content for multiple social media channels. Provide a JSON response with adaptations for each channel.

        Original content: "{content}"

        For each channel, consider:
        - Character limits (Twitter: 280, Instagram: 2200, Facebook: 2000, LinkedIn: 3000, WhatsApp: 500)
        - Audience expectations and tone
        - Platform-specific features (hashtags, mentions, emojis)

        Return JSON in this format:
        {{
            "facebook": {{"content": "...", "tone": "...", "hashtags": []}},
            "instagram": {{"content": "...", "tone": "...", "hashtags": []}},
            "twitter": {{"content": "...", "tone": "...", "hashtags": []}},
            "linkedin": {{"content": "...", "tone": "...", "hashtags": []}},
            "whatsapp": {{"content": "...", "tone": "...", "hashtags": []}}
        }}
        """

        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a social media content adaptation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.6
                )

                result = json.loads(response.choices[0].message.content)

                for channel, data in result.items():
                    console.print(f"\n[bold]{channel.upper()}:[/bold]")
                    console.print(f"Content: {data.get('content', 'N/A')}")
                    console.print(f"Tone: {data.get('tone', 'N/A')}")
                    if data.get('hashtags'):
                        console.print(f"Hashtags: {' '.join(data['hashtags'])}")
                    console.print(f"[dim]Length: {len(data.get('content', ''))} chars[/dim]")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("\n[bold]Batch Adaptation Prompt:[/bold]")
            console.print(prompt)

    def _get_platform_guidelines(self, platform: str) -> Dict:
        """Get platform-specific guidelines"""
        guidelines = {
            "facebook": {
                "max_length": 2000,
                "style": "Friendly, conversational tone. Use emojis sparingly. Focus on storytelling.",
                "features": "Can include longer content, multiple images, links work well."
            },
            "instagram": {
                "max_length": 2200,
                "style": "Visual-first, lifestyle-focused. Use relevant hashtags (5-10). Engage with community.",
                "features": "Stories, Reels, carousel posts. Strong visual component required."
            },
            "twitter": {
                "max_length": 280,
                "style": "Concise, witty, timely. Use hashtags strategically (1-2). Be conversational.",
                "features": "Threading for longer thoughts. Replies and retweets for engagement."
            },
            "linkedin": {
                "max_length": 3000,
                "style": "Professional, industry-focused. Share insights and expertise. Use professional tone.",
                "features": "Document posts, industry discussions, professional networking."
            },
            "youtube": {
                "max_length": 5000,
                "style": "Descriptive, SEO-optimized. Include timestamps, clear CTAs.",
                "features": "Video descriptions, community posts, playlist organization."
            }
        }
        return guidelines.get(platform, guidelines["facebook"])

    async def run_interactive_menu(self):
        """Run interactive testing menu"""
        while True:
            console.print("\n[bold cyan]AI Prompt Testing Menu[/bold cyan]")
            console.print("1. Test Content Suggestions")
            console.print("2. Test Content Optimization")
            console.print("3. Test Content Moderation")
            console.print("4. Test City Research")
            console.print("5. Test Channel Adaptation")
            console.print("6. Test News to Post Conversion")
            console.print("7. Test Image Prompt Enhancement")
            console.print("8. Test Multi-Perspective Analysis")
            console.print("9. Test Batch Channel Adaptation")
            console.print("0. Exit")

            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"])

            if choice == "0":
                console.print("[yellow]Exiting...[/yellow]")
                break
            elif choice == "1":
                await self.test_content_suggestions()
            elif choice == "2":
                await self.test_content_optimization()
            elif choice == "3":
                await self.test_moderation()
            elif choice == "4":
                await self.test_city_research()
            elif choice == "5":
                await self.test_channel_adaptation()
            elif choice == "6":
                await self.test_news_to_post()
            elif choice == "7":
                await self.test_image_prompt_enhancement()
            elif choice == "8":
                await self.test_multi_perspective_analysis()
            elif choice == "9":
                await self.test_batch_adaptation()

            if not Confirm.ask("\nContinue testing?"):
                break

async def main():
    """Main entry point"""
    console.print("[bold green]OmniPush AI Prompt Testing Tool[/bold green]")
    console.print("=" * 50)

    tester = AIPromptTester()

    if not tester.openai_api_key:
        console.print("[yellow]⚠ OpenAI API key not found in environment[/yellow]")
        console.print("Some features will use fallback/mock implementations")
    else:
        console.print("[green]✓ OpenAI API configured[/green]")

    await tester.run_interactive_menu()

if __name__ == "__main__":
    asyncio.run(main())