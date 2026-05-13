import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

class FacebookSimpleClient:
    def __init__(self, user_access_token: Optional[str] = None, db_client=None, tenant_id: Optional[str] = None):
        """
        user_access_token: A valid Facebook user access token with pages_show_list and pages_manage_posts permissions.
        If not provided, will try FB_USER_ACCESS_TOKEN from environment.
        db_client: Supabase client for caching
        tenant_id: Tenant ID for multi-tenant caching
        """
        self.user_access_token = user_access_token or os.getenv("FB_USER_ACCESS_TOKEN")
        if not self.user_access_token:
            raise ValueError("Missing user access token. Provide it or set FB_USER_ACCESS_TOKEN.")
        
        self.db_client = db_client
        self.tenant_id = tenant_id
        self.cache_duration_hours = 24  # Cache pages for 24 hours

    def _get_db_client(self):
        """Get the appropriate database client (service_client if wrapper, or raw client)"""
        if hasattr(self.db_client, 'service_client'):
            return self.db_client.service_client
        return self.db_client

    # --------------------------------
    # Long-lived token helper
    # --------------------------------
    @staticmethod
    def exchange_for_long_lived_user_token(app_id: str, app_secret: str, short_lived_token: str) -> Dict:
        """
        Exchanges a short-lived user access token for a long-lived token (approx 60 days).
        Returns the full JSON payload from Graph API which typically contains:
          - access_token
          - token_type
          - expires_in (seconds)
        """
        url = f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_token,
        }
        resp = requests.get(url, params=params, timeout=30)
        payload = FacebookSimpleClient._raise_for_graph_error(resp)
        return payload

    def get_all_pages(self, use_cache: bool = True) -> List[Dict]:
        """
        Fetch all pages the user has access to (handles pagination).
        Returns a list of page objects including id, name, access_token (if granted).
        
        Args:
            use_cache: Whether to use cached pages if available
        """
        # Try to get from cache first if enabled
        if use_cache and self.db_client and self.tenant_id:
            cached_pages = self._get_cached_pages()
            if cached_pages:
                logger.info(f"Retrieved {len(cached_pages)} pages from cache")
                return cached_pages
        
        # Fetch from Facebook API
        logger.info("Fetching pages from Facebook API")
        pages: List[Dict] = []
        url = f"{GRAPH_BASE}/me/accounts"
        params = {"access_token": self.user_access_token}

        while True:
            resp = requests.get(url, params=params, timeout=30)
            data = self._raise_for_graph_error(resp)
            pages.extend(data.get("data", []))

            paging = data.get("paging", {})
            next_url = paging.get("next")
            if not next_url:
                break
            # For next page, use provided next URL directly
            url = next_url
            params = {}  # next already contains token and cursors
        
        # Cache the pages if caching is enabled
        if use_cache and self.db_client and self.tenant_id:
            self._cache_pages(pages)
            
        return pages

    def get_page_details_by_name(self, page_name_query: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Find a page by case-insensitive partial name match among user's pages.
        Returns: { page_id, page_name, page_access_token } or None if not found.
        
        Args:
            page_name_query: Name of the page to search for
            use_cache: Whether to use cached pages if available
        """
        pages = self.get_all_pages(use_cache=use_cache)
        # Prefer exact case-insensitive match, then first partial match
        exact = [p for p in pages if p.get("name", "").lower() == page_name_query.lower()]
        if exact:
            p = exact[0]
            result = {
                "page_id": p["id"],
                "page_name": p["name"],
                "page_access_token": p.get("access_token"),
            }
            # Update last accessed time if caching is enabled
            if use_cache and self.db_client and self.tenant_id:
                self._update_page_last_accessed(p["id"])
            return result

        partial = [p for p in pages if page_name_query.lower() in p.get("name", "").lower()]
        if partial:
            p = partial[0]
            result = {
                "page_id": p["id"],
                "page_name": p["name"],
                "page_access_token": p.get("access_token"),
            }
            # Update last accessed time if caching is enabled
            if use_cache and self.db_client and self.tenant_id:
                self._update_page_last_accessed(p["id"])
            return result
        return None
    
    def get_page_details_by_id(self, page_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Find a page by its ID among user's pages.
        Returns: { page_id, page_name, page_access_token } or None if not found.
        
        Args:
            page_id: ID of the page to find
            use_cache: Whether to use cached pages if available
        """
        pages = self.get_all_pages(use_cache=use_cache)
        for p in pages:
            if p.get("id") == page_id:
                result = {
                    "page_id": p["id"],
                    "page_name": p["name"],
                    "page_access_token": p.get("access_token"),
                }
                # Update last accessed time if caching is enabled
                if use_cache and self.db_client and self.tenant_id:
                    self._update_page_last_accessed(page_id)
                return result
        return None

    def post_images_then_feed(self, page_id: str, page_access_token: str, message: str, image_paths: List[str]) -> Dict:
        """
        Uploads images to the page (unpublished) and then creates a feed post attaching them with a message.
        Images can be either local file paths or HTTP URLs.
        Returns the Graph API response from the feed post.
        """
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # raise RuntimeError("Facebook posting is temporarily disabled")

        if not image_paths:
            raise ValueError("image_paths must contain at least one path or URL.")

        # Step 1: Upload each image to get media_fbid
        media_fbids: List[str] = []
        for path in image_paths:
            photo_id = self._upload_photo_unpublished(page_id, page_access_token, path)
            media_fbids.append(photo_id)

        # Step 2: Create feed post with attached_media
        feed_url = f"{GRAPH_BASE}/{page_id}/feed"
        data = {
            "message": message,
            "access_token": page_access_token,
        }
        for idx, media_fbid in enumerate(media_fbids):
            data[f"attached_media[{idx}]"] = f'{{"media_fbid":"{media_fbid}"}}'

        resp = requests.post(feed_url, data=data, timeout=60)
        return self._raise_for_graph_error(resp)

    # Internal helpers

    def _upload_photo_unpublished(self, page_id: str, page_access_token: str, image_path: str) -> str:
        """
        Upload a photo from either a local file path or HTTP URL.
        
        Args:
            page_id: Facebook page ID
            page_access_token: Page access token
            image_path: Either a local file path or HTTP URL to the image
            
        Returns:
            The Facebook photo ID
        """
        photos_url = f"{GRAPH_BASE}/{page_id}/photos"

        if image_path.startswith("/static"):
            image_path = image_path.replace("/static", "static")
        
        if image_path.startswith("/media"):
            image_path = image_path.replace("/media", "media")

        # Check if image_path is a local file or HTTP URL
        if self._is_local_file(image_path):
            # Upload local file
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Local image file not found: {image_path}")
                
            data = {
                "access_token": page_access_token,
                "published": "false",
            }
            
            with open(image_path, 'rb') as image_file:
                files = {'source': image_file}
                resp = requests.post(photos_url, data=data, files=files, timeout=60)
        else:
            # Upload from URL
            data = {
                "access_token": page_access_token,
                "url": image_path,
                "published": "false",
            }
            resp = requests.post(photos_url, data=data, timeout=60)
        
        response_data = self._raise_for_graph_error(resp)
        if "id" not in response_data:
            raise RuntimeError(f"Photo upload response missing id: {response_data}")
        return response_data["id"]

    def _is_local_file(self, path: str) -> bool:
        """
        Determine if a path is a local file path or HTTP URL.
        
        Args:
            path: The path to check
            
        Returns:
            True if it's a local file path, False if it's a URL
        """
        parsed = urlparse(path)
        # If it has a scheme (http, https, etc.) and netloc, it's a URL
        return not (parsed.scheme and parsed.netloc)

    def _get_cached_pages(self) -> Optional[List[Dict]]:
        """
        Retrieve cached pages from database if they exist and are not expired.
        Returns list of pages or None if cache miss/expired.
        """
        if not self.db_client or not self.tenant_id:
            return None
            
        try:
            # Get user account record
            user_account = self._get_or_create_user_account()
            if not user_account:
                return None
                
            # Check for cached pages that are not expired
            cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_duration_hours)
            
            result = self._get_db_client().table('facebook_pages_cache').select(
                'page_id, page_name, page_access_token, category, category_list, tasks, access_token_expires_at'
            ).eq(
                'tenant_id', self.tenant_id
            ).eq(
                'facebook_user_account_id', user_account['id']
            ).gte(
                'updated_at', cutoff_time.isoformat()
            ).execute()
            
            if not result.data:
                return None
                
            # Convert to Facebook API format
            pages = []
            for row in result.data:
                pages.append({
                    'id': row['page_id'],
                    'name': row['page_name'],
                    'access_token': row['page_access_token'],
                    'category': row['category'],
                    'category_list': row['category_list'],
                    'tasks': row['tasks']
                })
                
            return pages
            
        except Exception as e:
            # Check if it's an RLS policy error
            if 'row-level security policy' in str(e).lower():
                logger.warning("RLS policy blocking Facebook cache access - disabling caching for this session")
                # Disable caching for this instance
                self.db_client = None
                self.tenant_id = None
            else:
                logger.exception(f"Error retrieving cached pages: {e}")
            return None
    
    def _cache_pages(self, pages: List[Dict]) -> None:
        """
        Cache pages in database.
        """
        if not self.db_client or not self.tenant_id or not pages:
            return
            
        try:
            # Get or create user account record
            user_account = self._get_or_create_user_account()
            if not user_account:
                logger.exception("Failed to get user account for caching pages")
                return
                
            # Clear existing cached pages for this user account
            self._get_db_client().table('facebook_pages_cache').delete().eq(
                'tenant_id', self.tenant_id
            ).eq(
                'facebook_user_account_id', user_account['id']
            ).execute()
            
            # Insert new cached pages
            cache_records = []
            for page in pages:
                cache_records.append({
                    'tenant_id': self.tenant_id,
                    'facebook_user_account_id': user_account['id'],
                    'page_id': page['id'],
                    'page_name': page['name'],
                    'page_access_token': page.get('access_token'),
                    'category': page.get('category'),
                    'category_list': page.get('category_list'),
                    'tasks': page.get('tasks')
                })
            
            if cache_records:
                self._get_db_client().table('facebook_pages_cache').insert(cache_records).execute()
                logger.info(f"Cached {len(cache_records)} pages for tenant {self.tenant_id}")
                
        except Exception as e:
            # Check if it's an RLS policy error
            if 'row-level security policy' in str(e).lower():
                logger.warning("RLS policy blocking Facebook cache access - disabling caching for this session")
                # Disable caching for this instance
                self.db_client = None
                self.tenant_id = None
            else:
                logger.exception(f"Error caching pages: {e}")
    
    def _get_or_create_user_account(self) -> Optional[Dict]:
        """
        Get or create a Facebook user account record in cache.
        Returns the user account record or None if error.
        """
        if not self.db_client or not self.tenant_id:
            return None
            
        try:
            # Try to get existing user account based on token (simplified)
            # In a real implementation, you'd decode the token to get user ID
            result = self._get_db_client().table('facebook_user_accounts').select('*').eq(
                'tenant_id', self.tenant_id
            ).eq(
                'user_access_token', self.user_access_token
            ).execute()
            
            if result.data:
                return result.data[0]
                
            # Create new user account record
            # Note: In production, you should get actual Facebook user ID from token
            user_data = {
                'tenant_id': self.tenant_id,
                'facebook_user_id': f'user_{hash(self.user_access_token) % 1000000}',  # Simplified
                'user_access_token': self.user_access_token,
                'token_type': 'user'
            }
            
            result = self._get_db_client().table('facebook_user_accounts').insert(user_data).execute()
            
            if result.data:
                return result.data[0]
                
        except Exception as e:
            # Check if it's an RLS policy error
            if 'row-level security policy' in str(e).lower():
                logger.warning("RLS policy blocking Facebook cache access - disabling caching for this session")
                # Disable caching for this instance
                self.db_client = None
                self.tenant_id = None
            else:
                logger.exception(f"Error getting or creating user account: {e}")
            
        return None
    
    def _update_page_last_accessed(self, page_id: str) -> None:
        """
        Update the last_accessed_at timestamp for a page.
        """
        if not self.db_client or not self.tenant_id:
            return
            
        try:
            self._get_db_client().table('facebook_pages_cache').update({
                'last_accessed_at': datetime.utcnow().isoformat()
            }).eq(
                'tenant_id', self.tenant_id
            ).eq(
                'page_id', page_id
            ).execute()
            
        except Exception as e:
            logger.exception(f"Error updating page last accessed: {e}")
    
    def clear_cache(self) -> bool:
        """
        Clear all cached data for this tenant.
        Returns True if successful, False otherwise.
        """
        if not self.db_client or not self.tenant_id:
            return False
            
        try:
            # Clear pages cache
            self._get_db_client().table('facebook_pages_cache').delete().eq(
                'tenant_id', self.tenant_id
            ).execute()
            
            # Clear user accounts cache
            self._get_db_client().table('facebook_user_accounts').delete().eq(
                'tenant_id', self.tenant_id
            ).execute()
            
            logger.info(f"Cleared Facebook cache for tenant {self.tenant_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error clearing cache: {e}")
            return False

    @staticmethod
    def _raise_for_graph_error(resp: requests.Response) -> Dict:
        """
        Raises an informative error if Graph API returned an error status or an 'error' object.
        Returns parsed JSON dict otherwise.
        """
        try:
            payload = resp.json()
        except Exception:
            resp.raise_for_status()
            raise

        if not resp.ok:
            raise RuntimeError(f"Graph API HTTP {resp.status_code}: {payload}")
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(f"Graph API Error: {payload['error']}")
        return payload


