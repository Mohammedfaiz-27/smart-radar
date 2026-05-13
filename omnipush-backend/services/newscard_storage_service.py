import os
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class NewscardStorageService:
    """Service for managing local storage and caching of generated news cards"""
    
    def __init__(self):
        self.storage_dir = Path(__file__).parent.parent / "static" / "generated-newscards"
        self.metadata_file = self.storage_dir / "newscard_metadata.json"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load newscard metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _generate_content_hash(self, content: str, channel_name: str, template_name: str) -> str:
        """Generate a hash for content to avoid duplicates"""
        content_string = f"{content}_{channel_name}_{template_name}"
        return hashlib.md5(content_string.encode()).hexdigest()[:12]
    
    def store_newscard(
        self, 
        html_content: str, 
        content: str,
        tenant_id: str,
        channel_name: str = "News Channel",
        template_name: str = "unknown",
        category: str = "News"
    ) -> Dict[str, str]:
        """Store generated newscard locally with metadata"""
        
        # Generate content hash for deduplication
        content_hash = self._generate_content_hash(content, channel_name, template_name)
        
        # Create filename with timestamp and hash
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"newscard_{timestamp}_{content_hash}.html"
        
        # Create tenant-specific directory
        tenant_dir = self.storage_dir / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        
        # Full file path
        file_path = tenant_dir / filename
        
        # Check if similar content already exists (avoid duplicates)
        if content_hash in self.metadata:
            existing_entry = self.metadata[content_hash]
            existing_path = Path(existing_entry['local_path'])
            if existing_path.exists():
                logger.info(f"Similar newscard already exists: {existing_entry['local_path']}")
                return {
                    'local_path': str(existing_path),
                    'url': f"/static/generated-newscards/{existing_entry['relative_path']}",
                    'filename': existing_path.name,
                    'cached': True,
                    'hash': content_hash
                }
        
        try:
            # Save HTML file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Calculate relative path for URL
            relative_path = f"{tenant_id}/{filename}"
            
            # Store metadata
            metadata_entry = {
                'content_hash': content_hash,
                'local_path': str(file_path),
                'relative_path': relative_path,
                'filename': filename,
                'tenant_id': tenant_id,
                'channel_name': channel_name,
                'template_name': template_name,
                'category': category,
                'content_preview': content[:100] + '...' if len(content) > 100 else content,
                'created_at': datetime.now().isoformat(),
                'file_size': len(html_content)
            }
            
            self.metadata[content_hash] = metadata_entry
            self._save_metadata()
            
            logger.info(f"Newscard stored locally: {file_path}")
            
            return {
                'local_path': str(file_path),
                'url': f"/static/generated-newscards/{relative_path}",
                'filename': filename,
                'cached': False,
                'hash': content_hash
            }
            
        except Exception as e:
            logger.error(f"Error storing newscard: {e}")
            raise Exception(f"Failed to store newscard: {e}")
    
    def get_newscard_by_hash(self, content_hash: str) -> Optional[Dict]:
        """Get newscard metadata by content hash"""
        return self.metadata.get(content_hash)
    
    def list_newscards_by_tenant(self, tenant_id: str) -> List[Dict]:
        """List all newscards for a specific tenant"""
        tenant_newscards = []
        for hash_key, metadata in self.metadata.items():
            if metadata.get('tenant_id') == tenant_id:
                # Check if file still exists
                if Path(metadata['local_path']).exists():
                    tenant_newscards.append(metadata)
                else:
                    # Clean up metadata for missing files
                    logger.warning(f"Newscard file missing, cleaning metadata: {metadata['local_path']}")
        
        # Sort by creation date (newest first)
        tenant_newscards.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return tenant_newscards
    
    def cleanup_old_newscards(self, max_age_days: int = 30):
        """Clean up newscards older than specified days"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        to_remove = []
        for hash_key, metadata in self.metadata.items():
            try:
                created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                if created_at < cutoff_date:
                    # Remove file
                    file_path = Path(metadata['local_path'])
                    if file_path.exists():
                        file_path.unlink()
                    to_remove.append(hash_key)
                    cleaned_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up newscard {hash_key}: {e}")
        
        # Remove from metadata
        for hash_key in to_remove:
            del self.metadata[hash_key]
        
        if cleaned_count > 0:
            self._save_metadata()
            logger.info(f"Cleaned up {cleaned_count} old newscards")
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        total_files = len(self.metadata)
        total_size = sum(metadata.get('file_size', 0) for metadata in self.metadata.values())
        
        # Count by tenant
        tenant_counts = {}
        template_usage = {}
        
        for metadata in self.metadata.values():
            tenant_id = metadata.get('tenant_id', 'unknown')
            template_name = metadata.get('template_name', 'unknown')
            
            tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1
            template_usage[template_name] = template_usage.get(template_name, 0) + 1
        
        return {
            'total_newscards': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'tenant_counts': tenant_counts,
            'template_usage': template_usage,
            'storage_directory': str(self.storage_dir)
        }

# Global instance
newscard_storage_service = NewscardStorageService()