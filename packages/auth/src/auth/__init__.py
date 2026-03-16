"""auth 模块 - 认证与会话管理."""

from .__version__ import __version__
from .manager import AuthManager
from .repository import SessionRepository
from .sites import ZnzmoAuthenticator
from .types import Credentials, CaptchaOutcome, VerifyResult
from .exceptions import (
    AuthError,
    SessionNotFoundError,
    SessionExpiredError,
    InvalidCredentialsError,
    LoginFailedError,
    CaptchaRequiredError,
    SiteNotSupportedError,
)

__all__ = [
    "__version__",
    # 核心类
    "AuthManager",
    "SessionRepository",
    # 站点适配器
    "ZnzmoAuthenticator",
    # 类型
    "Credentials",
    "CaptchaOutcome",
    "VerifyResult",
    # 异常
    "AuthError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "InvalidCredentialsError",
    "LoginFailedError",
    "CaptchaRequiredError",
    "SiteNotSupportedError",
]