if __name__ == "__main__":
    """
    Example usage:

    1) Generate a long-lived token:
       - Set FB_APP_ID, FB_APP_SECRET, FB_SHORT_LIVED_TOKEN env vars
       - Run: python script.py token
       It will print the long-lived token JSON.

    2) Use a user access token (short or long-lived) to list pages and post:
       - Set FB_USER_ACCESS_TOKEN (or pass to FacebookSimpleClient)
       - Optionally set:
         FB_TARGET_PAGE_NAME (default: Newsit-Tamilnadu)
         FB_POST_MESSAGE (default: Hello from the simple utility!)
         FB_IMAGE_PATHS as pipe-separated paths (URLs or local file paths)
       - Run: python script.py post
    """
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "post"

    if mode == "token":
        app_id = os.getenv("FB_APP_ID", "").strip()
        app_secret = os.getenv("FB_APP_SECRET", "").strip()
        short_token = os.getenv("FB_SHORT_LIVED_TOKEN", "").strip()
        if not app_id or not app_secret or not short_token:
            raise SystemExit("Missing FB_APP_ID, FB_APP_SECRET, or FB_SHORT_LIVED_TOKEN env vars.")
        result = FacebookSimpleClient.exchange_for_long_lived_user_token(
            app_id=app_id, app_secret=app_secret, short_lived_token=short_token
        )
        print("Long-lived token response:", result)
        # Tip: export FB_USER_ACCESS_TOKEN to the returned access_token for ongoing use.
        sys.exit(0)

    # Default flow: list pages and post
    TARGET_PAGE_NAME = os.getenv("FB_TARGET_PAGE_NAME", "Newsit-Tamilnadu")
    MESSAGE = os.getenv("FB_POST_MESSAGE", "Hello from the simple utility!")
    IMAGE_PATHS = [u for u in os.getenv("FB_IMAGE_PATHS", "").split("|") if u] or [
        "https://example.com/your-image-1.jpg"  # Can also use local paths like "/path/to/image.jpg"
    ]

    client = FacebookSimpleClient()
    print("Fetching all pages...")
    pages = client.get_all_pages()
    print(f"Found {len(pages)} pages.")
    for p in pages:
        print(f"- {p.get('name')} (id={p.get('id')})")

    print(f"\nLooking up page: {TARGET_PAGE_NAME}")
    details = client.get_page_details_by_name(TARGET_PAGE_NAME)
    if not details or not details.get("page_access_token"):
        raise SystemExit(f"Page '{TARGET_PAGE_NAME}' not found or missing page access token.")

    print(f"Posting to page '{details['page_name']}' (id={details['page_id']})...")
    result = client.post_images_then_feed(
        page_id=details["page_id"],
        page_access_token=details["page_access_token"],
        message=MESSAGE,
        image_paths=IMAGE_PATHS,
    )
    print("Post result:", result)