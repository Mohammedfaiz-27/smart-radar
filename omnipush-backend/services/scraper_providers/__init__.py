"""
Scraper Provider Abstractions

Provides clean separation between keyword-based and account-based scraping.
"""

from services.scraper_providers.base import BaseSocialScraperProvider
from services.scraper_providers.facebook_keyword_provider import FacebookKeywordProvider
from services.scraper_providers.facebook_account_provider import FacebookAccountProvider
from services.scraper_providers.twitter_keyword_provider import TwitterKeywordProvider
from services.scraper_providers.twitter_account_provider import TwitterAccountProvider
from services.scraper_providers.instagram_account_provider import InstagramAccountProvider

__all__ = [
    'BaseSocialScraperProvider',
    'FacebookKeywordProvider',
    'FacebookAccountProvider',
    'TwitterKeywordProvider',
    'TwitterAccountProvider',
    'InstagramAccountProvider',
]
