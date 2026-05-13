import os
import asyncio
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI
from playwright.async_api import async_playwright
from typing import Dict, Any, List
import logging
from config.prompts import Prompts
from services.s3_service import s3_service
from services.llm_service import llm_service, LLMProfile
from utils.tamil_text_cleaner import safe_truncate_tamil

logger = logging.getLogger(__name__)


class ContentService:
    def __init__(self):
        self.llm_service = llm_service
        if self.llm_service.is_available(LLMProfile.DEFAULT):
            logger.info("LLM service initialized for content service")
        else:
            logger.warning("LLM service not configured - content generation will be limited")

    async def generate_html_content(self, content: str, channel_name: str = None, use_exact_template: bool = False) -> str:
        """Generate HTML content using OpenAI based on the sample.html template"""

        # Read the appropriate HTML template
        if use_exact_template:
            try:
                with open("sample_newscard.html", "r", encoding="utf-8") as f:
                    sample_html = f.read()
            except FileNotFoundError:
                try:
                    with open("sample.html", "r", encoding="utf-8") as f:
                        sample_html = f.read()
                except FileNotFoundError:
                    sample_html = self._get_fallback_template()
        else:
            try:
                with open("sample.html", "r", encoding="utf-8") as f:
                    sample_html = f.read()
            except FileNotFoundError:
                sample_html = self._get_fallback_template()

        if not self.llm_service.is_available(LLMProfile.DEFAULT):
            logger.error("LLM service not configured - cannot generate content")
            raise ValueError("OpenAI API key required for content generation")

        try:
            html_content = await self.llm_service.generate(
                messages=Prompts.get_html_generation_messages(content, sample_html, channel_name),
                profile=LLMProfile.DEFAULT,
            )

            if not html_content:
                return self._generate_simple_html(content)

            # Clean the response to extract HTML
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0]
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0]

            return html_content.strip()

        except Exception as e:
            logger.error(f"Error generating HTML content: {e}")
            # Fallback to simple template substitution
            return self._generate_simple_html(content)

    def _fit_content_to_newscard(self, content: str, max_length: int = 180) -> str:
        # """Fit content to the newscard space constraints"""
        # if len(content) <= max_length:
        #     return content
        
        # # Try to find a good breaking point at sentences first
        # sentences = content.split('.')
        # fitted_content = ""
        
        # for sentence in sentences:
        #     sentence = sentence.strip()
        #     if not sentence:
        #         continue
        #     potential_content = fitted_content + sentence + '.'
        #     if len(potential_content) <= max_length:
        #         fitted_content = potential_content
        #     else:
        #         break
        
        # # If we couldn't fit even one sentence, try breaking at commas or spaces
        # if not fitted_content or len(fitted_content) < 50:
        #     # Try breaking at commas
        #     parts = content.split(',')
        #     fitted_content = ""
        #     for part in parts:
        #         part = part.strip()
        #         potential_content = fitted_content + part + ','
        #         if len(potential_content) <= max_length:
        #             fitted_content = potential_content
        #         else:
        #             break
            
        #     # Remove trailing comma if exists
        #     fitted_content = fitted_content.rstrip(',').strip()
            
        #     # If still too short or too long, just truncate (using safe truncation for Tamil)
        #     if not fitted_content or len(fitted_content) < 30:
        #         fitted_content = safe_truncate_tamil(content, max_length)
        
        # return fitted_content.strip()
        return content.strip()

    async def generate_exact_newscard_template(self, content: str, channel_name: str = None, tone: str = "professional", tenant_id: str = None, channel_id: str = None, image_url: str = None, headline: str = None, district: str = None) -> str:
        """Generate HTML using rotating newscard templates with content fitting and proper template assignment support"""

        # Import the template service
        from .newscard_template_service import newscard_template_service

        # Fit content to newscard constraints
        fitted_content = self._fit_content_to_newscard(content)

        # Get database client for template assignment support
        db_client = None
        try:
            from core.database import get_database
            db = get_database()
            db_client = db.service_client
        except Exception as e:
            logger.warning(f"Failed to get database client: {e}")

        # Use the new async template rotation system that respects channel assignments
        try:
            return await newscard_template_service.generate_newscard_html_async(
                content=fitted_content,
                tenant_id=tenant_id,
                channel_id=channel_id,
                channel_name=channel_name or "News Channel",
                category="News",
                image_url=image_url,
                headline=headline,
                district=district,
                db_client=db_client
            )
        except Exception as e:
            logger.error(f"Error using async template rotation system: {e}")
            # Fallback to sync system if async one fails
            try:
                return newscard_template_service.generate_newscard_html(
                    content=fitted_content,
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    channel_name=channel_name or "News Channel",
                    category="News",
                    image_url=image_url,
                    headline=headline,
                    district=district,
                    db_client=db_client
                )
            except Exception as e2:
                logger.error(f"Error using sync template rotation system: {e2}")
                # Final fallback to old system if both fail
                return self._legacy_template_generation(fitted_content, channel_name, tone)
    
    def _legacy_template_generation(self, fitted_content: str, channel_name: str, tone: str) -> str:
        """Legacy template generation as fallback"""
        try:
            with open("sample_newscard.html", "r", encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            # Fallback to a minimal newscard-like template
            return self._generate_newscard_fallback(fitted_content, channel_name, tone)
        
        # Replace content in the template
        import re
        
        # Find and replace the main content span - look for the specific content in sample_newscard.html
        # The template has: <span>Congress leader Rahul Gandhi accused 'vote theft'...</span>
        
        # First try to replace the exact content from the sample
        sample_content = """Congress leader Rahul Gandhi accused 'vote theft' in the Maharashtra assembly elections, highlighting surges in the voter list and demanded machine-readable voter rolls and CCTV footage<i class="period">.</i>"""
        
        if sample_content in template:
            # Replace the exact sample content with our fitted content
            template = template.replace(sample_content, fitted_content)
        else:
            # Fallback: find any span with content and replace it
            content_pattern = r'(<span[^>]*>)([^<]*?)(</span>)'
            if re.search(content_pattern, template):
                template = re.sub(content_pattern, rf'\1{fitted_content}\3', template, count=1)
        
        # Replace channel name if provided
        if channel_name:
            template = template.replace('www.newsit.app', channel_name)
            template = template.replace('NewsIT', channel_name)
        
        # Apply tone-based CSS modifications
        template = self._apply_tone_styles(template, tone)
        
        # Update date - handle multiple possible date formats in the template
        current_date = datetime.now().strftime("%d/%m/%Y")
        template = template.replace('<div>None</div>', f'<div>{current_date}</div>')
        template = template.replace('>None<', f'>{current_date}<')
        
        return template
    
    def _apply_tone_styles(self, template: str, tone: str) -> str:
        """Apply tone-specific styling to the template"""
        tone_colors = {
            "professional": {"bg": "#1a365d", "accent": "#2b6cb8", "news_bg": "#1e3a8a"},
            "casual": {"bg": "#742a2a", "accent": "#c53030", "news_bg": "#dc2626"},  
            "modern": {"bg": "#553c9a", "accent": "#805ad5", "news_bg": "#7c3aed"},
            "energetic": {"bg": "#c05621", "accent": "#dd6b20", "news_bg": "#ea580c"},
            "calm": {"bg": "#2d3748", "accent": "#4a5568", "news_bg": "#374151"}
        }
        
        colors = tone_colors.get(tone, tone_colors["professional"])
        
        # Apply color scheme modifications
        # Replace background colors
        if 'background-color: #282059' in template:
            template = template.replace('background-color: #282059', f'background-color: {colors["bg"]}')
        
        # Replace news badge color
        if 'background-color: #c20017' in template:
            template = template.replace('background-color: #c20017', f'background-color: {colors["news_bg"]}')
            
        # Add tone-specific class to body for additional styling
        if 'class="without-image without-ad lang-en"' in template:
            template = template.replace(
                'class="without-image without-ad lang-en"', 
                f'class="without-image without-ad lang-en tone-{tone}"'
            )
        
        return template

    def _generate_newscard_fallback(self, content: str, channel_name: str, tone: str) -> str:
        """Generate fallback newscard when template file is not found"""
        current_date = datetime.now().strftime("%d/%m/%Y")
        channel_display = channel_name or "Social Media Channel"
        
        tone_colors = {
            "professional": {"bg": "#282059", "accent": "#c20017"},
            "casual": {"bg": "#742a2a", "accent": "#c53030"},  
            "modern": {"bg": "#553c9a", "accent": "#805ad5"},
            "energetic": {"bg": "#c05621", "accent": "#dd6b20"},
            "calm": {"bg": "#2d3748", "accent": "#4a5568"}
        }
        
        colors = tone_colors.get(tone, tone_colors["professional"])
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            background-color: black;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 1080px;
            min-height: 1080px;
            padding: 0;
            margin: 0;
            font-family: Arial, sans-serif;
        }}
        
        .container {{
            position: relative;
            text-align: center;
            color: white;
            width: 1080px;
            height: 1080px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            background-color: {colors["bg"]};
            background-image: url('https://newsit-web-assets.s3.ap-south-1.amazonaws.com/images/background.png');
        }}
        
        .inner-container {{
            position: relative;
            text-align: center;
            color: white;
            width: 950px;
            height: 870px;
            background-color: white;
            border-radius: 36px;
            display: flex;
            align-items: stretch;
            justify-content: start;
            flex-direction: column;
        }}
        
        .heading-row {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 40px;
        }}
        
        .news {{
            color: rgb(243, 236, 236);
            font-size: 32px;
            font-weight: bold;
            background-color: {colors["accent"]};
            padding: 8px 16px;
            text-transform: uppercase;
            font-family: sans-serif;
        }}
        
        .centered {{
            color: rgb(39, 25, 87);
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 0 50px 25px 50px;
            flex-grow: 1;
            flex-direction: column;
        }}
        
        .centered span {{
            max-width: 100%;
            max-height: 100%;
            font-size: 90px;
            line-height: 1.14;
            word-wrap: break-word;
            margin-bottom: 12px;
        }}
        
        .footer-row {{
            width: 950px;
            height: 80px;
            display: flex;
            align-items: end;
            justify-content: stretch;
        }}
        
        .inner-footer-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        
        .pill {{
            padding: 6px 12px;
            border: 2px solid white;
            border-radius: 24px;
            color: rgb(255, 255, 255);
            font-size: 20px;
            font-family: sans-serif;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
    </style>
    <title>News</title>
</head>
<body>
    <div class="container">
        <div class="inner-container">
            <div class="heading-row">
                <div class="news">News</div>
            </div>
            <div class="centered">
                <span>{content}</span>
            </div>
        </div>
        <div class="footer-row">
            <div class="inner-footer-row">
                <div>
                    <div class="pill">{channel_display}</div>
                </div>
                <div>
                    <div class="pill date">
                        <div>{current_date}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    # ... rest of the methods remain the same
    async def generate_text_content(self, content: str) -> str:
        """Lightweight refinement of the user's content prior to HTML generation"""
        try:
            response = await self.llm_service.generate(
                messages=[
                    {
                        "role": "system",
                        "content": "You polish social media copy: concise, engaging, no hashtags or links added. Return only the improved text.",
                    },
                    {"role": "user", "content": content},
                ],
                profile=LLMProfile.DEFAULT,
                max_tokens=600,
            )
            return response.strip() if response else content
        except Exception:
            return content

    def _get_fallback_template(self) -> str:
        """Get a basic fallback template if sample.html is not found"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f0f0f0; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .content { font-size: 24px; text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">{{CONTENT}}</div>
    </div>
</body>
</html>"""

    def _generate_simple_html(self, content: str) -> str:
        """Generate simple HTML when OpenAI fails"""
        current_date = datetime.now().strftime("%d/%m/%Y")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Post</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .content {{
            font-size: 28px;
            line-height: 1.4;
            color: #333;
            margin: 20px 0;
        }}
        .date {{
            color: #666;
            font-size: 16px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">{content}</div>
        <div class="date">{current_date}</div>
    </div>
</body>
</html>"""

    async def generate_screenshot(self, html_content: str, tenant_id: str = None) -> Dict[str, str]:
        """Generate screenshot of HTML content using Playwright and upload to S3"""

        # Create screenshot filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
            :-3
        ]  # Include milliseconds
        filename = f"screenshot_{timestamp}.png"

        # Use TemporaryDirectory for better cleanup - automatically deleted even if process crashes
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create temp files in the temporary directory
            temp_html_path = temp_dir_path / f"newscard_{timestamp}.html"
            temp_screenshot_path = temp_dir_path / filename

            # Write HTML content to temp file
            temp_html_path.write_text(html_content, encoding="utf-8")

            try:
                async with async_playwright() as p:
                    # Launch browser
                    browser = await p.chromium.launch()
                    page = await browser.new_page()

                    # Set larger viewport to accommodate body padding/margins
                    await page.set_viewport_size({"width": 1200, "height": 1200})

                    # Navigate to the HTML file
                    await page.goto(f"file://{temp_html_path}", wait_until="networkidle")

                    # Wait for fonts to load properly (especially important for Tamil/Unicode fonts)
                    await page.evaluate("document.fonts.ready")

                    # CRITICAL: Wait for ALL images to finish loading (especially S3 images)
                    # This fixes the issue where follow.png and other S3 images don't load
                    # Includes timeout to prevent hanging indefinitely
                    # Handles templates with no images or broken image tags
                    await page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            const allImages = Array.from(document.images);

                            // Filter out images that shouldn't be waited for
                            const images = allImages.filter(img => {
                                // Skip images with empty or invalid src
                                if (!img.src || img.src === '' || img.src === 'about:blank') {
                                    console.log('Skipping image with empty/invalid src');
                                    return false;
                                }

                                // Skip hidden images (display: none or visibility: hidden)
                                const style = window.getComputedStyle(img);
                                if (style.display === 'none' || style.visibility === 'hidden') {
                                    console.log('Skipping hidden image:', img.src);
                                    return false;
                                }

                                return true;
                            });

                            console.log(`Waiting for ${images.length} images to load (${allImages.length} total img tags)`);

                            if (images.length === 0) {
                                console.log('No images to wait for, proceeding...');
                                resolve();
                                return;
                            }

                            let loadedCount = 0;
                            const totalImages = images.length;
                            let resolved = false;

                            // Set timeout to prevent hanging indefinitely (5 seconds is enough for most images)
                            const timeout = setTimeout(() => {
                                if (!resolved) {
                                    console.warn(`Image loading timeout: ${loadedCount}/${totalImages} images loaded`);
                                    resolved = true;
                                    resolve();
                                }
                            }, 5000);

                            const checkComplete = () => {
                                loadedCount++;
                                console.log(`Image ${loadedCount}/${totalImages} loaded`);
                                if (loadedCount === totalImages && !resolved) {
                                    console.log('All images loaded successfully');
                                    resolved = true;
                                    clearTimeout(timeout);
                                    resolve();
                                }
                            };

                            images.forEach((img, index) => {
                                if (img.complete && img.naturalWidth !== 0) {
                                    // Image already loaded
                                    console.log(`Image ${index + 1} already loaded:`, img.src);
                                    checkComplete();
                                } else {
                                    // Wait for image to load
                                    console.log(`Waiting for image ${index + 1}:`, img.src);
                                    img.addEventListener('load', () => {
                                        console.log(`Image ${index + 1} loaded successfully`);
                                        checkComplete();
                                    });
                                    img.addEventListener('error', () => {
                                        console.warn(`Image ${index + 1} failed to load:`, img.src);
                                        checkComplete(); // Continue even if image fails
                                    });
                                }
                            });
                        });
                    }
                """)

                    # Additional timeout to ensure all rendering is complete
                    await page.wait_for_timeout(10000)

                    # Get the card container element position and size
                    # Most templates use .card-container, .container, or body as main container
                    card_selector = ".card-container, .container, body > div:first-child"

                    try:
                        # Try to get the bounding box of the card container
                        card_element = await page.query_selector(card_selector)
                        if card_element:
                            bounding_box = await card_element.bounding_box()
                            if bounding_box:
                                # Use clip to capture exactly the card area
                                await page.screenshot(
                                    path=str(temp_screenshot_path),
                                    clip={
                                        'x': bounding_box['x'],
                                        'y': bounding_box['y'],
                                        'width': min(bounding_box['width'], 1080),
                                        'height': min(bounding_box['height'], 1080)
                                    }
                                )
                            else:
                                # Fallback if bounding box not found
                                await page.screenshot(path=str(temp_screenshot_path), clip={'x': 0, 'y': 0, 'width': 1080, 'height': 1080})
                        else:
                            # Fallback if element not found
                            await page.screenshot(path=str(temp_screenshot_path), clip={'x': 0, 'y': 0, 'width': 1080, 'height': 1080})
                    except Exception as clip_error:
                        logger.warning(f"Failed to use clip region, falling back to full page: {clip_error}")
                        # Final fallback to full_page
                        await page.screenshot(path=str(temp_screenshot_path), full_page=True)

                    # Close browser
                    await browser.close()

                # Read screenshot content
                screenshot_content = temp_screenshot_path.read_bytes()

                # Upload to S3 if tenant_id provided, otherwise fall back to local
                if tenant_id:
                    try:
                        upload_result = await s3_service.upload_screenshot(
                            screenshot_content, filename, tenant_id
                        )
                        
                        # Save screenshot metadata to media table
                        from uuid import uuid4
                        from core.database import get_database
                        
                        db = get_database()
                        supabase = db.service_client
                        media_id = str(uuid4())
                        
                        # Extract S3 key from URL for database storage
                        s3_key = upload_result.get('key')
                        if not s3_key and 'amazonaws.com' in upload_result['url']:
                            s3_key = upload_result['url'].split('.com/')[-1]
                        
                        # Use system user ID for automated screenshots
                        SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
                        
                        media_data = {
                            'id': media_id,
                            'tenant_id': tenant_id,
                            'file_name': filename,
                            'file_path': upload_result['url'],
                            'file_size': len(screenshot_content),
                            'mime_type': 'image/png',
                            'content_type': 'image/png',
                            'media_type': 'image',
                            's3_key': s3_key,
                            's3_bucket': 'omnipush-demo',
                            'size': len(screenshot_content),
                            'metadata': {
                                'width': 1080,
                                'height': 1080,
                                'format': 'png',
                                'screenshot': True
                            },
                            'created_at': datetime.utcnow().isoformat()
                        }
                        
                        try:
                            supabase.table('media').insert(media_data).execute()
                        except Exception as db_error:
                            logger.warning(f"Failed to save screenshot metadata to database: {db_error}")

                        # No manual cleanup needed - TemporaryDirectory handles it automatically
                        return {
                            "path": upload_result['key'],
                            "filename": filename,
                            "url": upload_result['url'],
                            "s3_key": upload_result['key'],
                            "media_id": media_id
                        }
                    except Exception as s3_error:
                        logger.warning(f"S3 upload failed, falling back to local: {s3_error}")

                    # Fallback to local storage
                    screenshots_dir = Path("static") / "screenshots"
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    local_screenshot_path = screenshots_dir / filename

                    # Copy temp file to local directory (can't move across filesystems)
                    shutil.copy2(temp_screenshot_path, local_screenshot_path)

                    # No manual cleanup needed - TemporaryDirectory handles it automatically
                    return {
                        "path": str(local_screenshot_path),
                        "filename": filename,
                        "url": f"/static/screenshots/{filename}",
                    }

            except Exception as e:
                # No manual cleanup needed - TemporaryDirectory handles it automatically
                logger.error(f"Screenshot generation failed: {str(e)}")
                raise Exception(f"Screenshot generation failed: {str(e)}")

    async def generate_social_media_posts(self, city: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate social media posts based on research data"""
        
        combined_research = f"""
        City: {city}
        OpenAI Analysis: {research_data.get('openai_analysis', '')}
        Perplexity Research: {research_data.get('perplexity_research', '')}
        """

        try:
            response = await self.llm_service.generate(
                messages=Prompts.get_social_posts_messages(city, safe_truncate_tamil(combined_research, 3000, suffix="")),
                profile=LLMProfile.CREATIVE,
            )

            if not response:
                return self._create_fallback_posts(city)

            import json_repair

            return json_repair.loads(response.strip())

        except Exception as e:
            logger.error(f"Error generating social posts: {e}")
            # Fallback posts
            return self._create_fallback_posts(city)

    def _create_fallback_posts(self, city: str) -> Dict[str, Any]:
        """Create fallback social media posts"""
        return {
            "instagram_posts": [
                {
                    "caption": f"Exploring the beautiful city of {city}! 🌆✨",
                    "hashtags": [f"#{city.replace(' ', '').lower()}", "#citylife", "#explore"],
                    "type": "photo"
                },
                {
                    "caption": f"Local culture and community in {city} 💫",
                    "hashtags": [f"#{city.replace(' ', '').lower()}culture", "#community"],
                    "type": "carousel"
                }
            ],
            "facebook_posts": [
                {
                    "content": f"Discover what makes {city} special - from its rich history to vibrant community life.",
                    "call_to_action": "Learn more"
                },
                {
                    "content": f"Planning a visit to {city}? Here's what you need to know about this amazing place.",
                    "call_to_action": "Visit now"
                }
            ],
            "twitter_posts": [
                {
                    "content": f"Why {city} should be on your travel list 🌟",
                    "hashtags": [f"#{city.replace(' ', '').lower()}", "#travel"]
                },
                {
                    "content": f"The hidden gems of {city} are waiting to be discovered! ✨",
                    "hashtags": [f"#{city.replace(' ', '').lower()}", "#hiddengems"]
                }
            ],
            "linkedin_posts": [
                {
                    "content": f"Economic and business opportunities in {city}: A comprehensive overview of the local market and investment potential.",
                    "tone": "professional"
                },
                {
                    "content": f"Infrastructure and development initiatives in {city} are creating new opportunities for growth and innovation.",
                    "tone": "informative"
                }
            ]
        }


async def generate_news_card_from_text(title: str, content: str, tenant_id: str = None, content_adaptation: Dict[str, Any] = None, channel_id: str = None, image_url: str = None, headline: str = None, district: str = None) -> Dict[str, Any]:
    """
    Generate news card image from text content.

    IMPORTANT: This function does NOT perform content adaptation. Content should already be
    adapted using adapt_content_multi_page_news() before calling this function.
    This function only generates the newscard HTML/image from the provided content.
    """
    try:
        # Check generation mode settings
        enable_llm_generation = os.getenv("ENABLE_LLM_HTML_GENERATION", "false").lower() == "true"
        use_exact_template = os.getenv("USE_EXACT_NEWSCARD_TEMPLATE", "false").lower() == "true"

        html_content = None
        content_adapted = False

        # Extract channel information from content adaptation
        channel_name = content_adaptation.get('channel_name') if content_adaptation else None

        # # Use channel-specific tone if available, otherwise use provided tone or default
        # if channel_name and content_adaptation:
        #     from config.prompts import Prompts
        #     channel_settings = Prompts.get_channel_tone_settings(channel_name)
        #     tone = channel_settings.get('tone', 'professional')
        # else:
        #     tone = content_adaptation.get('tone', 'professional') if content_adaptation else 'professional'


        # Get tone from content_adaptation settings (default to 'professional')
        tone = content_adaptation.get('tone', 'professional') if content_adaptation else 'professional'

        if use_exact_template:
            # Use the exact newscard template with content fitting and tone support
            content_service = ContentService()

            # IMPORTANT: Content is already adapted by adapt_content_multi_page_news
            # We do NOT perform additional content adaptation here to avoid duplicate LLM calls
            # # Apply content adaptation if provided
            # adapted_content = content
            # if content_adaptation:
            #     # Apply content adaptation settings using channel-specific tone
            #     custom_instructions = content_adaptation.get('custom_instructions', '')
                
            #     # Use channel-specific adaptation if channel is specified
            #     if channel_name:
            #         from config.prompts import Prompts
            #         adaptation_prompt = Prompts.get_channel_adaptation_prompt(
            #             content, channel_name, custom_instructions
            #         )
            #     else:
            #         adaptation_prompt = f"""
            #             Adapt the following content with these settings:
            #             - Tone: {tone}
            #             - Style: {content_adaptation.get('style', 'modern')}  
            #             - Color scheme: {content_adaptation.get('color_scheme', 'default')}
            #             - Custom instructions: {custom_instructions}
                        
            #             Original content: {content}
                        
            #             Requirements:
            #             1. Keep the content concise for news card format (max 180 characters)
            #             2. Maintain the core message and facts
            #             3. Adapt the tone and style as specified
            #             4. Make it engaging and appropriate for the target audience
            #             5. Return only the adapted content text without explanations
            #             6. Do not create hashtags. Since this is a news card, we don't need hashtags.
                        
            #             Always respond in Tamil. Since the audience is Tamil speaking. If the content is not in Tamil, translate it to Tamil.

            #             Some of the place names in Tamil. Use these place names in the content if they are present in the content:
            #             Kavundampalayam - கவுண்டம்பாளையம்
            #             Mettupalayam - மேட்டுப்பாளையம்
            #             Kinathukadavu - கிணத்துக்கடவு
            #             Pollachi - பொள்ளாச்சி
            #             """
                
            #     try:
            #         adapted_response = await content_service.llm_service.generate(
            #             messages=[
            #                 {
            #                     "role": "system",
            #                     "content": "You are a content adaptation expert. Adapt content for social media news cards, keeping it concise and engaging. Always respond in Tamil. Since the audience is Tamil speaking. If the content is not in Tamil, translate it to Tamil.",
            #                 },
            #                 {"role": "user", "content": adaptation_prompt},
            #             ],
            #             profile=LLMProfile.DEFAULT,
            #             max_tokens=400,
            #             temperature=0.7,
            #         )
            #         adapted_content = adapted_response.strip() if adapted_response else content
            #         content_adapted = bool(adapted_response)
            #         logger.info(
            #             f"Content successfully adapted using LLM. Original length: {len(content)}, Adapted length: {len(adapted_content)}"
            #         )
            #     except Exception as adaptation_error:
            #         logger.warning(f"Content adaptation failed, using original content: {adaptation_error}")
            #         adapted_content = content
            
            adapted_content = content

            # Generate HTML using exact template
            html_content = await content_service.generate_exact_newscard_template(
                adapted_content,
                channel_name=channel_name,
                tone=tone,
                tenant_id=tenant_id,
                channel_id=channel_id,
                image_url=image_url,
                headline=headline,
                district=district
            )
            logger.info("Successfully generated HTML using exact newscard template")
            
            # Store newscard locally for future reference
            if tenant_id:
                try:
                    from .newscard_storage_service import newscard_storage_service
                    from .newscard_template_service import newscard_template_service
                    
                    # Get template name from the service (if available)
                    template_info = "rotated_template"
                    
                    storage_result = newscard_storage_service.store_newscard(
                        html_content=html_content,
                        content=adapted_content,
                        tenant_id=tenant_id,
                        channel_name=channel_name or "News Channel",
                        template_name=template_info,
                        category="News"
                    )
                    logger.info(f"Newscard stored locally: {storage_result.get('local_path', 'unknown')}")
                except Exception as storage_error:
                    logger.warning(f"Failed to store newscard locally: {storage_error}")
                    # Don't fail the entire process if storage fails
            
        elif enable_llm_generation:
            # Use LLM-based HTML generation
            # IMPORTANT: Content is already adapted by adapt_content_multi_page_news
            # We do NOT perform additional content adaptation here to avoid duplicate LLM calls
            content_service = ContentService()
            adapted_content = content

            # 
            # if content_adaptation:
            #     # Apply content adaptation settings
            #     custom_instructions = content_adaptation.get('custom_instructions', '')
                
            #     adaptation_prompt = f"""
            #         Adapt the following content with these settings:
            #         - Tone: {tone}
            #         - Style: {content_adaptation.get('style', 'modern')}  
            #         - Color scheme: {content_adaptation.get('color_scheme', 'default')}
            #         - Custom instructions: {custom_instructions}
                    
            #         Original content: {content}
                    
            #         Requirements:
            #         1. Keep the content concise for news card format (max 180 characters)
            #         2. Maintain the core message and facts
            #         3. Adapt the tone and style as specified
            #         4. Make it engaging and appropriate for the target audience
            #         5. Return only the adapted content text without explanations
                    
            #         If custom instructions mention Tamil or specific language, follow those instructions. Otherwise, keep the content in the same language as the original.
            #         """
                
            #     try:
            #         adapted_response = await content_service.llm_service.generate(
            #             messages=[
            #                 {
            #                     "role": "system",
            #                     "content": "You are a content adaptation expert. Adapt content for social media news cards, keeping it concise and engaging.",
            #                 },
            #                 {"role": "user", "content": adaptation_prompt},
            #             ],
            #             profile=LLMProfile.DEFAULT,
            #             max_tokens=400,
            #             temperature=0.7,
            #         )
            #         adapted_content = adapted_response.strip() if adapted_response else content
            #         content_adapted = bool(adapted_response)
            #         logger.info(
            #             f"Content successfully adapted using LLM. Original length: {len(content)}, Adapted length: {len(adapted_content)}"
            #         )
            #     except Exception as adaptation_error:
            #         logger.warning(f"Content adaptation failed, using original content: {adaptation_error}")
            #         adapted_content = content

            # Generate HTML using LLM with content
            html_content = await content_service.generate_html_content(f"{adapted_content}", channel_name=channel_name)
            logger.info("Successfully generated HTML using LLM")
            
        else:
            # Fallback to template-based generation
            logger.info("Using fallback template-based HTML generation")
            html_content = generate_html_preview(title, content)
        
        # Capture screenshot
        content_service = ContentService()
        image_info = await content_service.generate_screenshot(html_content, tenant_id)
        
        return {
            'url': image_info['url'],
            'filename': image_info['filename'],
            'path': image_info['path'],
            's3_key': image_info.get('s3_key'),
            'template_mode': 'exact_template' if use_exact_template else ('llm_generated' if enable_llm_generation else 'fallback'),
            'llm_generated': enable_llm_generation and html_content is not None and not use_exact_template,
            'exact_template_used': use_exact_template,
            'content_adapted': content_adapted,
            'tone_applied': tone if use_exact_template or content_adaptation else None
        }
        
    except Exception as e:
        logger.exception(f"News card generation failed: {e}")
        return {
            'url': None,
            'filename': None,
            'path': None,
            'error': str(e),
            'template_mode': 'error',
            'llm_generated': False,
            'exact_template_used': False,
            'content_adapted': False,
            'tone_applied': None
        }


def generate_html_preview(title: str, content: str) -> str:
    """Generate HTML preview for content"""
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            text-align: center;
        }}
        .title {{
            font-size: 32px;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 20px;
            line-height: 1.3;
        }}
        .content {{
            font-size: 20px;
            line-height: 1.6;
            color: #4a5568;
            margin: 30px 0;
            text-align: left;
        }}
        .date {{
            color: #718096;
            font-size: 16px;
            margin-top: 30px;
            font-weight: 500;
        }}
        .accent {{
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 2px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">{title}</h1>
        <div class="accent"></div>
        <div class="content">{content}</div>
        <div class="date">{current_date}</div>
    </div>
</body>
</html>"""


async def capture_screenshot(html_content: str, tenant_id: str = None) -> Dict[str, str]:
    """Capture screenshot from HTML content"""
    content_service = ContentService()
    return await content_service.generate_screenshot(html_content, tenant_id)


async def moderate_content_with_ai(content: str, source: str) -> Dict[str, Any]:
    """Moderate content using OpenAI moderation API"""
    try:
        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Use OpenAI moderation endpoint
        response = await openai_client.moderations.create(input=content)
        
        result = response.results[0]
        
        # Check if content is flagged
        flagged = result.flagged
        categories = result.categories
        category_scores = result.category_scores
        
        # Collect flagged categories
        flags = []
        for category, is_flagged in categories.model_dump().items():
            if is_flagged:
                flags.append(category)
        
        # Calculate overall risk score (0-1)
        risk_score = max(category_scores.model_dump().values()) if category_scores else 0
        
        # Determine status based on flags and score
        if flagged or risk_score > 0.8:
            status = 'rejected'
            approved = False
        elif risk_score > 0.5:
            status = 'flagged'
            approved = False
        else:
            status = 'approved'
            approved = True
        
        return {
            'status': status,
            'score': risk_score,
            'flags': flags,
            'approved': approved,
            'details': {
                'source': source,
                'categories': categories.model_dump(),
                'category_scores': category_scores.model_dump()
            }
        }
        
    except Exception as e:
        logger.exception(f"Content moderation failed: {e}")
        # Default to approved if moderation fails
        return {
            'status': 'approved',
            'score': 0.0,
            'flags': [],
            'approved': True,
            'details': {'error': str(e)}
        }