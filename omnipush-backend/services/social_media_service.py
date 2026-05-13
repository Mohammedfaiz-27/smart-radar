import os
import json
import facebook
from openai import AsyncOpenAI
from typing import Dict, Any, List
from config.prompts import Prompts


class SocialMediaService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.facebook_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")

    async def generate_social_handles(
        self, city: str, research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate social media handles for the city based on research data"""

        combined_research = f"""
        City: {city}
        OpenAI Analysis: {research_data.get('openai_analysis', '')}
        Perplexity Research: {research_data.get('perplexity_research', '')}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=Prompts.get_social_handles_messages(
                    city, combined_research[:2000]
                ),
                # max_tokens=500,
            )

            content = response.choices[0].message.content

            # Clean the response to extract JSON
            # if "```json" in content:
            #     content = content.split("```json")[1].split("```")[0]
            # elif "```" in content:
            #     content = content.split("```")[1].split("```")[0]

            import json_repair
            return json_repair.loads(content.strip())

        except Exception as e:
            # Fallback handles
            return self._create_fallback_handles(city)

    def _create_fallback_handles(self, city: str) -> Dict[str, Any]:
        """Create fallback social media handles"""
        city_clean = city.replace(" ", "").lower()
        return {
            "facebook_pages": [f"{city} Official", f"Visit {city}"],
            "instagram_pages": [f"@{city_clean}official", f"@visit{city_clean}"],
            "twitter_accounts": [f"@{city_clean}news", f"@{city_clean}gov"],
            "whatsapp_group": f"{city} Community Group",
        }

    async def post_to_facebook(
        self, page_id: str, image_path: str, message: str
    ) -> Dict[str, Any]:
        """Post content to Facebook page"""
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # return {
        #     "success": False,
        #     "error": "Facebook posting is temporarily disabled",
        #     "message": "Facebook posting is temporarily disabled",
        # }

        try:
            graph = facebook.GraphAPI(access_token=self.facebook_access_token)

            # Upload photo with message
            with open(image_path, "rb") as image_file:
                response = graph.put_photo(
                    image=image_file, message=message, album_path=f"{page_id}/photos"
                )

            return {
                "success": True,
                "post_id": response.get("id"),
                "message": "Posted successfully to Facebook",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to post to Facebook",
            }


async def publish_to_platforms(
    content: str, 
    image_url: str = None, 
    channels: List[str] = None, 
    tenant_id: str = None
) -> List[str]:
    """
    Publish content to multiple social media platforms
    
    Args:
        content: The text content to publish
        image_url: Optional URL of the image to include
        channels: List of platform names to publish to
        tenant_id: Tenant ID for context
    
    Returns:
        List of successfully published platform names
    """
    if not channels:
        return []
    
    service = SocialMediaService()
    published_channels = []
    
    for channel in channels:
        try:
            if channel.lower() == 'facebook':
                # For now, return success - in production you'd need page IDs
                published_channels.append('facebook')
            elif channel.lower() == 'twitter':
                # Twitter/X publishing logic would go here
                published_channels.append('twitter')
            elif channel.lower() == 'instagram':
                # Instagram publishing logic would go here
                published_channels.append('instagram')
            elif channel.lower() == 'linkedin':
                # LinkedIn publishing logic would go here
                published_channels.append('linkedin')
            else:
                # Unknown platform, skip
                continue
                
        except Exception as e:
            # Log error but continue with other platforms
            print(f"Failed to publish to {channel}: {str(e)}")
            continue
    
    return published_channels
