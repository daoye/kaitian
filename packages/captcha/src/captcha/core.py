"""captcha 模块核心实现.

提供统一的验证码挑战与求解接口，支持人工介入和扩展能力。
"""

from typing import Optional, Protocol
from dataclasses import dataclass


class CaptchaOutcome:
    """验证码处理结果.

    表示验证码识别/处理后的输出结果，用于判断下一步操作。
    """

    def __init__(
        self,
        status: str,
        data: Optional[dict] = None,
    ):
        self.status = status
        self.data = data or {}

    # 状态常量（便于外部使用）
    STATUS_SOLVED = "solved"
    STATUS_MANUAL_REQUIRED = "manual_required"
    STATUS_FAILED = "failed"
    STATUS_NOT_PRESENT = "not_present"


@dataclass
class CaptchaChallenge:
    """验证码挑战输入对象.

    封装验证码识别所需的所有上下文信息。
    """

    site: str
    challenge_type: str
    image_bytes: bytes
    page_url: str
    metadata: dict

    def to_dict(self) -> dict:
        """转换为字典，便于日志和调试."""
        return {
            "site": self.site,
            "challenge_type": self.challenge_type,
            "page_url": self.page_url,
            "has_image": len(self.image_bytes) > 0,
        }


class CaptchaSolver(Protocol):
    """验证码求解器接口协议.

    所有验证码求解器必须实现此协议。
    """

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        """解决验证码挑战.

        Args:
            challenge: 验证码挑战对象，包含图片字节、站点信息等

        Returns:
            CaptchaOutcome: 验证码处理结果

        Raises:
            Exception: 求解失败时抛出异常
        """
        ...


class ManualCaptchaSolver:
    """手动验证码求解器（默认实现）.

    始终返回 manual_required，强制人工介入。
    这是验证码处理链条的"保底"选项，确保流程不会中断。
    """

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        """返回手动介入结果."""
        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_MANUAL_REQUIRED,
            data={
                "message": "Manual intervention required",
                "reason": "No automatic solver configured",
                "site": challenge.site,
                "challenge_type": challenge.challenge_type,
            },
        )


class CaptchaOrchestrator:
    """验证码编排器.

    负责管理多个求解器策略，实现自动识别 -> 云服务兜底 -> 手动回退的链条。
    """

    def __init__(self, solvers: list):
        """初始化编排器.

        Args:
            solvers: 求解器列表，按优先级排序
        """
        self.solvers = solvers

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        """依次尝试所有求解器，直到成功或全部失败.

        Args:
            challenge: 验证码挑战对象

        Returns:
            CaptchaOutcome: 第一个成功的结果，或最后一个失败的结果
        """
        last_exception = None

        for solver in self.solvers:
            try:
                outcome = await solver.solve(challenge)
                if outcome.status == CaptchaOutcome.STATUS_SOLVED:
                    return outcome
            except Exception as e:
                last_exception = e
                continue

        # 所有求解器失败，返回最终失败结果
        if last_exception:
            return CaptchaOutcome(
                status=CaptchaOutcome.STATUS_FAILED,
                data={
                    "message": "All solvers failed",
                    "reason": str(last_exception),
                    "site": challenge.site,
                    "challenge_type": challenge.challenge_type,
                },
            )

        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_MANUAL_REQUIRED,
            data={
                "message": "No solver available",
                "reason": "Manual intervention required",
                "site": challenge.site,
                "challenge_type": challenge.challenge_type,
            },
        )
