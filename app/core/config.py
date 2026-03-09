"""Configuration management for KaiTian application."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ====================
    # Application
    # ====================
    app_name: str = "KaiTian"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # ====================
    # Playwright Browser Configuration (System-wide)
    # ====================
    # 是否使用无头模式（默认False，使用有界面模式更容易通过反爬检测）
    playwright_headless: bool = False

    # 是否使用CDP模式（默认False，使用真实Chrome浏览器，反检测效果更好）
    # 注意: CDP模式需要系统没有运行中的Chrome实例
    playwright_cdp_mode: bool = True

    # CDP端口（默认9222）
    playwright_cdp_port: int = 9222

    # Cookie 持久化目录
    cookie_dir: str = "data/platform_sessions"

    # 浏览器数据目录
    browser_data_dir: str = "data/browser_data"

    # 默认登录超时时间（秒）
    login_timeout: int = 300

    # 默认页面操作超时时间（毫秒）
    playwright_timeout: int = 60000

    # ====================
    # Database
    # ====================
    database_url: str = "sqlite:///./kaitian.db"

    # ====================
    # Crawl4AI Configuration
    # ====================
    crawl4ai_api_url: Optional[str] = None
    crawl4ai_timeout: int = 30

    # ====================
    # MediaCrawler Configuration
    # ====================
    mediacrawler_api_url: str = "http://localhost:8080"
    mediacrawler_timeout: int = 60
    mediacrawler_max_retries: int = 3
    mediacrawler_poll_interval: int = 2

    # ====================
    # AI / LLM Configuration
    # ====================
    # LLM 提供商: openai, azure, anthropic
    llm_provider: str = "openai"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7

    # Azure OpenAI
    azure_openai_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_deployment_name: Optional[str] = None

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # ====================
    # Social Media API Keys
    # ====================
    # Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_username: Optional[str] = None
    reddit_password: Optional[str] = None

    # Twitter/X
    twitter_consumer_key: Optional[str] = None
    twitter_consumer_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None

    # LinkedIn
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_person_urn: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
