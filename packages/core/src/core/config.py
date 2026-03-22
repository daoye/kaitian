"""
配置管理

提供基于 Pydantic Settings 的配置管理，支持多层级配置覆盖
"""

import os
from pathlib import Path
from typing import Any, Optional

import toml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    path: Path = Field(default=Path("./data/kaitian.db"), description="数据库路径")
    url: str = Field(default="sqlite:///kaitian.db", description="数据库连接URL")
    echo: bool = Field(default=False, description="是否输出数据库日志")

    @field_validator("path")
    @classmethod
    def resolve_database_path(cls, v: Path) -> Path:
        return v.expanduser().resolve()

    model_config = SettingsConfigDict(env_prefix="KAITIAN_DB_")


class BrowserConfig(BaseSettings):
    """浏览器配置"""

    headless: bool = Field(default=True, description="是否无头模式")
    timeout: int = Field(default=30000, description="默认超时时间（毫秒）")
    user_data_dir: Optional[Path] = Field(default=None, description="用户数据目录")
    proxy_server: Optional[str] = Field(default=None, description="浏览器代理地址")
    proxy_username: Optional[str] = Field(default=None, description="浏览器代理用户名")
    proxy_password: Optional[str] = Field(default=None, description="浏览器代理密码")
    proxy_bypass: Optional[str] = Field(default=None, description="浏览器代理绕过地址")
    enable_cdc: bool = Field(default=False, description="是否启用 CDC")
    cdp_port: Optional[int] = Field(default=None, description="CDP 端口")

    @field_validator("user_data_dir")
    @classmethod
    def resolve_user_data_dir(cls, v: Optional[Path]) -> Optional[Path]:
        """解析用户数据目录路径"""
        if v is None:
            return v
        return v.expanduser().resolve()

    model_config = SettingsConfigDict(env_prefix="KAITIAN_BROWSER_")


class StealthConfig(BaseSettings):
    """Stealth 配置"""

    enabled: bool = Field(default=False, description="是否启用 Stealth")

    model_config = SettingsConfigDict(env_prefix="KAITIAN_STEALTH_")


class DownloadConfig(BaseSettings):
    """下载配置"""

    temp_dir: Path = Field(default=Path("./temp"), description="临时文件目录")
    max_concurrent: int = Field(default=3, description="最大并发下载数")
    retry_count: int = Field(default=3, description="重试次数")
    chunk_size: int = Field(default=8192, description="下载块大小（字节）")
    output_dir: Path = Field(default=Path("./downloads"), description="下载输出目录")

    @field_validator("temp_dir")
    @classmethod
    def resolve_temp_dir(cls, v: Path) -> Path:
        """解析临时目录路径"""
        return v.expanduser().resolve()

    @field_validator("output_dir")
    @classmethod
    def resolve_output_dir(cls, v: Path) -> Path:
        return v.expanduser().resolve()

    @field_validator("chunk_size", mode="before")
    @classmethod
    def parse_chunk_size(cls, v: object) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            value = v.strip().upper()
            units = {"KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}
            for suffix, multiplier in units.items():
                if value.endswith(suffix):
                    amount = float(value[: -len(suffix)])
                    return int(amount * multiplier)
            return int(value)
        raise TypeError("invalid chunk_size")

    model_config = SettingsConfigDict(env_prefix="KAITIAN_DOWNLOAD_")


class LogConfig(BaseSettings):
    """日志配置"""

    level: str = Field(default="info", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式"
    )
    file: Optional[Path] = Field(default=None, description="日志文件路径")

    @field_validator("file")
    @classmethod
    def resolve_log_file(cls, v: Optional[Path]) -> Optional[Path]:
        """解析日志文件路径"""
        if v is None:
            return v
        return v.expanduser().resolve()

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.lower()

    model_config = SettingsConfigDict(env_prefix="KAITIAN_LOG_")


class SecurityConfig(BaseSettings):
    """安全配置"""

    encrypt_key: Optional[str] = Field(default=None, description="加密密钥")
    session_timeout: int = Field(default=3600, description="会话超时时间（秒）")

    model_config = SettingsConfigDict(env_prefix="KAITIAN_SECURITY_")


class CoreConfig(BaseSettings):
    """核心配置"""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    stealth: StealthConfig = Field(default_factory=StealthConfig)

    model_config = SettingsConfigDict(
        env_prefix="KAITIAN_",
        env_nested_delimiter="__",
    )


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: Optional[CoreConfig] = None
        self._config_file_paths = [
            Path("./kaitian.toml"),
            Path("./pyproject.toml"),
            Path("~/.config/kaitian/config.toml").expanduser(),
        ]

    def _load_toml_config(self, file_path: Path) -> dict[str, Any]:
        """从 TOML 文件加载配置"""
        if not file_path.exists():
            return {}
        try:
            data = toml.load(file_path)

            # 如果是 pyproject.toml，提取 [tool.kaitian] 部分
            if file_path.name == "pyproject.toml":
                return data.get("tool", {}).get("kaitian", {})

            # 普通 kaitian.toml 文件
            return data

        except Exception as e:
            print(f"Warning: Failed to load config from {file_path}: {e}")
            return {}

    def _normalize_legacy_config(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(config)
        database = dict(normalized.get("database", {}))
        if "path" in database and "url" not in database:
            database["url"] = f"sqlite:///{database['path']}"
        if database:
            normalized["database"] = database

        download = dict(normalized.get("download", {}))
        if "concurrent" in download and "max_concurrent" not in download:
            download["max_concurrent"] = download.pop("concurrent")
        if "retry_times" in download and "retry_count" not in download:
            download["retry_count"] = download.pop("retry_times")
        if download:
            normalized["download"] = download
        return normalized

    def _merge_configs(self, *configs: dict[str, Any]) -> dict[str, Any]:
        """合并多个配置字典"""
        result = {}
        for config in reversed(configs):  # 反向顺序，后面的覆盖前面的
            self._deep_merge(result, config)
        return result

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def load_config(self, config_file: Optional[Path] = None) -> CoreConfig:
        """加载配置

        配置优先级（从高到低）：
        1. 环境变量
        2. 指定的配置文件
        3. 本地 kaitian.toml
        4. pyproject.toml [tool.kaitian]
        5. 用户配置文件 ~/.config/kaitian/config.toml
        6. 默认配置
        """
        # 收集所有配置文件
        config_sources = []

        # 添加用户配置文件
        user_config = self._config_file_paths[2]
        if user_config.exists():
            config_sources.append(self._load_toml_config(user_config))

        # 添加 pyproject.toml
        pyproject_config = self._config_file_paths[1]
        if pyproject_config.exists():
            config_sources.append(self._load_toml_config(pyproject_config))

        # 添加本地 kaitian.toml
        local_config = self._config_file_paths[0]
        if local_config.exists():
            config_sources.append(self._load_toml_config(local_config))

        # 添加指定的配置文件
        if config_file and config_file.exists():
            config_sources.append(self._load_toml_config(config_file))

        # 合并配置
        merged_config = self._normalize_legacy_config(self._merge_configs(*config_sources))

        # 创建配置对象
        self._config = CoreConfig(**merged_config)
        return self._config

    @property
    def config(self) -> CoreConfig:
        """获取当前配置"""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload_config(self, config_file: Optional[Path] = None) -> CoreConfig:
        """重新加载配置"""
        return self.load_config(config_file)


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> CoreConfig:
    """获取全局配置"""
    return config_manager.config
