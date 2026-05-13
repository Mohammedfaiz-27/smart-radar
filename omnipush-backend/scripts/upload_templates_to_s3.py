#!/usr/bin/env python3
"""
Template S3 Upload Script
========================

This script uploads all newscard templates from the local templates directory
to S3 and updates the newscard_templates table with S3 URLs.

Usage:
    uv run python scripts/upload_templates_to_s3.py

Requirements:
    - AWS credentials configured (AWS CLI, environment variables, or IAM role)
    - S3 bucket access
    - Database connection to update template URLs
"""

import os
import sys
import boto3
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import mimetypes

# Add parent directory to path to import from omnipush modules
sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings
from core.database import get_database
from services.newscard_template_service import NewscardTemplateService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TemplateS3Uploader:
    """Service for uploading templates to S3 and updating database"""

    def __init__(self, bucket_name: str, s3_prefix: str = "templates/newscard"):
        self.bucket_name = bucket_name
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
        self.db = get_database()

        # Template directories
        self.template_base_dir = Path(__file__).parent.parent / "templates"
        self.newscard_dir = self.template_base_dir / "newscard"
        self.newscard_nue_dir = self.template_base_dir / "newscard_nue"

        # Track upload results
        self.upload_results = []

    def get_all_template_files(self) -> List[Dict[str, str]]:
        """Get all template files with their metadata"""
        templates = []

        # Process newscard directory
        if self.newscard_dir.exists():
            templates.extend(self._process_directory(
                self.newscard_dir,
                "newscard",
                supports_images_default=False
            ))

        # Process newscard_nue directory
        if self.newscard_nue_dir.exists():
            templates.extend(self._process_directory(
                self.newscard_nue_dir,
                "newscard_nue",
                supports_images_default=None  # Will be determined by subdirectory
            ))

        logger.info(f"Found {len(templates)} template files to process")
        return templates

    def _process_directory(self, base_dir: Path, prefix: str, supports_images_default: Optional[bool]) -> List[Dict[str, str]]:
        """Process templates in a directory structure"""
        templates = []

        # Direct HTML files in root (newscard only)
        if supports_images_default is not None:
            for template_file in base_dir.glob("template_*.html"):
                templates.append(self._create_template_info(
                    template_file, prefix, supports_images_default
                ))

        # Process with_images subdirectory
        with_images_dir = base_dir / "with_images"
        if with_images_dir.exists():
            for template_file in with_images_dir.glob("*.html"):
                templates.append(self._create_template_info(
                    template_file, prefix, True, subdirectory="with_images"
                ))

        # Process without_images subdirectory
        without_images_dir = base_dir / "without_images"
        if without_images_dir.exists():
            for template_file in without_images_dir.glob("*.html"):
                templates.append(self._create_template_info(
                    template_file, prefix, False, subdirectory="without_images"
                ))

        return templates

    def _create_template_info(self, file_path: Path, prefix: str, supports_images: bool, subdirectory: str = None) -> Dict[str, str]:
        """Create template info dictionary"""

        # Generate template name based on current service logic
        if subdirectory:
            if subdirectory == "with_images":
                template_name = f"{prefix}_{file_path.stem}_with_image"
            else:  # without_images
                template_name = f"{prefix}_{file_path.stem}_without_image"
        else:
            template_name = f"{prefix}_{file_path.stem}"

        # Generate S3 key
        if subdirectory:
            s3_key = f"{self.s3_prefix}/{prefix}/{subdirectory}/{file_path.name}"
        else:
            s3_key = f"{self.s3_prefix}/{prefix}/{file_path.name}"

        # Generate display name
        display_name = file_path.stem.replace('_', ' ').replace('template ', '').title()
        if subdirectory == "with_images":
            display_name += " (With Images)"
        elif subdirectory == "without_images":
            display_name += " (Text Only)"

        return {
            'file_path': str(file_path),
            'template_name': template_name,
            'display_name': display_name,
            's3_key': s3_key,
            'supports_images': supports_images,
            'local_path': str(file_path.relative_to(self.template_base_dir))
        }

    def upload_file_to_s3(self, local_path: str, s3_key: str) -> str:
        """Upload a file to S3 and return the S3 URL"""
        try:
            # Determine content type
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'text/html'

            # Upload file
            with open(local_path, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'CacheControl': 'max-age=31536000',  # 1 year cache
                    }
                )

            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            logger.info(f"Uploaded {local_path} to {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {str(e)}")
            raise

    async def update_template_in_database(self, template_info: Dict[str, str], s3_url: str):
        """Update or insert template information in database"""
        try:
            template_data = {
                'template_name': template_info['template_name'],
                'template_display_name': template_info['display_name'],
                'template_path': template_info['local_path'],  # Keep local path for fallback
                's3_url': s3_url,
                's3_bucket': self.bucket_name,
                's3_key': template_info['s3_key'],
                'supports_images': template_info['supports_images'],
                'description': f"Template uploaded from {template_info['local_path']}",
                'is_active': True,
                'updated_at': datetime.utcnow().isoformat()
            }

            # Try to update existing record first
            existing = self.db.client.table('newscard_templates')\
                .select('id')\
                .eq('template_name', template_info['template_name'])\
                .execute()

            if existing.data:
                # Update existing record
                result = self.db.client.table('newscard_templates')\
                    .update(template_data)\
                    .eq('template_name', template_info['template_name'])\
                    .execute()
                logger.info(f"Updated existing template: {template_info['template_name']}")
            else:
                # Insert new record
                result = self.db.client.table('newscard_templates')\
                    .insert(template_data)\
                    .execute()
                logger.info(f"Inserted new template: {template_info['template_name']}")

            return True

        except Exception as e:
            logger.error(f"Failed to update database for {template_info['template_name']}: {str(e)}")
            return False

    async def upload_all_templates(self, dry_run: bool = False) -> Dict[str, int]:
        """Upload all templates to S3 and update database"""
        templates = self.get_all_template_files()

        stats = {
            'total': len(templates),
            'uploaded': 0,
            'failed': 0,
            'db_updated': 0,
            'db_failed': 0
        }

        logger.info(f"Starting upload of {stats['total']} templates (dry_run={dry_run})")

        for template_info in templates:
            try:
                logger.info(f"Processing: {template_info['template_name']}")

                if not dry_run:
                    # Upload to S3
                    s3_url = self.upload_file_to_s3(
                        template_info['file_path'],
                        template_info['s3_key']
                    )
                    stats['uploaded'] += 1

                    # Update database
                    if await self.update_template_in_database(template_info, s3_url):
                        stats['db_updated'] += 1
                    else:
                        stats['db_failed'] += 1

                    self.upload_results.append({
                        'template_name': template_info['template_name'],
                        'status': 'success',
                        's3_url': s3_url,
                        'local_path': template_info['file_path']
                    })
                else:
                    logger.info(f"DRY RUN: Would upload {template_info['file_path']} to {template_info['s3_key']}")

            except Exception as e:
                stats['failed'] += 1
                logger.error(f"Failed to process {template_info['template_name']}: {str(e)}")
                self.upload_results.append({
                    'template_name': template_info['template_name'],
                    'status': 'failed',
                    'error': str(e),
                    'local_path': template_info['file_path']
                })

        return stats

    def print_upload_summary(self, stats: Dict[str, int]):
        """Print a summary of upload results"""
        print("\n" + "="*60)
        print("TEMPLATE UPLOAD SUMMARY")
        print("="*60)
        print(f"Total templates processed: {stats['total']}")
        print(f"Successfully uploaded: {stats['uploaded']}")
        print(f"Upload failures: {stats['failed']}")
        print(f"Database updates: {stats['db_updated']}")
        print(f"Database failures: {stats['db_failed']}")
        print("="*60)

        # Print failed uploads if any
        failed_results = [r for r in self.upload_results if r['status'] == 'failed']
        if failed_results:
            print("\nFAILED UPLOADS:")
            for result in failed_results:
                print(f"- {result['template_name']}: {result.get('error', 'Unknown error')}")

        # Print successful uploads
        success_results = [r for r in self.upload_results if r['status'] == 'success']
        if success_results:
            print(f"\nSUCCESSFUL UPLOADS ({len(success_results)}):")
            for result in success_results[:5]:  # Show first 5
                print(f"- {result['template_name']}")
            if len(success_results) > 5:
                print(f"... and {len(success_results) - 5} more")

async def main():
    """Main script entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Upload newscard templates to S3')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--prefix', default='templates/newscard', help='S3 key prefix')
    parser.add_argument('--dry-run', action='store_true', help='Preview uploads without executing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize uploader
    uploader = TemplateS3Uploader(
        bucket_name=args.bucket,
        s3_prefix=args.prefix
    )

    try:
        # Run upload process
        stats = await uploader.upload_all_templates(dry_run=args.dry_run)

        # Print summary
        uploader.print_upload_summary(stats)

        if args.dry_run:
            print("\n🚀 Ready to upload! Run without --dry-run to execute.")
        else:
            print(f"\n✅ Upload complete! {stats['uploaded']}/{stats['total']} templates uploaded successfully.")

    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())