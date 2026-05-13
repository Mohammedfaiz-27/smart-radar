"""
Base Provider Interface for Social Media Scraping

Defines the contract that all scraper providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any


class BaseSocialScraperProvider(ABC):
    """
    Base interface for social media scraper providers.

    All scraper providers (keyword-based and account-based) must implement this interface.
    """

    @abstractmethod
    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch posts from the social media platform.

        Args:
            **kwargs: Provider-specific parameters
                - For keyword providers: query, max_items, date_range_days
                - For account providers: account_id, account_identifier, max_items, date_range_days

        Returns:
            Tuple of (success: bool, posts: List[Dict])
                - success: Whether the fetch operation succeeded
                - posts: List of normalized post dictionaries with keys:
                    - id: str (unique post ID)
                    - content: str (post text/message)
                    - url: str (post URL)
                    - author_id: str (account ID)
                    - author_name: str (account name)
                    - created_time: Optional[datetime]
                    - hashtags: List[str]
                    - reactions: int
                    - shares: int
                    - comments: int
                    - media_url: Optional[str] (image/video URL)
        """
        pass

    @abstractmethod
    def get_platform(self) -> str:
        """
        Get the platform name for this provider.

        Returns:
            Platform name (e.g., 'facebook', 'twitter')
        """
        pass

    def get_scraping_mode(self) -> str:
        """
        Get the scraping mode for this provider.

        Returns:
            Scraping mode ('keyword' or 'account')
        """
        # Default implementation - subclasses can override
        return getattr(self, 'scraping_mode', 'keyword')
