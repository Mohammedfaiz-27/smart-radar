import base64
import os
import logging
import mimetypes
import subprocess
import tempfile
import warnings
from typing import List, Dict, Any, Optional

import requests


logger = logging.getLogger(__name__)


def _get_media_type_and_mimetype(file_path_or_url: str) -> tuple[str, str, str]:
    """
    Determine media type, MIME type, and appropriate filename for WhatsApp media.
    
    Args:
        file_path_or_url: Local file path or URL to media
        
    Returns:
        Tuple of (media_type, mimetype, filename)
        media_type: 'image', 'video', or 'document'
        mimetype: MIME type string
        filename: Appropriate filename with extension
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


def _convert_video_to_mp4(input_path: str, output_path: str = None) -> str:
    """
    Convert video to MP4 format using ffmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Optional output path. If None, creates a temp file.
        
    Returns:
        Path to converted MP4 file
        
    Raises:
        RuntimeError: If ffmpeg is not available or conversion fails
    """
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("ffmpeg is not installed or not available in PATH")
    
    # Create output path if not provided
    if output_path is None:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"converted_{os.path.basename(input_path)}.mp4")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Convert video to MP4 with optimized settings for WhatsApp
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',          # H.264 video codec
            '-c:a', 'aac',              # AAC audio codec  
            '-preset', 'fast',          # Encoding speed vs compression
            '-crf', '23',               # Quality (lower = better quality)
            '-movflags', '+faststart',  # Optimize for streaming
            '-y',                       # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Video converted successfully: {input_path} -> {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg conversion failed: {e.stderr}")
        raise RuntimeError(f"Video conversion failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error during video conversion: {e}")
        raise RuntimeError(f"Video conversion failed: {str(e)}")


def _is_video_file(file_path: str) -> bool:
    """Check if file is a video based on extension and mimetype."""
    media_type, _, _ = _get_media_type_and_mimetype(file_path)
    return media_type == 'video'


def convert_video_for_upload(file_content: bytes, original_filename: str) -> tuple[bytes, str, str]:
    """
    Utility function to convert uploaded video to MP4 format.
    
    Args:
        file_content: Original video file content as bytes
        original_filename: Original filename of the uploaded video
        
    Returns:
        Tuple of (converted_file_content, new_filename, new_content_type)
        
    Raises:
        RuntimeError: If video conversion fails or ffmpeg is not available
    """
    if not _is_video_file(original_filename) or original_filename.lower().endswith('.mp4'):
        # Return original content if not a video or already MP4
        return file_content, original_filename, "video/mp4" if _is_video_file(original_filename) else None
    
    import tempfile
    
    temp_input_path = None
    converted_file_path = None
    
    try:
        # Write uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_original_{original_filename}") as temp_file:
            temp_file.write(file_content)
            temp_input_path = temp_file.name
        
        # Convert to MP4
        logger.info(f"Converting video {original_filename} to MP4 format")
        converted_file_path = _convert_video_to_mp4(temp_input_path)
        
        # Read converted file content
        with open(converted_file_path, 'rb') as converted_file:
            converted_content = converted_file.read()
        
        # Generate new filename
        base_name = original_filename.rsplit('.', 1)[0]
        new_filename = f"{base_name}.mp4"
        new_content_type = "video/mp4"
        
        logger.info(f"Video conversion completed: {original_filename} -> {new_filename}")
        
        return converted_content, new_filename, new_content_type
        
    except Exception as e:
        logger.error(f"Video conversion failed for {original_filename}: {e}")
        raise RuntimeError(f"Video conversion failed: {str(e)}")
        
    finally:
        # Clean up temporary files
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp input file: {cleanup_error}")
        
        if converted_file_path and os.path.exists(converted_file_path):
            try:
                os.remove(converted_file_path)
                # Also remove temp directory if empty
                temp_dir = os.path.dirname(converted_file_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup converted file: {cleanup_error}")


def get_page_access_token(page_id: str, user_access_token: str) -> str:
    accounts = get_all_accounts(user_access_token)
    
    # Find the page by its ID instead of hardcoding the name
    page_details = None
    for account_name, account_info in accounts.items():
        if account_info["id"] == page_id:
            page_details = {
                "page_name": account_info["name"],
                "page_id": account_info["id"],
                "page_access_token": account_info["access_token"],
            }
            break
    
    if not page_details:
        raise ValueError(f"No page found with ID: {page_id}")
    
    return page_details


def _post_image_to_facebook_page(
    page_id: str, image_url: str, page_access_token: str
) -> str:
    """
    Upload an image (by URL) to the page as an unpublished photo, returning the media ID.
    """
    # DISABLING FACEBOOK - Temporarily disabled due to posting issues
    # raise RuntimeError("Facebook posting is temporarily disabled")
    post_url = f"https://graph.facebook.com/v22.0/{page_id}/photos"
    payload = {
        "access_token": page_access_token,
        "url": image_url,
        "published": False,
    }
    resp = requests.post(post_url, data=payload)
    data = resp.json()
    if resp.status_code != 200 or "id" not in data:
        raise RuntimeError(
            f"Failed to upload photo to page: status={resp.status_code}, body={data}"
        )
    return data["id"]


def _upload_local_photo_to_facebook_page(
    page_id: str, image_path: str, page_access_token: str
) -> str:
    """
    Upload a local image file to the page as an unpublished photo, returning the media ID.
    """
    # DISABLING FACEBOOK - Temporarily disabled due to posting issues
    # raise RuntimeError("Facebook posting is temporarily disabled")

    post_url = f"https://graph.facebook.com/v22.0/{page_id}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        data = {"access_token": page_access_token, "published": False}
        resp = requests.post(post_url, files=files, data=data)
    data = resp.json()
    if resp.status_code != 200 or "id" not in data:
        raise RuntimeError(
            f"Failed to upload local photo to page: status={resp.status_code}, body={data}"
        )
    return data["id"]


def post_to_facebook_page(
    page_id: str,
    message: str,
    image_urls: List[str],
    user_access_token: Optional[str] = None,
    page_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Post a message with one or more images to a Facebook Page.

    DEPRECATED: This function is deprecated. Please use SocialPostingService.post_to_account()
    or SocialPostingService.post_to_platform_accounts() with database-stored credentials instead.

    - If page_access_token is not provided, user_access_token must be provided and will be
      exchanged for a page access token via get_page_access_token.
    - Images are uploaded first as unpublished photos; then a feed post is created with
      attached_media.
    """
    # DISABLING FACEBOOK - Temporarily disabled due to posting issues
    # logger.warning("Facebook posting is temporarily disabled")
    # return {"success": False, "error": "Facebook posting is temporarily disabled"}

    warnings.warn(
        "post_to_facebook_page() is deprecated. Use SocialPostingService.post_to_account() "
        "or SocialPostingService.post_to_platform_accounts() with database-stored credentials instead.",
        DeprecationWarning,
        stacklevel=2
    )
    if not page_access_token:
        # TEMPORARY: Use user_access_token directly as page_access_token
        # Skip fetching page details from Facebook API
        if not user_access_token:
            raise ValueError(
                "Either page_access_token or user_access_token must be provided"
            )
        logger.info("TEMPORARY: Using user_access_token directly as page_access_token, skipping page details fetch")
        page_access_token = user_access_token
        # Commented out the page details fetching:
        # page_details = get_page_access_token(page_id, user_access_token)
        # page_access_token = page_details["page_access_token"]

    try:
        media_ids: List[str] = []
        for url in image_urls:
            if url.startswith("/static"):
                url = url.replace("/static", "static")
            if url.startswith("/media"):
                url = url.replace("/media", "media")
            try:
                # Support local file paths as well as remote URLs
                if url.startswith("http://") or url.startswith("https://"):
                    media_id = _post_image_to_facebook_page(
                        page_id, url, page_access_token
                    )
                elif os.path.exists(url):
                    media_id = _upload_local_photo_to_facebook_page(
                        page_id, url, page_access_token
                    )
                else:
                    media_id = _post_image_to_facebook_page(
                        page_id, url, page_access_token
                    )
                media_ids.append(media_id)
            except Exception as e:
                logger.warning(f"Skipping image due to upload error: {e}")

        # if not media_ids:
        #     return {"success": False, "error": "No images could be uploaded"}

        feed_url = f"https://graph.facebook.com/v22.0/{page_id}/feed"
        feed_data: Dict[str, Any] = {
            "message": message if message else "SmartPost",
            "access_token": page_access_token,
        }
        for idx, media_id in enumerate(media_ids):
            feed_data[f"attached_media[{idx}]"] = f'{{"media_fbid":"{media_id}"}}'

        feed_resp = requests.post(feed_url, data=feed_data)
        feed_json = feed_resp.json()
        if feed_resp.status_code == 200 and feed_json.get("id"):
            return {"success": True, "id": feed_json.get("id"), "raw": feed_json}
        return {"success": False, "error": feed_json}
    except Exception as e:
        logger.exception("Error posting to Facebook page")
        return {"success": False, "error": str(e)}


