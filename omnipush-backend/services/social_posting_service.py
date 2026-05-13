import base64
import json
import logging
import mimetypes
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Optional, List
import requests

from services.social_accounts_service import SocialAccountsService, SocialAccount
from core.database import get_database

logger = logging.getLogger("social-posting-service")


@dataclass
class PostResponse:
    platform: str
    post_id: Optional[str] = None
    media_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SocialPlatformService:
    """Base class for social platform services"""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = logging.getLogger(f"social-posting-service.{platform_name.lower()}")

    def post(self, **kwargs) -> PostResponse:
        raise NotImplementedError("Subclasses must implement the post method")


class FacebookService(SocialPlatformService):
    """Facebook posting service"""

    def __init__(self):
        super().__init__("Facebook")

    def _send_api_request(self, url: str, payload: Dict[str, str]) -> str:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Facebook API error: {response.text}")

        data = response.json()
        post_id = data.get("id")
        if not post_id:
            raise RuntimeError(f"Unexpected Facebook response: {data}")
        return post_id

    def post(self, user_id: str, token: str, media_url: str, caption: str, media_type: str) -> PostResponse:
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # self.logger.warning("Facebook posting is temporarily disabled")
        # return PostResponse(
        #     platform=self.platform_name,
        #     media_url=media_url,
        #     error="Facebook posting is temporarily disabled"
        # )

        try:
            self.logger.info(f"Posting to Facebook - User: {user_id}, Media Type: {media_type}, Has Media: {bool(media_url)}")

            # Check if this is a link-only post (no media)
            # A link post is when there's no media and content contains a URL
            content_has_link = 'http://' in caption or 'https://' in caption
            is_link_post = not media_url and content_has_link

            if is_link_post:
                # Link post - use /feed endpoint for auto link preview
                self.logger.info(f"Detected link post, using /feed endpoint for preview generation")
                url = f"https://graph.facebook.com/v23.0/{user_id}/feed"

                # Extract the URL from the caption
                # Find the first URL in the text
                words = caption.split()
                link_url = None
                for word in words:
                    if word.startswith(('http://', 'https://')):
                        link_url = word.strip()
                        break

                if not link_url:
                    # Fallback: assume entire caption is the link
                    link_url = caption.strip()

                # Check if there's additional text (message) besides the link
                caption_without_link = caption.replace(link_url, '').strip()

                if caption_without_link:
                    # Link + message
                    payload = {
                        "link": link_url,
                        "message": caption_without_link,
                        "access_token": token,
                    }
                    self.logger.info(f"Link post with message: '{caption_without_link[:30]}...' + {link_url[:50]}")
                else:
                    # Just the link
                    payload = {
                        "link": link_url,
                        "access_token": token,
                    }
                    self.logger.info(f"Link-only post: {link_url[:60]}")
            elif media_type == "VIDEO":
                # Video post
                url = f"https://graph.facebook.com/v23.0/{user_id}/videos"
                payload = {
                    "file_url": media_url,
                    "description": caption,
                    "access_token": token,
                }
            else:
                # Image post
                url = f"https://graph.facebook.com/v23.0/{user_id}/photos"
                payload = {
                    "url": media_url,
                    "caption": caption,
                    "access_token": token,
                }

            post_id = self._send_api_request(url, payload)
            self.logger.info(f"Successfully posted to Facebook - Post ID: {post_id}")

            return PostResponse(
                platform=self.platform_name,
                post_id=post_id,
                media_url=media_url,
                message="Post published successfully",
            )
        except Exception as exc:
            self.logger.error(f"Failed to post to Facebook: {str(exc)}")
            return PostResponse(platform=self.platform_name, media_url=media_url, error=str(exc))


