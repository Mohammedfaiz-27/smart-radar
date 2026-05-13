import os
import random
import hashlib
import html
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

from utils.tamil_text_cleaner import safe_clean_tamil_content

logger = logging.getLogger(__name__)

class NewscardTemplateService:
    """Service for managing newscard template rotation and generation"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / "templates" / "newscard"
        self.template_cache = {}
        self.template_rotation_state = {}
        self._load_templates_from_db()
        # Fallback to local templates if DB loading fails
        if not self.available_templates:
            self._load_templates()
    
    def _load_templates_from_db(self):
        """Load available newscard templates from database with S3 URLs"""
        try:
            from core.database import get_database
            db = get_database()

            result = db.client.table('newscard_templates')\
                .select('id, template_name, template_display_name, template_path, s3_url, supports_images, is_active')\
                .eq('is_active', True)\
                .execute()

            templates = []
            for template_data in result.data:
                template_name = template_data['template_name']
                self.template_cache[template_name] = {
                    'id': template_data['id'],
                    'name': template_name,
                    'display_name': template_data['template_display_name'],
                    'has_images': template_data['supports_images'],
                    's3_url': template_data.get('s3_url'),
                    'path': template_data.get('template_path'),
                    'content': None  # Will be loaded on demand
                }
                templates.append(template_name)

            self.available_templates = templates
            logger.info(f"Loaded {len(templates)} newscard templates from database: {templates}")

        except Exception as e:
            logger.error(f"Failed to load templates from database: {e}")
            self.available_templates = []

    def _load_templates(self):
        """Fallback: Load all available newscard templates from both newscard/ and newscard_nue/ directories"""
        templates = []

        # Load templates from original newscard directory
        if self.template_dir.exists():
            templates.extend(self._load_templates_from_directory(self.template_dir, "newscard"))
        else:
            logger.warning(f"Newscard template directory not found: {self.template_dir}")

        # Load templates from newscard_nue directory
        nue_template_dir = Path(__file__).parent.parent / "templates" / "newscard_nue"
        if nue_template_dir.exists():
            templates.extend(self._load_templates_from_directory(nue_template_dir, "newscard_nue"))
        else:
            logger.warning(f"Newscard_nue template directory not found: {nue_template_dir}")

        # Only update if we don't already have templates from DB
        if not hasattr(self, 'available_templates') or not self.available_templates:
            self.available_templates = templates
            logger.info(f"Loaded {len(templates)} newscard templates from local files: {templates}")
    
    def _load_templates_from_directory(self, template_dir: Path, directory_prefix: str) -> List[str]:
        """Load templates from a specific directory with proper naming and categorization"""
        templates = []
        
        # Load regular templates without images from root directory
        for template_file in template_dir.glob("template_*.html"):
            template_name = f"{directory_prefix}_{template_file.stem}"
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.template_cache[template_name] = {
                    'content': content,
                    'path': template_file,
                    'name': template_name,
                    'has_images': False
                }
                templates.append(template_name)
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")
        
        # Load templates with images from with_images subdirectory
        with_images_dir = template_dir / "with_images"
        if with_images_dir.exists():
            for template_file in with_images_dir.glob("*.html"):
                template_name = f"{directory_prefix}_{template_file.stem}_with_image"
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.template_cache[template_name] = {
                        'content': content,
                        'path': template_file,
                        'name': template_name,
                        'has_images': True
                    }
                    templates.append(template_name)
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
        
        # Load templates without images from without_images subdirectory (for newscard_nue)
        without_images_dir = template_dir / "without_images"
        if without_images_dir.exists():
            for template_file in without_images_dir.glob("*.html"):
                template_name = f"{directory_prefix}_{template_file.stem}_without_image"
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.template_cache[template_name] = {
                        'content': content,
                        'path': template_file,
                        'name': template_name,
                        'has_images': False
                    }
                    templates.append(template_name)
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
        
        return templates
    
    def get_next_template(self, tenant_id: str, channel_id: str = None, with_images: bool = False, db_client=None) -> str:
        """Get the next template for rotation based on tenant and channel"""

        # Note: Template assignment checking is not supported in sync method
        # Use the async version (get_assigned_template_async) for full assignment support
        if db_client and channel_id:
            logger.info(f"Template assignment check skipped for sync method. Channel: {channel_id}, tenant: {tenant_id}. Use async method for assignment support.")

        # Filter templates based on image requirement
        available_templates = self._filter_templates_by_image_support(with_images)
        
        if not available_templates:
            logger.warning(f"No templates available (with_images={with_images}), returning fallback")
            return self._get_fallback_template()
        
        # Create unique identifier for rotation
        # Use channel_id if available, otherwise fall back to tenant_id only
        rotation_key = f"{tenant_id}:{channel_id}:{with_images}" if channel_id else f"{tenant_id}:{with_images}"
        
        # Use rotation key to determine consistent rotation per channel
        # Use a better hash distribution method
        import hashlib
        hash_bytes = hashlib.md5(rotation_key.encode()).digest()
        # Convert first 4 bytes to int for better distribution
        rotation_hash = int.from_bytes(hash_bytes[:4], byteorder='big')
        
        # Add a small time component for variety (changes every hour for better rotation)
        time_component = datetime.now().hour  # Changes every hour (24 times per day)
        
        # Use the channel_id hash to add more variance for better distribution
        channel_hash = int.from_bytes(hashlib.md5(channel_id.encode() if channel_id else b'').digest()[:4], byteorder='big') if channel_id else 0
        
        # Rotate template based on channel/tenant and time to ensure variety
        rotation_index = (rotation_hash + time_component + channel_hash) % len(available_templates)
        template_name = available_templates[rotation_index]

        context = f"channel {channel_id}" if channel_id else f"tenant {tenant_id}"
        logger.info(f"Selected template '{template_name}' (with_images={with_images}) for {context}")

        content = self.get_template_by_name(template_name)
        return content if content else self._get_fallback_template()

    async def get_assigned_template_async(self, tenant_id: str, channel_id: str = None, with_images: bool = False, db_client=None) -> str:
        """Async version to get assigned template for a social channel, with fallback to rotation"""

        # First, try to get assigned template for the specific social channel
        if db_client and channel_id:
            try:
                from services.social_template_assignment_service import SocialTemplateAssignmentService
                assignment_service = SocialTemplateAssignmentService(db_client)
                assigned_template_name = await assignment_service.get_assigned_template_for_channel(
                    tenant_id=tenant_id,
                    social_account_id=channel_id,
                    has_images=with_images
                )

                if assigned_template_name:
                    # First, try to resolve the template name to the full database name
                    cached_template_name = self._resolve_template_name(assigned_template_name)

                    if cached_template_name:
                        # Try to get the template content using the resolved name
                        template_content = self.get_template_by_name(cached_template_name)
                        if template_content:
                            logger.info(f"Using assigned template '{assigned_template_name}' (mapped to '{cached_template_name}') for channel {channel_id}")
                            return template_content
                        else:
                            logger.warning(f"Resolved template '{cached_template_name}' found but content could not be loaded")
                    else:
                        # Fallback: try the original name directly (in case it's already a full name)
                        template_content = await self.get_template_by_name_from_s3(assigned_template_name)
                        if template_content:
                            logger.info(f"Using assigned template '{assigned_template_name}' from S3 for channel {channel_id}")
                            return template_content
                        logger.warning(f"Assigned template '{assigned_template_name}' not found in cache or S3, falling back to rotation")
                else:
                    logger.info(f"No template assignment found for channel {channel_id}, using rotation")

            except Exception as e:
                logger.warning(f"Failed to get assigned template, falling back to rotation: {e}")

        # Fall back to rotation method
        return self.get_next_template(tenant_id, channel_id, with_images)
    
    def _resolve_template_name(self, db_template_name: str) -> Optional[str]:
        """
        Resolve database template name to cached template name.
        Database stores: 'template_1_modern_gradient' or 'left_content_right_image_without_image'
        Cache stores: 'newscard_template_1_modern_gradient' or 'newscard_nue_left_content_right_image_without_image'
        """
        # First, try exact match (shouldn't happen but just in case)
        if db_template_name in self.template_cache:
            return db_template_name

        # Try with different prefixes
        possible_prefixes = ['newscard_', 'newscard_nue_']

        for prefix in possible_prefixes:
            candidate_name = f"{prefix}{db_template_name}"
            if candidate_name in self.template_cache:
                return candidate_name

        # Try to find by checking if the db_template_name is a suffix of any cached name
        for cached_name in self.template_cache.keys():
            if cached_name.endswith(db_template_name):
                return cached_name

        # No match found
        logger.warning(f"No template match found for database name: '{db_template_name}'. Available templates: {list(self.template_cache.keys())}")
        return None

    def _filter_templates_by_image_support(self, with_images: bool = False) -> List[str]:
        """Filter templates based on whether they support images"""
        return [
            name for name in self.available_templates
            if self.template_cache[name].get('has_images', False) == with_images
        ]
    
    def get_random_template(self) -> str:
        """Get a random template"""
        if not self.available_templates:
            return self._get_fallback_template()

        template_name = random.choice(self.available_templates)
        logger.info(f"Selected random template '{template_name}'")
        content = self.get_template_by_name(template_name)
        return content if content else self._get_fallback_template()
    
    def get_template_by_name(self, template_name: str) -> Optional[str]:
        """Get a specific template by name, prioritizing S3 over local cache"""
        if template_name not in self.template_cache:
            return None

        template_info = self.template_cache[template_name]

        # If content is already cached, return it
        if template_info.get('content'):
            return template_info['content']

        # Try to load from S3 first if available
        if template_info.get('s3_url'):
            try:
                import requests
                response = requests.get(template_info['s3_url'], timeout=10)
                if response.status_code == 200:
                    content = response.text
                    # Cache the content for future use
                    self.template_cache[template_name]['content'] = content
                    logger.info(f"Loaded template '{template_name}' from S3")
                    return content
                else:
                    logger.warning(f"Failed to load template from S3, status: {response.status_code}")
            except Exception as e:
                logger.warning(f"Error loading template from S3: {e}")

        # Fallback to local file if available
        if template_info.get('path'):
            try:
                if isinstance(template_info['path'], str):
                    # It's a file path from database
                    base_dir = Path(__file__).parent.parent
                    full_path = base_dir / template_info['path'].lstrip('/')
                    if full_path.exists():
                        content = full_path.read_text(encoding='utf-8')
                        # Cache the content for future use
                        self.template_cache[template_name]['content'] = content
                        logger.info(f"Loaded template '{template_name}' from local file")
                        return content
                else:
                    # It's a Path object from old loading method
                    if template_info['path'].exists():
                        content = template_info['path'].read_text(encoding='utf-8')
                        # Cache the content for future use
                        self.template_cache[template_name]['content'] = content
                        logger.info(f"Loaded template '{template_name}' from local cache")
                        return content
            except Exception as e:
                logger.error(f"Error loading template from local file: {e}")

        logger.error(f"Failed to load template '{template_name}' from any source")
        return None

    async def get_template_by_name_from_s3(self, template_name: str) -> Optional[str]:
        """Get a specific template by name, preferring S3 over local cache"""
        try:
            from services.template_s3_service import template_s3_service
            return await template_s3_service.get_template_content_by_name(template_name)
        except ImportError:
            # Fallback to local cache if S3 service not available
            logger.warning("S3 service not available, falling back to local cache")
            return self.get_template_by_name(template_name)
        except Exception as e:
            logger.error(f"Error fetching template from S3, falling back to local: {str(e)}")
            return self.get_template_by_name(template_name)
    
    def list_available_templates(self) -> List[Dict[str, str]]:
        """List all available templates with metadata"""
        return [
            {
                'name': name,
                'display_name': info.get('display_name', name.replace('_', ' ').title()),
                'path': str(info.get('path', '')),
                's3_url': info.get('s3_url', ''),
                'has_images': info.get('has_images', False),
                'source': 'S3' if info.get('s3_url') else 'Local'
            }
            for name, info in self.template_cache.items()
        ]
    
    def render_template(
        self,
        template_content: str,
        content: str,
        channel_name: str = "News Channel",
        category: str = "News",
        source: str = None,
        website: str = None,
        date: str = None,
        logo_url: str = None,
        image_url: str = None,
        lang: str = "en",
        body_class: str = "without-image without-ad lang-en",
        headline: str = None,
        district: str = None
    ) -> str:
        """Render template with provided content and metadata"""

        # Handle None template content gracefully
        if template_content is None:
            logger.error("Template content is None, using fallback template")
            template_content = self._get_fallback_template()

        if date is None:
            date = datetime.now().strftime("%d/%m/%Y")
        
        # Set channel-specific defaults
        if source is None:
            source = channel_name
        if website is None:
            website = f"www.{channel_name.lower().replace(' ', '')}.com"
        if logo_url is None:
            # Use Smart Post logo as default
            logo_url = "/static/smart-post-logo.jpeg"

        # Note: We do NOT use html.escape() for Tamil/Unicode content as it breaks rendering
        # Tamil characters are already valid UTF-8 and templates have charset="UTF-8"
        # Escaping converts Unicode to HTML entities which breaks JS font auto-sizing
        # Only escape for potential HTML injection concerns (channel_name, category, etc.)

        # Clean Tamil text in content, headline, and district before rendering
        if content:
            content = safe_clean_tamil_content(content, "newscard_content")
        if headline:
            headline = safe_clean_tamil_content(headline, "newscard_headline")
        if district:
            district = safe_clean_tamil_content(district, "newscard_district")

        # Create replacement mappings
        replacements = {
            '{{content}}': content or "",  # Keep raw Unicode for proper Tamil rendering
            '{{channel_name}}': html.escape(channel_name) if channel_name else "",
            '{{category}}': html.escape(category) if category else "",
            '{{source}}': f"Source: {html.escape(source)}" if source else "",
            '{{website}}': html.escape(website) if website else "",
            '{{date}}': date,  # Date is safe, doesn't need escaping
            '{{logo_url}}': logo_url,  # URLs don't need escaping in this context
            '{{image_url}}': image_url or "https://via.placeholder.com/800x400/cccccc/666666?text=No+Image",
            '{{lang}}': lang,  # Language code is safe
            '{{body_class}}': body_class,  # CSS class is safe
            '{{headline_placeholder}}': headline or '',  # Keep raw Unicode for proper Tamil rendering
            '{{headline}}': headline or '',  # Keep raw Unicode for proper Tamil rendering
            '{{district}}': district or '',  # Keep raw Unicode for proper Tamil rendering
        }
        
        # Apply replacements
        rendered_template = template_content
        for placeholder, value in replacements.items():
            rendered_template = rendered_template.replace(placeholder, str(value))
        
        logger.info("Template rendered successfully with provided content")
        return rendered_template
    
    def generate_newscard_html(
        self,
        content: str,
        tenant_id: str = None,
        channel_id: str = None,
        channel_name: str = "News Channel",
        category: str = "News",
        template_name: str = None,
        image_url: str = None,
        db_client=None,
        headline: str = None,
        district: str = None,
        **kwargs
    ) -> str:
        """Generate complete newscard HTML with template rotation"""
        
        # Use channel_name as fallback for channel_id if not provided
        effective_channel_id = channel_id or channel_name
        
        # Determine if we need templates with images
        with_images = image_url is not None
        
        # Get template
        template_content = None

        if template_name:
            template_content = self.get_template_by_name(template_name)
            if not template_content:
                logger.warning(f"Template '{template_name}' not found, using rotation")
                template_content = self.get_next_template(tenant_id or "default", effective_channel_id, with_images)
        elif tenant_id:
            template_content = self.get_next_template(tenant_id, effective_channel_id, with_images, db_client)
        else:
            # For random template, use image-supporting templates if image_url is provided
            available_templates = self._filter_templates_by_image_support(with_images)
            if available_templates:
                import random
                template_name = random.choice(available_templates)
                template_content = self.get_template_by_name(template_name)
                if not template_content:
                    template_content = self.get_random_template()
            else:
                template_content = self.get_random_template()

        # Ensure we have valid template content
        if not template_content:
            logger.warning("No template content obtained, using fallback")
            template_content = self._get_fallback_template()

        # Render template with content
        return self.render_template(
            template_content=template_content,
            content=content,
            channel_name=channel_name,
            category=category,
            image_url=image_url,
            headline=headline,
            district=district,
            **kwargs
        )

    async def generate_newscard_html_async(
        self,
        content: str,
        tenant_id: str = None,
        channel_id: str = None,
        channel_name: str = "News Channel",
        category: str = "News",
        template_name: str = None,
        image_url: str = None,
        db_client=None,
        headline: str = None,
        district: str = None,
        **kwargs
    ) -> str:
        """Async version: Generate complete newscard HTML with template assignment support"""

        # For template assignment lookups, only use channel_id if it's a valid UUID
        # For rotation tracking, use channel_id or fallback to channel_name
        assignment_channel_id = channel_id  # Only use if it's a UUID (None otherwise)
        rotation_channel_id = channel_id or channel_name  # For rotation tracking

        # Determine if we need templates with images
        with_images = image_url is not None

        # Get template
        template_content = None

        if template_name:
            # Try S3 first, then local cache
            template_content = await self.get_template_by_name_from_s3(template_name)
            if not template_content:
                logger.warning(f"Template '{template_name}' not found, using assigned/rotation")
                # Only check assignment if we have a valid channel_id UUID
                if assignment_channel_id and tenant_id and db_client:
                    template_content = await self.get_assigned_template_async(
                        tenant_id, assignment_channel_id, with_images, db_client
                    )
                if not template_content:
                    # Fall back to rotation
                    template_content = self.get_next_template(tenant_id or "default", rotation_channel_id, with_images, db_client)
        elif tenant_id and db_client and assignment_channel_id:
            # Use async method to check for assignments (only if we have a valid UUID)
            template_content = await self.get_assigned_template_async(
                tenant_id, assignment_channel_id, with_images, db_client
            )

        # If no template from assignment, use rotation
        if not template_content and tenant_id:
            # Fall back to sync rotation method
            template_content = self.get_next_template(tenant_id, rotation_channel_id, with_images, db_client)

        # If still no template (no tenant_id or rotation failed), use random selection
        if not template_content:
            # For random template, use image-supporting templates if image_url is provided
            available_templates = self._filter_templates_by_image_support(with_images)
            if available_templates:
                import random
                template_name = random.choice(available_templates)
                # Try to get from S3 first, then local cache
                template_content = await self.get_template_by_name_from_s3(template_name)
                if not template_content:
                    template_content = self.get_template_by_name(template_name)
                if not template_content:
                    template_content = self.get_random_template()
            else:
                template_content = self.get_random_template()

        # Ensure we have valid template content
        if not template_content:
            logger.warning("No template content obtained, using fallback")
            template_content = self._get_fallback_template()

        # Render template with content
        return self.render_template(
            template_content=template_content,
            content=content,
            channel_name=channel_name,
            category=category,
            image_url=image_url,
            headline=headline,
            district=district,
            **kwargs
        )

    def _get_fallback_template(self) -> str:
        """Get fallback template when no templates are available"""
        logger.warning("Using fallback template")
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        * {
            box-sizing: border-box;
        }
        
        body {
            background-color: #1a202c;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 1080px;
            min-height: 1080px;
            padding: 0;
            margin: 0;
            font-family: Arial, sans-serif;
        }
        
        .container {
            position: relative;
            text-align: center;
            color: white;
            width: 1080px;
            height: 1080px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }
        
        .inner-container {
            position: relative;
            text-align: center;
            color: white;
            width: 950px;
            height: 870px;
            background-color: white;
            border-radius: 16px;
            display: flex;
            align-items: stretch;
            justify-content: start;
            flex-direction: column;
        }
        
        .heading-row {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 40px;
            background: linear-gradient(135deg, #4299e1, #3182ce);
            border-radius: 16px 16px 0 0;
        }
        
        .footer-row {
            width: 950px;
            height: 80px;
            display: flex;
            align-items: end;
            justify-content: stretch;
            background: #f7fafc;
            border-radius: 0 0 16px 16px;
        }
        
        .inner-footer-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            padding: 0 40px;
        }
        
        .inner-footer-row > div {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }
        
        .pill {
            padding: 6px 12px;
            border: 2px solid #4299e1;
            border-radius: 20px;
            color: #2d3748;
            font-size: 16px;
            font-family: sans-serif;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .news {
            color: white;
            font-size: 24px;
            font-weight: bold;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 8px;
            text-transform: uppercase;
            font-family: sans-serif;
            backdrop-filter: blur(5px);
        }
        
        .centered {
            color: #2d3748;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 40px 50px;
            flex-grow: 1;
            flex-direction: column;
        }
        
        .centered span {
            max-width: 100%;
            max-height: 100%;
            font-size: 70px;
            line-height: 1.2;
            word-wrap: break-word;
            margin-bottom: 12px;
            font-weight: bold;
        }
    </style>
    <title>{{channel_name}} - News</title>
</head>

<body>
    <div class="container">
        <div class="inner-container">
            <div class="heading-row">
                <div class="news">{{{{category}}}}</div>
                <div class="logo-wrapper">
                    <img class="logo" src="{{{{logo_url}}}}" alt="{{{{channel_name}}}}" style="height: 35px;" />
                </div>
            </div>
            <div class="centered">
                <span>{{{{content}}}}</span>
            </div>
        </div>
        <div class="footer-row">
            <div class="inner-footer-row">
                <div>
                    <div class="pill">{{{{website}}}}</div>
                </div>
                <div>
                    <div class="pill">{{{{source}}}}</div>
                    <div class="pill date">
                        <div>{{{{date}}}}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function adjustFontSize() {
            const container = document.querySelector(".centered");
            const textElement = container.querySelector("span");

            let buffer = 24;
            let fontSize = 70;
            textElement.style.fontSize = fontSize + "px";

            while (
                (textElement.scrollHeight + buffer > container.clientHeight) &&
                fontSize > 12
            ) {
                fontSize -= 2;
                textElement.style.fontSize = fontSize + "px";
            }
        }

        window.addEventListener("load", adjustFontSize);
        window.addEventListener("resize", adjustFontSize);
    </script>
</body>
</html>"""

# Global instance
newscard_template_service = NewscardTemplateService()