# Captcha 模块

提供统一的验证码挑战与求解接口，支持人工介入和扩展能力。

## 核心接口

### CaptchaChallenge

验证码挑战输入对象，封装所有上下文信息。

```python
from dataclasses import dataclass

@dataclass
class CaptchaChallenge:
    site: str              # 站点标识（如 "znzmo"）
    challenge_type: str      # 验证码类型（如 "image", "recaptcha_v2", "turnstile"）
    image_bytes: bytes       # 验证码图片字节数据
    page_url: str          # 当前页面 URL
    metadata: dict         # 扩展元信息（如验证码元素选择器等）
```

### CaptchaOutcome

验证码处理结果对象，用于判断下一步操作。

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class CaptchaOutcome:
    status: str                                   # "solved", "manual_required", "failed", "not_present"
    data: Optional[Dict[str, Any]] = None  # 扩展数据（如识别结果、错误信息）
```

**状态常量**:
- `STATUS_SOLVED`: "solved" - 验证码已成功识别
- `STATUS_MANUAL_REQUIRED`: "manual_required" - 需要人工介入
- `STATUS_FAILED`: "failed" - 验证码处理失败
- `STATUS_NOT_PRESENT`: "not_present" - 未检测到验证码

### CaptchaSolver（协议）

验证码求解器接口协议。

```python
from typing import Protocol

class CaptchaSolver(Protocol):
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        """解决验证码挑战.

        Args:
            challenge: 验证码挑战对象

        Returns:
            CaptchaOutcome: 验证码处理结果

        Raises:
            Exception: 求解失败时抛出异常
        """
```

### ManualCaptchaSolver

手动验证码求解器（默认实现）。

始终返回 `manual_required`，强制人工介入。这是验证码处理链条的"保底"选项，确保流程不会中断。

```python
class ManualCaptchaSolver:
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_MANUAL_REQUIRED,
            data={
                "message": "Manual intervention required",
                "reason": "No automatic solver configured",
                "site": challenge.site,
                "challenge_type": challenge.challenge_type,
            },
        )
```

### CaptchaOrchestrator

验证码编排器，管理多个求解器策略。

实现自动识别 → 云服务兜底 → 手动回退的链条。

```python
class CaptchaOrchestrator:
    def __init__(self, solvers: list):
        """初始化编排器。

        Args:
            solvers: 求解器列表，按优先级排序
        """
        self.solvers = solvers

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        """依次尝试所有求解器，直到成功或全部失败.

        Returns:
            CaptchaOutcome: 第一个成功的结果，或最后一个失败的结果
        """
        # 依次尝试所有求解器
        for solver in self.solvers:
            try:
                outcome = await solver.solve(challenge)
                if outcome.status == CaptchaOutcome.STATUS_SOLVED:
                    return outcome
            except Exception as e:
                continue

        # 所有求解器失败，返回手动介入
        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_MANUAL_REQUIRED,
            data={
                "message": "Manual intervention required",
                "reason": "No solver available",
                "site": challenge.site,
                "challenge_type": challenge.challenge_type,
            },
        )
```

## 使用示例

### 在 ZnzmoAuthenticator 中使用手动求解器（当前默认）

```python
from captcha import CaptchaChallenge, CaptchaOutcome, ManualCaptchaSolver
from auth.sites.znzmo.authenticator import ZnzmoAuthenticator

# 使用默认手动求解器
auth = ZnzmoAuthenticator(captcha_solver=ManualCaptchaSolver())

try:
    session = await auth.login({"username": "user", "password": "pass"})
except CaptchaRequiredError as e:
    # 捕获 CaptchaRequiredError，需要人工介入
    print(f"需要人工介入: {e}")
```

### 未来扩展：接入自动识别

当需要接入自动识别服务（如 PaddleOCR、2Captcha）时，只需实现 CaptchaSolver 协议：

```python
from paddleocr import PaddleOCR

class PaddleOCRSolver:
    """基于 PaddleOCR 的验证码求解器."""

    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True)

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        # 识别验证码图片
        result = self.ocr.ocr(challenge.image_bytes, cls=True)

        # 提取识别的文本
        if result and len(result) > 0:
            recognized_text = result[0].get('rec_texts', [''])[0]
            return CaptchaOutcome(
                status=CaptchaOutcome.STATUS_SOLVED,
                data={"code": recognized_text},
            )

        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_FAILED,
            data={"reason": "OCR recognition failed"},
        )
```

### 多求解器策略

使用 CaptchaOrchestrator 管理多个求解器：

```python
from captcha import CaptchaChallenge, CaptchaOutcome, CaptchaOrchestrator
from paddleocr import PaddleOCRSolver
from twocaptcha import TwoCaptchaSolver

# 配置求解器列表（按优先级）
orchestrator = CaptchaOrchestrator([
    PaddleOCRSolver(),              # 第一优先级：本地 OCR
    TwoCaptchaSolver(api_key="..."),  # 第二优先级：云服务兜底
    ManualCaptchaSolver(),           # 第三优先级：手动介入
])

# 使用编排器
outcome = await orchestrator.solve(challenge)
```

## 集成到 Auth 模块

CaptchaOutcome 与 `auth.types.CaptchaOutcome` 兼容。

## 扩展点

### 1. 新的求解器实现

只需实现 `CaptchaSolver` 协议，即可无缝接入：

```python
class CustomSolver:
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        # 自定义求解逻辑
        return CaptchaOutcome(
            status=CaptchaOutcome.STATUS_SOLVED,
            data={"code": "your_solution"},
        )
```

### 2. 验证码类型自动检测

未来可以扩展 CaptchaChallenge 类，自动检测验证码类型：

```python
class CaptchaChallenge:
    # ... 现有字段

    def detect_type(self) -> str:
        """根据页面元信息自动检测验证码类型."""
        if "recaptcha" in self.page_url.lower():
            return "recaptcha_v2"
        elif "turnstile" in self.page_url.lower():
            return "turnstile"
        else:
            return "image"
```

### 3. 可观测性

建议为 CaptchaOrchestrator 添加结构化日志和指标统计：

```python
import logging

logger = logging.getLogger("captcha.orchestrator")

class CaptchaOrchestrator:
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaOutcome:
        logger.info("captcha.detected", extra={
            "site": challenge.site,
            "type": challenge.challenge_type,
        })

        outcome = await self._try_solvers(challenge)

        if outcome.status == CaptchaOutcome.STATUS_SOLVED:
            logger.info("captcha.solved", extra={
                "site": challenge.site,
                "solver": outcome.data.get("solver"),
            })
        else:
            logger.warning("captcha.failed", extra={
                "site": challenge.site,
                "reason": outcome.data.get("reason"),
            })

        return outcome
```

## 测试

运行测试确保模块正常工作：

```bash
uv run pytest packages/captcha/tests/ -v
```

## 安装

```bash
pip install -e .
```

## 安装

```bash
pip install -e .
```

