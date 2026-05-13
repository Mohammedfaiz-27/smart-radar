import os
import boto3
import mimetypes
import uuid
from typing import Optional, Dict, Any
import logging
import httpx
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 file uploads and management"""
    
    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY")
        self.aws_secret = os.getenv("AWS_SECRET")
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "omnipush-media")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Check if AWS credentials are available
        if not self.aws_access_key or not self.aws_secret:
            logger.warning("AWS credentials not found in environment variables. "
                          "S3 functionality will be disabled. "
                          "Set AWS_ACCESS_KEY and AWS_SECRET environment variables to enable S3.")
            self.s3_client = None
            return
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret,
                region_name=self.region
            )
            
            # Try to ensure bucket exists - if creation fails, continue anyway
            self._ensure_bucket_exists()
        except Exception as e:
            logger.warning(f"Could not initialize S3 client: {e}. S3 functionality will be disabled.")
            self.s3_client = None
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket {self.bucket_name} exists and is accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, try to create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.warning(f"Failed to create bucket {self.bucket_name}: {create_error}")
                    # Don't raise here, continue without bucket creation
            elif error_code == '403':
                # Permission denied - bucket might exist but we don't have access
                logger.warning(f"Permission denied accessing bucket {self.bucket_name}. "
                             f"This might be due to insufficient permissions or the bucket doesn't exist. "
                             f"Continuing without bucket verification.")
            else:
                logger.warning(f"Error accessing bucket {self.bucket_name}: {e}. Continuing anyway.")
    
    def generate_file_key(self, tenant_id: str, filename: str, media_type: str = "media") -> str:
        """Generate consistent S3 key for files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Extract file extension
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = ""

        # Create consistent naming: tenants/{tenant_id}/{media_type}/{timestamp}_{unique_id}{ext}
        key = f"tenants/{tenant_id}/{media_type}/{timestamp}_{unique_id}{ext}"
        return key

    def _sanitize_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Sanitize metadata values to ensure they only contain ASCII characters"""
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                continue
            # Encode to ASCII, replacing non-ASCII chars with '?', then decode back to string
            ascii_value = value.encode('ascii', errors='replace').decode('ascii')
            sanitized[key] = ascii_value
        return sanitized
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        tenant_id: str,
        media_type: str = "media",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Upload file to S3 and return URLs"""
        try:
            # Generate S3 key
            s3_key = self.generate_file_key(tenant_id, filename, media_type)

            # Determine content type
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = 'application/octet-stream'

            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'Body': file_content,
                'ContentType': content_type
            }

            # Add metadata if provided - sanitize to ASCII only
            if metadata:
                upload_params['Metadata'] = self._sanitize_metadata(metadata)
            
            # Upload file
            self.s3_client.put_object(**upload_params)
            
            # Generate URLs
            file_url = self._get_file_url(s3_key)
            
            return {
                'url': file_url,
                'key': s3_key,
                'filename': filename,
                'content_type': content_type,
                'size': len(file_content)
            }
            
        except NoCredentialsError:
            logger.exception("AWS credentials not found")
            raise ValueError("AWS credentials not configured")
        except ClientError as e:
            logger.exception(f"S3 upload failed: {e}")
            raise RuntimeError(f"File upload failed: {e}")
    
    def _get_file_url(self, s3_key: str) -> str:
        """Generate public URL for S3 object"""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            logger.exception(f"Failed to delete file {s3_key}: {e}")
            return False
    
    async def upload_screenshot(
        self, 
        file_content: bytes, 
        filename: str, 
        tenant_id: str
    ) -> Dict[str, str]:
        """Upload screenshot to S3"""
        return await self.upload_file(
            file_content, 
            filename, 
            tenant_id, 
            media_type="screenshots"
        )
    
    async def upload_newscard(
        self, 
        file_content: bytes, 
        filename: str, 
        tenant_id: str
    ) -> Dict[str, str]:
        """Upload newscard to S3"""
        return await self.upload_file(
            file_content, 
            filename, 
            tenant_id, 
            media_type="newscards"
        )
    
    async def upload_video(
        self, 
        file_content: bytes, 
        filename: str, 
        tenant_id: str
    ) -> Dict[str, str]:
        """Upload video to S3"""
        return await self.upload_file(
            file_content, 
            filename, 
            tenant_id, 
            media_type="videos"
        )
    
    async def download_and_upload_image(
        self,
        image_url: str,
        filename: str,
        tenant_id: str,
        media_type: str = "ai-generated"
    ) -> Dict[str, str]:
        """Download image from URL and upload to S3"""
        try:
            # Download the image
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_content = response.content

            # Upload to S3
            return await self.upload_file(
                image_content,
                filename,
                tenant_id,
                media_type
            )

        except httpx.HTTPError as e:
            logger.exception(f"Failed to download image from {image_url}: {e}")
            raise ValueError(f"Failed to download image: {e}")
        except Exception as e:
            logger.exception(f"Failed to process image upload: {e}")
            raise RuntimeError(f"Image processing failed: {e}")

    async def upload_external_news_image(
        self,
        image_url: str,
        tenant_id: str,
        external_source: str = "slack",
        external_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Download image from external source URL and upload to S3 in appropriate folder

        Args:
            image_url: Source URL of the image
            tenant_id: Tenant ID
            external_source: Source type (slack, twitter, facebook, etc.)
            external_id: Optional external ID for filename

        Returns:
            Dictionary with S3 URL and key, or None if upload fails
        """
        if not self.s3_client:
            logger.warning("S3 client not available, returning original URL")
            return None

        try:
            # Download the image
            logger.info(f"Downloading image from {external_source}: {image_url}")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_content = response.content

            # Determine file extension from content-type or URL
            content_type = response.headers.get('content-type', '')
            ext = mimetypes.guess_extension(content_type.split(';')[0]) if content_type else None

            if not ext:
                # Try to get extension from URL
                url_path = image_url.split('?')[0]  # Remove query params
                _, url_ext = os.path.splitext(url_path)
                ext = url_ext if url_ext else '.jpg'

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{external_id or unique_id}_{timestamp}{ext}"

            # Upload to S3 with source-specific folder structure
            # Path: tenants/{tenant_id}/external-news/{source}/filename
            media_type = f"external-news/{external_source}"

            result = await self.upload_file(
                image_content,
                filename,
                tenant_id,
                media_type
            )

            logger.info(f"Successfully uploaded {external_source} image to S3: {result['url']}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload {external_source} image to S3: {e}")
            return None
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for temporary access"""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.exception(f"Failed to generate presigned URL: {e}")
            raise


# Global instance - lazy initialization
_s3_service = None


class S3ServiceProxy:
    """Proxy class for lazy initialization of S3Service"""
    
    def __init__(self):
        self._service = None
    
    def __getattr__(self, name):
        if self._service is None:
            self._service = S3Service()
        return getattr(self._service, name)


# Global instance
s3_service = S3ServiceProxy()