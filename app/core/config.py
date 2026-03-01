"""Configuration management for KaiTian application."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "KaiTian"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Database (SQLite)
    database_url: str = "sqlite:///./kaitian.db"
    database_echo: bool = False

    # Crawl4AI Configuration (API-based)
    crawl4ai_enabled: bool = True
    crawl4ai_api_url: Optional[str] = None  # Defaults to http://localhost:8001
    crawl4ai_timeout: int = 30

    # Search Configuration
    search_keywords: str = "python,programming,automation"
    subreddit_list: str = "python,learnprogramming,programming"
    search_interval_minutes: int = 30
    max_posts_per_search: int = 10

    # Processing
    relevance_threshold: float = 0.7
    max_concurrent_requests: int = 5
    request_timeout_seconds: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def keywords(self) -> list[str]:
        """Parse search keywords from comma-separated string."""
        return [k.strip() for k in self.search_keywords.split(",") if k.strip()]

    @property
    def subreddits(self) -> list[str]:
        """Parse subreddit list from comma-separated string."""
        return [s.strip() for s in self.subreddit_list.split(",") if s.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
