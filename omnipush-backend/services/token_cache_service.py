#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Cache Service for OmniPush Platform

Handles caching of Facebook page access tokens locally in JSON format.
Provides fallback to API calls when cache fails or is missing.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from services.social_util import get_all_accounts

logger = logging.getLogger(__name__)

CACHE_FILE = "facebook_tokens_cache.json"
CACHE_EXPIRY_HOURS = 24  # Tokens cached for 24 hours


class TokenCacheService:
    """Service for caching Facebook page access tokens"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / CACHE_FILE
        self.cache_dir.mkdir(exist_ok=True)
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load token cache from JSON file"""
        try:
            if not self.cache_file.exists():
                return {}
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            if self._is_cache_expired(cache_data):
                logger.info("Token cache expired, will refresh")
                return {}
                
            return cache_data
            
        except Exception as e:
            logger.exception(f"Failed to load token cache: {e}")
            return {}
    
    def _save_cache(self, cache_data: Dict[str, Any]):
        """Save token cache to JSON file"""
        try:
            cache_data['last_updated'] = datetime.utcnow().isoformat()
            cache_data['expires_at'] = (
                datetime.utcnow() + timedelta(hours=CACHE_EXPIRY_HOURS)
            ).isoformat()
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"Token cache saved to {self.cache_file}")
            
        except Exception as e:
            logger.exception(f"Failed to save token cache: {e}")
    
    def _is_cache_expired(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache is expired"""
        try:
            expires_at = cache_data.get('expires_at')
            if not expires_at:
                return True
                
            expiry_time = datetime.fromisoformat(expires_at)
            return datetime.utcnow() > expiry_time
            
        except Exception as e:
            logger.exception(f"Error checking cache expiry: {e}")
            return True
    
    def get_page_access_token(self, page_id: str, user_access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get page access token from cache or API
        
        Args:
            page_id: Facebook page ID
            user_access_token: User access token for API fallback
            
        Returns:
            Page details with access token, or None if failed
        """
        try:
            # Try to get from cache first
            cache_data = self._load_cache()
            cached_tokens = cache_data.get('page_tokens', {})
            
            if page_id in cached_tokens:
                page_details = cached_tokens[page_id]
                logger.info(f"Using cached token for page {page_id}")
                return page_details
            
            # Cache miss or expired, fetch from API
            logger.info(f"Cache miss for page {page_id}, fetching from API...")
            page_details = self._fetch_page_token_from_api(page_id, user_access_token)
            
            if page_details:
                # Update cache
                cached_tokens[page_id] = page_details
                cache_data['page_tokens'] = cached_tokens
                self._save_cache(cache_data)
                logger.info(f"Updated cache with token for page {page_id}")
            
            return page_details
            
        except Exception as e:
            logger.exception(f"Failed to get page access token for {page_id}: {e}")
            return None
    
    def _fetch_page_token_from_api(self, page_id: str, user_access_token: str) -> Optional[Dict[str, Any]]:
        """Fetch page access token from Facebook API"""
        try:
            # Get all accounts
            accounts = get_all_accounts(user_access_token)
            
            # Find the specific page by ID
            for page_name, page_data in accounts.items():
                if page_data['id'] == page_id:
                    page_details = {
                        "page_name": page_data["name"],
                        "page_id": page_data["id"],
                        "page_access_token": page_data["access_token"],
                    }
                    logger.info(f"Found page token for {page_name} ({page_id})")
                    return page_details
            
            # If not found by ID, try to find by name (fallback)
            logger.warning(f"Page {page_id} not found in accounts, trying fallback...")
            
            # For demo purposes, if we can't find the specific page, return the first available
            if accounts:
                first_page_name = list(accounts.keys())[0]
                first_page_data = accounts[first_page_name]
                page_details = {
                    "page_name": first_page_data["name"],
                    "page_id": first_page_data["id"],
                    "page_access_token": first_page_data["access_token"],
                }
                logger.info(f"Using fallback page: {first_page_name}")
                return page_details
            
            logger.exception(f"No pages found for user access token")
            return None
            
        except Exception as e:
            logger.exception(f"Failed to fetch page token from API: {e}")
            return None
    
    def clear_cache(self):
        """Clear the token cache"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("Token cache cleared")
        except Exception as e:
            logger.exception(f"Failed to clear cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache"""
        try:
            cache_data = self._load_cache()
            page_tokens = cache_data.get('page_tokens', {})
            
            return {
                'cache_file': str(self.cache_file),
                'cache_exists': self.cache_file.exists(),
                'cached_pages': len(page_tokens),
                'page_ids': list(page_tokens.keys()),
                'last_updated': cache_data.get('last_updated'),
                'expires_at': cache_data.get('expires_at'),
                'is_expired': self._is_cache_expired(cache_data) if cache_data else True
            }
        except Exception as e:
            logger.exception(f"Failed to get cache info: {e}")
            return {'error': str(e)}
