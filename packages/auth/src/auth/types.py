"""auth 类型定义."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Credentials:
    """认证凭据."""

    username: str
    password: str


@dataclass
class CaptchaOutcome:
    """验证码处理结果."""

    status: str  # "not_present", "manual_required", "solved", "failed"
    data: Optional[Dict[str, Any]] = None


@dataclass
class VerifyResult:
    """验证结果."""

    is_valid: bool
    message: str = ""
    details: Optional[Dict[str, Any]] = None