def post_to_whatsapp_group(
    group_id: str,
    message: str,
    image_url: Optional[str] = None,
    *,
    api_key: Optional[str] = None,
    sender_phone: Optional[str] = "+918189900456",
) -> Dict[str, Any]:
    """
    Post a message (and optional media: image/video) to a WhatsApp group using Periskope API.

    DEPRECATED: This function is deprecated. Please use SocialPostingService.post_to_account()
    or SocialPostingService.post_to_platform_accounts() with database-stored credentials instead.

    Supports images (.jpg, .png, .gif, .webp) and videos (.mp4, .mov, .avi, .mkv, .webm).
    Media can be a local file path or remote URL.

    Required env vars if not passed explicitly:
      - PERISKOPE_API_KEY
      - WHATSAPP_SENDER_PHONE (E.164 format), or falls back to x-phone from sample
    """
    warnings.warn(
        "post_to_whatsapp_group() is deprecated. Use SocialPostingService.post_to_account() "
        "or SocialPostingService.post_to_platform_accounts() with database-stored credentials instead.",
        DeprecationWarning,
        stacklevel=2
    )
    periskope_api_key = api_key or os.getenv("PERISKOPE_API_KEY")
    if not periskope_api_key:
        return {"success": False, "error": "PERISKOPE_API_KEY not configured"}

    sender = (
        sender_phone
        or os.getenv("WHATSAPP_SENDER_PHONE")
        or os.getenv("PERISKOPE_X_PHONE")
    )
    if not sender:
        # keep parity with sample which used a hard-coded x-phone; require explicit config here
        return {"success": False, "error": "WHATSAPP sender phone not configured"}

    url = "https://api.periskope.app/v1/message/send"
    headers = {
        "Authorization": f"Bearer {periskope_api_key}",
        "Content-Type": "application/json",
        "x-phone": sender,
    }
    payload: Dict[str, Any] = {"chat_id": group_id, "message": message}  # message,
    if image_url:
        if image_url.startswith("/static"):
            image_url = image_url.replace("/static", "static")
        if image_url.startswith("/media"):
            image_url = image_url.replace("/media", "media")

    if image_url:
        # Determine media type (image, video, or document) and appropriate MIME type
        media_type, mimetype, filename = _get_media_type_and_mimetype(image_url)
        
        # Check if it's a local file path
        if os.path.exists(image_url):
            try:
                with open(image_url, "rb") as media_file:
                    base64_media = base64.b64encode(media_file.read()).decode("utf-8")
                payload["media"] = {
                    "type": media_type,
                    "filename": filename,
                    "mimetype": mimetype,
                    "filedata": base64_media,
                }
            except Exception as e:
                logger.error(f"Failed to read local media file {image_url}: {e}")
                return {"success": False, "error": f"Failed to read media file: {str(e)}"}
        else:
            payload["media"] = {
                "type": media_type,
                "filename": filename,
                "mimetype": mimetype,
                "url": image_url,
            }

    resp = requests.post(url, headers=headers, json=payload)
    try:
        data = resp.json()
    except ValueError:
        data = {"status": resp.status_code, "text": resp.text}

    if resp.status_code == 200:
        return {"success": True, **(data if isinstance(data, dict) else {"raw": data})}
    return {"success": False, "error": data}


