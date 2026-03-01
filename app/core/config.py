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

    # LangChain & AI 配置
    # LLM 提供商选择: "openai", "azure", "anthropic", "ollama"
    llm_provider: str = "openai"

    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000

    # Azure OpenAI 配置
    azure_openai_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_deployment_name: Optional[str] = None
    azure_openai_api_version: str = "2024-02-15-preview"

    # Anthropic Claude 配置
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # 内容生成配置
    content_generation_max_tokens: int = 2000
    content_generation_temperature: float = 0.7
    content_generation_timeout: int = 30
    content_generation_cache_enabled: bool = False

    # Redis 配置（用于缓存）
    redis_enabled: bool = False
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 86400  # 24小时

    # API 限流配置
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60

    # LangChain 追踪配置
    langchain_tracing_enabled: bool = False
    langchain_api_key: Optional[str] = None

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
