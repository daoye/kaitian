"""captcha 类型定义.

此模块统一导出验证码相关的类型和协议。
避免与 auth 模块产生循环导入。
"""

# 导出核心类型
from .core import (
    CaptchaChallenge,
    CaptchaOutcome,
    CaptchaSolver,
    ManualCaptchaSolver,
    CaptchaOrchestrator,
)

# 导出异常类型
from .exceptions import CaptchaError

__all__ = [
    "CaptchaChallenge",
    "CaptchaOutcome",
    "CaptchaSolver",
    "CaptchaError",
    "ManualCaptchaSolver",
    "CaptchaOrchestrator",
]