def get_all_accounts(user_access_token: str) -> Dict[str, Dict[str, str]]:

    try:
        url = f"https://graph.facebook.com/v22.0/me/accounts?access_token={user_access_token}"
        response = requests.get(url)
        accounts = response.json()

        if accounts.get("paging", {}).get("cursors", {}).get("after"):
            while True:
                url = f"https://graph.facebook.com/v22.0/me/accounts?access_token={user_access_token}&after={accounts.get('paging', {}).get('cursors', {}).get('after')}"
                response = requests.get(url)
                response_data = response.json()
                if response_data.get("paging", {}).get("cursors", {}).get("after"):
                    accounts["data"].extend(response_data.get("data", []))
                else:
                    break

        account_list = {}
        for acc in accounts.get("data"):
            account_list[acc["name"]] = {
                "name": acc["name"],
                "id": acc["id"],
                "access_token": acc["access_token"],
            }

        return account_list
    except Exception as e:
        logger.exception(f"FBERROR: Failed to get accounts: {e}")
        raise


if __name__ == "__main__":
    user_access_token = os.getenv("FB_LONG_LIVED_TOKEN") or os.getenv(
        "FACEBOOK_ACCESS_TOKEN", ""
    )
    fb_result = post_to_facebook_page(
        page_id="61579232464240",
        message="Hello from Omnipush!",
        image_urls=["/static/screenshots/screenshot_20250811_212614_053.png"],
        user_access_token=user_access_token,  # or pass page_access_token=...
    )
    # print(get_page_access_token("61579232464240", user_access_token))
    
    # Test video media type detection
    print("Testing media type detection:")
    print(_get_media_type_and_mimetype("test.mp4"))  # Should return ('video', 'video/mp4', 'test.mp4')
    print(_get_media_type_and_mimetype("test.jpg"))  # Should return ('image', 'image/jpeg', 'test.jpg')
    print(_get_media_type_and_mimetype("https://example.com/video.mov"))  # Should return ('video', 'video/quicktime', 'video.mov')


"""


# Facebook
fb_result = post_to_facebook_page(
    page_id="YOUR_PAGE_ID",
    message="Hello from Omnipush!",
    image_urls=["https://example.com/image.jpg"],
    user_access_token="USER_LONG_LIVED_TOKEN"  # or pass page_access_token=...
)

# WhatsApp
wa_result = post_to_whatsapp_group(
    group_id="WHATSAPP_GROUP_ID",
    message="Hello group!",
    image_url="https://example.com/image.jpg"
)
"""