class InstagramService(SocialPlatformService):
    """Instagram posting service"""

    def __init__(self):
        super().__init__("Instagram")

    def _create_media_object(
        self,
        user_id: str,
        token: str,
        media_url: str,
        caption: str,
        media_type: str,
        post_type: str = "feed",
    ) -> str:
        payload: Dict[str, str] = {"caption": caption}

        if media_type == "IMAGE":
            payload["media_type"] = "IMAGE"
            payload["image_url"] = media_url
        else:
            if post_type == "reel":
                payload["media_type"] = "REELS"
                payload["video_url"] = media_url
                payload["thumb_offset"] = "0"
            else:
                payload["media_type"] = "REELS"
                payload["video_url"] = media_url

        url = f"https://graph.facebook.com/v23.0/{user_id}/media"
        response = requests.post(url, params={"access_token": token}, json=payload, timeout=30)
        data = response.json()

        if response.status_code != 200:
            raise RuntimeError(f"Instagram API error: {data}")

        media_id = data.get("id")
        if not media_id:
            raise RuntimeError(f"Could not retrieve media ID: {data}")
        return media_id

    def _wait_for_media_processing(
        self, user_id: str, token: str, media_id: str, media_type: str, poll_interval: int = 5, timeout: int = 300
    ) -> None:
        """Wait for Instagram to finish processing media (both IMAGE and VIDEO)

        Instagram needs time to download and process media from the provided URL.
        This applies to both images and videos before they can be published.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            url = f"https://graph.facebook.com/v23.0/{media_id}"
            response = requests.get(url, params={"fields": "status_code", "access_token": token}, timeout=30)
            data = response.json()

            status = data.get("status_code")
            if status == "FINISHED":
                self.logger.info(f"Instagram {media_type} processing finished - Media ID: {media_id}")
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram {media_type} processing failed: {data}")

            time.sleep(poll_interval)

        raise RuntimeError(f"Instagram {media_type} processing timed out after {timeout}s.")

    def _publish_media(self, user_id: str, token: str, media_id: str) -> str:
        url = f"https://graph.facebook.com/v23.0/{user_id}/media_publish"
        response = requests.post(url, params={"access_token": token}, json={"creation_id": media_id}, timeout=30)
        data = response.json()

        if response.status_code != 200:
            raise RuntimeError(f"Instagram publish error: {data}")

        post_id = data.get("id")
        if not post_id:
            raise RuntimeError(f"Could not retrieve Instagram post ID: {data}")
        return post_id

    def post(self, user_id: str, token: str, media_url: str, caption: str, media_type: str) -> PostResponse:
        try:
            self.logger.info(f"Posting to Instagram - User: {user_id}, Media Type: {media_type}")

            # Create media container (Instagram downloads media from URL)
            media_id = self._create_media_object(user_id, token, media_url, caption, media_type)

            # Wait for Instagram to finish processing media (both IMAGE and VIDEO)
            # Instagram needs time to download and process the media before it can be published
            self.logger.info(f"Waiting for Instagram {media_type} processing - Media ID: {media_id}")
            self._wait_for_media_processing(user_id, token, media_id, media_type)

            # Publish the media container
            post_id = self._publish_media(user_id, token, media_id)
            self.logger.info(f"Successfully posted to Instagram - Post ID: {post_id}")

            return PostResponse(
                platform=self.platform_name,
                post_id=post_id,
                media_url=media_url,
                message="Post published successfully",
            )
        except Exception as exc:
            self.logger.error(f"Failed to post to Instagram: {str(exc)}")
            return PostResponse(platform=self.platform_name, media_url=media_url, error=str(exc))


class ThreadsService(SocialPlatformService):
    """Threads posting service"""

    def __init__(self):
        super().__init__("Threads")

    def post(self, user_id: str, token: str, caption: str, media_url: Optional[str]) -> PostResponse:
        try:
            self.logger.info(f"Posting to Threads - User: {user_id}")

            payload = {"text": caption}
            if media_url:
                payload["media_url"] = media_url

            url = f"https://graph.threads.net/v23.0/{user_id}/posts"
            response = requests.post(url, params={"access_token": token}, json=payload, timeout=30)

            if response.status_code != 200:
                raise RuntimeError(f"Threads API error: {response.text}")

            data = response.json()
            post_id = data.get("id")
            if not post_id:
                raise RuntimeError(f"Could not retrieve Threads post ID: {data}")

            self.logger.info(f"Successfully posted to Threads - Post ID: {post_id}")

            return PostResponse(
                platform=self.platform_name,
                post_id=post_id,
                media_url=media_url,
                message="Post published successfully",
            )
        except Exception as exc:
            self.logger.error(f"Failed to post to Threads: {str(exc)}")
            return PostResponse(platform=self.platform_name, media_url=media_url, error=str(exc))


class WhatsAppService(SocialPlatformService):
    """WhatsApp posting service using Periskope API"""

    def __init__(self):
        super().__init__("WhatsApp")

    def _get_media_type_and_mimetype(self, file_path_or_url: str) -> tuple[str, str, str]:
        """
        Determine media type, MIME type, and appropriate filename for WhatsApp media.

        Returns:
            Tuple of (media_type, mimetype, filename)
        """
        # Get MIME type
        if os.path.exists(file_path_or_url):
            mimetype, _ = mimetypes.guess_type(file_path_or_url)
            filename = os.path.basename(file_path_or_url)
        else:
            # For URLs, try to guess from extension
            mimetype, _ = mimetypes.guess_type(file_path_or_url)
            filename = os.path.basename(file_path_or_url.split('?')[0])  # Remove query params

        if not mimetype:
            # Default fallbacks based on common extensions
            lower_path = file_path_or_url.lower()
            if any(ext in lower_path for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                mimetype = 'image/jpeg' if '.jpg' in lower_path or '.jpeg' in lower_path else 'image/png'
            elif any(ext in lower_path for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']):
                mimetype = 'video/mp4'
            else:
                mimetype = 'application/octet-stream'

        # Determine media type for WhatsApp
        if mimetype.startswith('image/'):
            media_type = 'image'
            if not filename or '.' not in filename:
                filename = 'image.jpg'
        elif mimetype.startswith('video/'):
            media_type = 'video'
            # Force all videos to MP4 mimetype for WhatsApp compatibility
            mimetype = 'video/mp4'
            if not filename or '.' not in filename:
                filename = 'video.mp4'
        else:
            media_type = 'document'
            if not filename or '.' not in filename:
                filename = 'file.bin'

        return media_type, mimetype, filename

    def post(
        self,
        group_id: str,
        message: str,
        media_url: Optional[str] = None,
        api_key: Optional[str] = None,
        sender_phone: Optional[str] = None
    ) -> PostResponse:
        """
        Post a message (and optional media) to a WhatsApp group using Periskope API.

        Args:
            group_id: WhatsApp group ID
            message: Text message to send
            media_url: Optional URL or local path to media file
            api_key: Periskope API key (uses env var PERISKOPE_API_KEY if not provided)
            sender_phone: Sender phone number (uses env var WHATSAPP_SENDER_PHONE if not provided)
        """
        try:
            # Get API key and sender phone
            periskope_api_key = api_key or os.getenv("PERISKOPE_API_KEY")
            if not periskope_api_key:
                return PostResponse(
                    platform=self.platform_name,
                    error="PERISKOPE_API_KEY not configured"
                )

            sender = (
                sender_phone
                or os.getenv("WHATSAPP_SENDER_PHONE")
                or os.getenv("PERISKOPE_X_PHONE")
                or "+918189900456"  # Default fallback
            )

            self.logger.info(f"Posting to WhatsApp - Group: {group_id}, Has Media: {bool(media_url)}")

            url = "https://api.periskope.app/v1/message/send"
            headers = {
                "Authorization": f"Bearer {periskope_api_key}",
                "Content-Type": "application/json",
                "x-phone": sender,
            }

            # Check if message is a link (starts with http:// or https://)
            is_link = message.strip().startswith(('http://', 'https://'))

            # For link messages, ensure clean formatting
            if is_link and not media_url:
                # Ensure the link is clean and on a single line
                clean_link = message.strip()
                # Remove any trailing/leading whitespace or newlines
                clean_link = ' '.join(clean_link.split())
                payload: Dict = {"chat_id": group_id, "message": clean_link}
                self.logger.info(f"Sending link message: {clean_link[:50]}...")
            else:
                payload: Dict = {"chat_id": group_id, "message": message}

            # Handle media if provided
            if media_url:
                # Clean up local paths
                if media_url.startswith("/static"):
                    media_url = media_url.replace("/static", "static")
                if media_url.startswith("/media"):
                    media_url = media_url.replace("/media", "media")

                # Determine media type and MIME type
                media_type, mimetype, filename = self._get_media_type_and_mimetype(media_url)

                # Check if it's a local file path
                if os.path.exists(media_url):
                    try:
                        with open(media_url, "rb") as media_file:
                            base64_media = base64.b64encode(media_file.read()).decode("utf-8")
                        payload["media"] = {
                            "type": media_type,
                            "filename": filename,
                            "mimetype": mimetype,
                            "filedata": base64_media,
                        }
                    except Exception as e:
                        self.logger.error(f"Failed to read local media file {media_url}: {e}")
                        return PostResponse(
                            platform=self.platform_name,
                            error=f"Failed to read media file: {str(e)}"
                        )
                else:
                    # Remote URL
                    payload["media"] = {
                        "type": media_type,
                        "filename": filename,
                        "mimetype": mimetype,
                        "url": media_url,
                    }

            # Send the message
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            try:
                data = response.json()
            except ValueError:
                data = {"status": response.status_code, "text": response.text}

            if response.status_code == 200:
                self.logger.info(f"Successfully posted to WhatsApp - Group: {group_id}")
                return PostResponse(
                    platform=self.platform_name,
                    post_id=data.get("message_id", group_id),  # Use message_id if available
                    media_url=media_url,
                    message="Message sent successfully",
                )
            else:
                raise RuntimeError(f"WhatsApp API error: {data}")

        except Exception as exc:
            self.logger.error(f"Failed to post to WhatsApp: {str(exc)}")
            return PostResponse(
                platform=self.platform_name,
                media_url=media_url,
                error=str(exc)
            )


class SocialPostingService:
    """Main service for posting to social platforms using database-stored credentials"""

    def __init__(self):
        self.facebook = FacebookService()
        self.instagram = InstagramService()
        self.threads = ThreadsService()
        self.whatsapp = WhatsAppService()
        self.accounts_service = SocialAccountsService()
        self.db = get_database()
        self.logger = logging.getLogger("social-posting-service")

    # Legacy methods for backward compatibility (direct credential passing)
    def post_to_facebook(self, user_id: str, token: str, media_url: str, caption: str, media_type: str) -> PostResponse:
        return self.facebook.post(user_id, token, media_url, caption, media_type)

    def post_to_instagram(self, user_id: str, token: str, media_url: str, caption: str, media_type: str) -> PostResponse:
        return self.instagram.post(user_id, token, media_url, caption, media_type)

    def post_to_threads(self, user_id: str, token: str, caption: str, media_url: Optional[str]) -> PostResponse:
        return self.threads.post(user_id, token, caption, media_url)

    def post_to_whatsapp(
        self,
        group_id: str,
        message: str,
        media_url: Optional[str] = None,
        api_key: Optional[str] = None,
        sender_phone: Optional[str] = None
    ) -> PostResponse:
        return self.whatsapp.post(group_id, message, media_url, api_key, sender_phone)

    # New database-driven methods
    def post_to_account(
        self,
        account_id: str,
        tenant_id: str,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> PostResponse:
        """
        Post content to a specific social account using database-stored credentials

        Args:
            account_id: Social account ID from database
            tenant_id: Tenant ID for security validation
            content: Content to post (caption/message)
            media_url: Optional media URL
            media_type: Media type ('IMAGE' or 'VIDEO')

        Returns:
            PostResponse with result details
        """
        try:
            # Fetch account credentials from database
            account = self.accounts_service.get_account_by_id(account_id, tenant_id)

            if not account:
                return PostResponse(
                    platform="unknown",
                    error=f"Social account {account_id} not found for tenant {tenant_id}"
                )

            if account.status != 'connected':
                return PostResponse(
                    platform=account.platform,
                    error=f"Account {account.account_name} is not connected (status: {account.status})"
                )

            # Route to appropriate platform service
            if account.platform == 'facebook':
                return self._post_to_facebook_account(account, content, media_url, media_type)
            elif account.platform == 'instagram':
                return self._post_to_instagram_account(account, content, media_url, media_type)
            elif account.platform == 'threads':
                return self._post_to_threads_account(account, content, media_url)
            elif account.platform == 'whatsapp':
                return self._post_to_whatsapp_account(account, content, media_url)
            else:
                return PostResponse(
                    platform=account.platform,
                    error=f"Platform {account.platform} not yet supported"
                )

        except Exception as e:
            self.logger.error(f"Error posting to account {account_id}: {e}")
            return PostResponse(
                platform="unknown",
                error=f"Failed to post: {str(e)}"
            )

    def post_to_platform_accounts(
        self,
        tenant_id: str,
        platform: str,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> List[PostResponse]:
        """
        Post content to all connected accounts for a specific platform

        Args:
            tenant_id: Tenant ID
            platform: Platform name ('facebook', 'instagram', 'whatsapp', etc.)
            content: Content to post
            media_url: Optional media URL
            media_type: Media type ('IMAGE' or 'VIDEO')

        Returns:
            List of PostResponse objects for each account
        """
        results = []

        try:
            # Get all connected accounts for the platform
            accounts = self.accounts_service.get_connected_accounts(tenant_id, platform)

            if not accounts:
                self.logger.warning(f"No connected {platform} accounts found for tenant {tenant_id}")
                return [PostResponse(
                    platform=platform,
                    error=f"No connected {platform} accounts found"
                )]

            # Post to each account
            for account in accounts:
                response = self.post_to_account(
                    account.id,
                    tenant_id,
                    content,
                    media_url,
                    media_type
                )
                results.append(response)

        except Exception as e:
            self.logger.error(f"Error posting to {platform} accounts for tenant {tenant_id}: {e}")
            results.append(PostResponse(
                platform=platform,
                error=f"Failed to post to {platform}: {str(e)}"
            ))

        return results

    def post_to_all_accounts(
        self,
        tenant_id: str,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, List[PostResponse]]:
        """
        Post content to all connected accounts across platforms

        Args:
            tenant_id: Tenant ID
            content: Content to post
            media_url: Optional media URL
            media_type: Media type ('IMAGE' or 'VIDEO')
            platforms: Optional list of platforms to post to

        Returns:
            Dictionary with platform as key and list of PostResponse as value
        """
        results = {}

        try:
            # Get all connected accounts
            all_accounts = self.accounts_service.get_connected_accounts(tenant_id)

            if not all_accounts:
                self.logger.warning(f"No connected accounts found for tenant {tenant_id}")
                return {"error": [PostResponse(
                    platform="all",
                    error="No connected social accounts found"
                )]}

            # Group accounts by platform
            platform_accounts = {}
            for account in all_accounts:
                if platforms and account.platform not in platforms:
                    continue

                if account.platform not in platform_accounts:
                    platform_accounts[account.platform] = []
                platform_accounts[account.platform].append(account)

            # Post to each platform
            for platform, accounts in platform_accounts.items():
                results[platform] = []
                for account in accounts:
                    response = self.post_to_account(
                        account.id,
                        tenant_id,
                        content,
                        media_url,
                        media_type
                    )
                    results[platform].append(response)

        except Exception as e:
            self.logger.error(f"Error posting to all accounts for tenant {tenant_id}: {e}")
            results["error"] = [PostResponse(
                platform="all",
                error=f"Failed to post: {str(e)}"
            )]

        return results

    def _post_to_facebook_account(self, account: SocialAccount, content: str, media_url: Optional[str], media_type: Optional[str]) -> PostResponse:
        """Post to Facebook using account credentials"""
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # return PostResponse(
        #     platform=account.platform,
        #     error="Facebook posting is temporarily disabled"
        # )
        try:
            # Use page_id if available, otherwise use account_id
            user_id = account.page_id or account.account_id

            if not account.access_token:
                return PostResponse(
                    platform=account.platform,
                    error="No access token available for Facebook account"
                )

            return self.facebook.post(
                user_id=user_id,
                token=account.access_token,
                media_url=media_url or "",
                caption=content,
                media_type=media_type or "IMAGE"
            )
        except Exception as e:
            return PostResponse(
                platform=account.platform,
                error=f"Facebook posting error: {str(e)}"
            )

    def _post_to_instagram_account(self, account: SocialAccount, content: str, media_url: Optional[str], media_type: Optional[str]) -> PostResponse:
        """Post to Instagram using account credentials"""
        try:
            if not account.access_token:
                return PostResponse(
                    platform=account.platform,
                    error="No access token available for Instagram account"
                )

            return self.instagram.post(
                user_id=account.account_id,
                token=account.access_token,
                media_url=media_url or "",
                caption=content,
                media_type=media_type or "IMAGE"
            )
        except Exception as e:
            return PostResponse(
                platform=account.platform,
                error=f"Instagram posting error: {str(e)}"
            )

    def _post_to_threads_account(self, account: SocialAccount, content: str, media_url: Optional[str]) -> PostResponse:
        """Post to Threads using account credentials"""
        try:
            if not account.access_token:
                return PostResponse(
                    platform=account.platform,
                    error="No access token available for Threads account"
                )

            return self.threads.post(
                user_id=account.account_id,
                token=account.access_token,
                caption=content,
                media_url=media_url
            )
        except Exception as e:
            return PostResponse(
                platform=account.platform,
                error=f"Threads posting error: {str(e)}"
            )

    def _post_to_whatsapp_account(self, account: SocialAccount, content: str, media_url: Optional[str]) -> PostResponse:
        """Post to WhatsApp using account credentials"""
        try:
            if not account.periskope_id:
                return PostResponse(
                    platform=account.platform,
                    error="No Periskope ID available for WhatsApp account"
                )

            # Get API key from environment variables
            api_key = os.getenv("PERISKOPE_API_KEY")
            sender_phone = os.getenv("WHATSAPP_SENDER_PHONE") or "+918189900456"

            return self.whatsapp.post(
                group_id=account.periskope_id,
                message=content,
                media_url=media_url,
                api_key=api_key,
                sender_phone=sender_phone
            )
        except Exception as e:
            return PostResponse(
                platform=account.platform,
                error=f"WhatsApp posting error: {str(e)}"
            )

    def save_publish_results(
        self,
        post_id: str,
        tenant_id: str,
        results: Dict[str, List[PostResponse]],
        update_status: bool = True
    ) -> bool:
        """
        Save publish results to the posts table

        Args:
            post_id: Post ID to update
            tenant_id: Tenant ID for security validation
            results: Dictionary with platform as key and list of PostResponse as value
            update_status: Whether to update post status based on results

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert PostResponse objects to dictionaries for JSON storage
            publish_results = {}
            all_success = True

            for platform, responses in results.items():
                publish_results[platform] = []
                for response in responses:
                    result_dict = {
                        "platform": response.platform,
                        "post_id": response.post_id,
                        "media_url": response.media_url,
                        "message": response.message,
                        "error": response.error,
                        "success": response.error is None,
                        "published_at": datetime.utcnow().isoformat() if response.error is None else None
                    }
                    publish_results[platform].append(result_dict)

                    if response.error is not None:
                        all_success = False

            # Prepare update data
            update_data = {
                "publish_results": publish_results
            }

            # Update status if requested
            if update_status:
                update_data["status"] = "published" if all_success else "failed"
                if all_success:
                    update_data["published_at"] = datetime.utcnow().isoformat()

            # Update the post in database
            response = self.db.service_client.table("posts").update(update_data).eq("id", post_id).eq("tenant_id", tenant_id).execute()

            if response.data:
                self.logger.info(f"Successfully saved publish results for post {post_id}")
                return True
            else:
                self.logger.error(f"Failed to save publish results for post {post_id}: No data returned")
                return False

        except Exception as e:
            self.logger.error(f"Error saving publish results for post {post_id}: {e}")
            return False