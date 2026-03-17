"""stealth 类型定义."""

from dataclasses import dataclass, field
from typing import Literal, Protocol


# 指纹预设类型
FingerprintPreset = Literal[
    "chrome_windows",
    "chrome_mac",
    "safari_mac",
    "firefox_windows",
    "firefox_mac",
    "edge_windows",
    "mobile_android",
    "mobile_ios",
]

# 噪声级别
NoiseLevel = Literal["low", "medium", "high"]

# 风险级别
RiskLevel = Literal["none", "low", "medium", "high"]

# 补丁上下文
PatchContext = Literal["main", "iframe", "worker"]


@dataclass(frozen=True, slots=True)
class StealthProfile:
    """指纹画像 - 定义浏览器环境指纹配置.

    用于确保同一会话内的指纹一致性，避免随机切换导致的异常。

    Attributes:
        user_agent: User-Agent 字符串
        viewport: 视口尺寸 {"width": int, "height": int}
        locale: 语言地区，如 "zh-CN", "en-US"
        timezone: 时区 ID，如 "Asia/Shanghai", "America/New_York"
        platform: 平台标识，如 "Win32", "MacIntel"
        color_depth: 颜色深度，通常为 24
        pixel_ratio: 设备像素比，桌面通常为 1.0
        hardware_concurrency: 逻辑 CPU 核心数
        device_memory: 设备内存 (GB)
        max_touch_points: 最大触控点数
        mobile: 是否为移动设备
        primary_pointer: 主要指针类型 "fine"(精确) 或 "coarse"(粗略)
        hover_capable: 是否支持悬停
        prefers_reduced_motion: 是否偏好减少动画
        extra_headers: 额外的 HTTP 请求头
    """

    user_agent: str
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    platform: str = "Win32"
    color_depth: int = 24
    pixel_ratio: float = 1.0
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    mobile: bool = False
    primary_pointer: str = "fine"
    hover_capable: bool = True
    prefers_reduced_motion: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)

    def to_context_options(self) -> dict:
        """转换为 Playwright context options."""
        return {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": self.timezone,
            "extra_http_headers": self.extra_headers,
        }


@dataclass(frozen=True, slots=True)
class StealthConfig:
    """反检测配置.

    Attributes:
        enabled: 是否启用反检测
        fingerprint_preset: 指纹预设模板
        human_like: 是否启用人类行为模拟
        noise_level: 行为噪声级别
        enabled_patches: 显式启用的补丁列表
    """

    enabled: bool = True
    fingerprint_preset: FingerprintPreset = "chrome_windows"
    human_like: bool = True
    noise_level: NoiseLevel = "medium"
    enabled_patches: list[str] = field(
        default_factory=lambda: [
            name for name, spec in PATCH_CATALOG.items() if spec.default_enabled
        ]
    )


@dataclass(frozen=True, slots=True)
class PatchSpec:
    """反检测补丁规范.

    定义单个补丁的元数据和配置信息，用于 Patch Catalog 系统。

    Attributes:
        name: 补丁名称（与 JS 文件名一致）
        risk_level: 风险级别（none/low/medium/high）
        default_enabled: 是否默认启用
        contexts: 适用的上下文列表
        description: 补丁描述
    """

    name: str
    risk_level: RiskLevel = "none"
    default_enabled: bool = True
    contexts: list[PatchContext] = field(default_factory=lambda: ["main"])
    description: str = ""


@dataclass(frozen=True, slots=True)
class StealthSitePolicy:
    """站点特定策略.

    定义针对特定站点的反检测策略，支持覆盖默认配置。

    Attributes:
        name: 策略名称
        hosts: 匹配的站点列表（支持通配符 *.example.com）
        enable_patches: 额外启用的补丁列表
        disable_patches: 禁用的补丁列表
        risk_limit: 风险级别限制
        enabled: 策略是否启用
    """

    name: str
    hosts: list[str] = field(default_factory=list)
    enable_patches: list[str] = field(default_factory=list)
    disable_patches: list[str] = field(default_factory=list)
    risk_limit: RiskLevel = "medium"
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class StealthPlan:
    """反检测执行计划.

    由 StealthManager 生成，包含完整的反检测执行指令。

    Attributes:
        profile: 指纹画像配置
        init_scripts: 初始化时执行的 JavaScript 脚本列表
        launch_args: 浏览器启动参数
        behavior_delays: 行为延迟配置
    """

    profile: StealthProfile
    init_scripts: list[str] = field(default_factory=list)
    launch_args: list[str] = field(default_factory=list)
    behavior_delays: dict[str, tuple[float, float]] = field(default_factory=dict)


class StealthHook(Protocol):
    """反检测钩子协议.

    供 browser 模块调用，在上下文初始化时应用反检测设置。
    """

    async def __call__(self, context: object) -> None:
        """应用反检测设置到 Playwright 上下文.

        Args:
            context: Playwright BrowserContext 实例
        """
        ...


# Patch Catalog - 补丁规范注册表
PATCH_CATALOG: dict[str, PatchSpec] = {
    # 基础补丁（P0 基线）
    "device_profile": PatchSpec(
        name="device_profile",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设备画像共享基础脚本，为其他补丁提供统一的设备特征数据",
    ),
    "navigator_webdriver": PatchSpec(
        name="navigator_webdriver",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="隐藏 navigator.webdriver 属性，避免被检测为自动化工具",
    ),
    "navigator_plugins": PatchSpec(
        name="navigator_plugins",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="模拟真实的浏览器插件列表",
    ),
    "navigator_mime_types": PatchSpec(
        name="navigator_mime_types",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="模拟真实的 MIME 类型列表",
    ),
    "navigator_languages": PatchSpec(
        name="navigator_languages",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置 navigator.languages 属性，与用户语言环境一致",
    ),
    "navigator_vendor": PatchSpec(
        name="navigator_vendor",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置 navigator.vendor 属性，与浏览器厂商一致",
    ),
    "navigator_platform": PatchSpec(
        name="navigator_platform",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置 navigator.platform 属性，与操作系统平台一致",
    ),
    "navigator_hardware": PatchSpec(
        name="navigator_hardware",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置硬件并发数和设备内存",
    ),
    "navigator_max_touch_points": PatchSpec(
        name="navigator_max_touch_points",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置最大触控点数",
    ),
    "navigator_user_agent_data": PatchSpec(
        name="navigator_user_agent_data",
        risk_level="low",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置 navigator.userAgentData 对象，包含 UA-CH 数据",
    ),
    "navigator_permissions": PatchSpec(
        name="navigator_permissions",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="模拟 navigator.permissions 接口",
    ),
    "chrome_runtime": PatchSpec(
        name="chrome_runtime",
        risk_level="low",
        default_enabled=True,
        contexts=["main"],
        description="模拟 chrome.runtime 对象，Chrome 特有",
    ),
    "match_media": PatchSpec(
        name="match_media",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe"],
        description="设置媒体查询匹配状态",
    ),
    "visual_viewport": PatchSpec(
        name="visual_viewport",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe"],
        description="设置可视视口对象",
    ),
    "intl": PatchSpec(
        name="intl",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置国际化对象（如 Intl.DateTimeFormat）",
    ),
    "media_capabilities": PatchSpec(
        name="media_capabilities",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="设置媒体编解码能力",
    ),
    "webgl": PatchSpec(
        name="webgl",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe"],
        description="修改 WebGL 指纹，添加噪声",
    ),
    "canvas": PatchSpec(
        name="canvas",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe", "worker"],
        description="添加 Canvas 指纹噪声",
    ),
    "screen": PatchSpec(
        name="screen",
        risk_level="none",
        default_enabled=True,
        contexts=["main", "iframe"],
        description="修改 screen 对象属性",
    ),
    # 高风险补丁（默认禁用）
    "iframe_content_window": PatchSpec(
        name="iframe_content_window",
        risk_level="high",
        default_enabled=False,
        contexts=["main", "iframe"],
        description="跨 iframe 内容窗口补丁，高风险，可能导致功能异常",
    ),
    "media_codecs": PatchSpec(
        name="media_codecs",
        risk_level="high",
        default_enabled=False,
        contexts=["main", "iframe", "worker"],
        description="扩展媒体编解码器支持，高风险，可能影响媒体播放",
    ),
}


# Patch 解析器 API
def resolve_enabled_patches(
    enabled_patches: list[str] | None = None,
    risk_limit: RiskLevel = "medium",
    context: PatchContext = "main",
) -> list[str]:
    """解析启用的补丁列表.

    根据配置和风险级别过滤补丁，确保只应用符合条件的补丁。

    Args:
        enabled_patches: 显式指定的补丁列表，如果为 None 则使用 PATCH_CATALOG 的默认配置
        risk_limit: 最大允许的风险级别，超过此级别的补丁将被过滤
        context: 目标上下文，只返回适用于该上下文的补丁

    Returns:
        过滤和排序后的补丁名称列表
    """
    if enabled_patches is None:
        enabled_patches = [name for name, spec in PATCH_CATALOG.items() if spec.default_enabled]

    # 定义风险级别权重
    risk_weight = {"none": 0, "low": 1, "medium": 2, "high": 3}
    risk_limit_weight = risk_weight[risk_limit]

    filtered = []
    for name in enabled_patches:
        spec = PATCH_CATALOG.get(name)
        if spec is None:
            continue

        # 过滤风险级别
        if risk_weight[spec.risk_level] > risk_limit_weight:
            continue

        # 过滤上下文
        if context not in spec.contexts:
            continue

        filtered.append(name)

    # 按照 PATCH_CATALOG 的顺序排序（保持定义顺序）
    catalog_order = list(PATCH_CATALOG.keys())
    filtered.sort(key=lambda x: catalog_order.index(x) if x in catalog_order else 999)

    return filtered


def get_available_patches() -> list[str]:
    """获取所有可用的补丁列表.

    Returns:
        所有在 PATCH_CATALOG 中注册的补丁名称
    """
    return list(PATCH_CATALOG.keys())


def get_patch_spec(name: str) -> PatchSpec | None:
    """获取补丁规范.

    Args:
        name: 补丁名称

    Returns:
        补丁规范，如果不存在则返回 None
    """
    return PATCH_CATALOG.get(name)


def match_host(host: str, pattern: str) -> bool:
    """匹配主机名和模式.

    支持通配符 *.example.com 匹配子域名。

    Args:
        host: 实际主机名（如 www.example.com）
        pattern: 匹配模式（如 *.example.com 或 example.com）

    Returns:
        是否匹配
    """
    if pattern == "*":
        return True

    if pattern.startswith("*."):
        suffix = pattern[2:]
        return host == suffix or host.endswith(f".{suffix}")

    return host == pattern


def resolve_site_policy(
    url: str,
    policies: list[StealthSitePolicy],
) -> StealthSitePolicy | None:
    """解析适用于指定 URL 的站点策略.

    按照顺序检查策略列表，返回第一个匹配的策略。

    Args:
        url: 目标 URL
        policies: 站点策略列表

    Returns:
        匹配的站点策略，如果没有匹配则返回 None
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.netloc

    for policy in policies:
        if not policy.enabled:
            continue

        for pattern in policy.hosts:
            if match_host(host, pattern):
                return policy

    return None


def apply_site_policy(
    enabled_patches: list[str],
    policy: StealthSitePolicy,
) -> list[str]:
    """应用站点策略到补丁列表.

    根据 site policy 的配置调整补丁列表。

    Args:
        enabled_patches: 原始启用的补丁列表
        policy: 站点策略

    Returns:
        调整后的补丁列表
    """
    result = list(enabled_patches)

    for patch in policy.disable_patches:
        if patch in result:
            result.remove(patch)

    for patch in policy.enable_patches:
        if patch not in result:
            result.append(patch)

    return result


# 预设指纹模板库
PRESET_PROFILES: dict[FingerprintPreset, StealthProfile] = {
    "chrome_windows": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
        platform="Win32",
        color_depth=24,
        pixel_ratio=1.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        mobile=False,
        primary_pointer="fine",
        hover_capable=True,
        prefers_reduced_motion=False,
    ),
    "chrome_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone="America/New_York",
        platform="MacIntel",
        color_depth=30,
        pixel_ratio=2.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        mobile=False,
        primary_pointer="fine",
        hover_capable=True,
        prefers_reduced_motion=False,
    ),
    "safari_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Safari/605.1.15"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone="America/New_York",
        platform="MacIntel",
        color_depth=30,
        pixel_ratio=2.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        mobile=False,
        primary_pointer="fine",
        hover_capable=True,
        prefers_reduced_motion=False,
    ),
    "firefox_windows": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
        platform="Win32",
        color_depth=24,
        pixel_ratio=1.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        mobile=False,
        primary_pointer="fine",
        hover_capable=True,
        prefers_reduced_motion=False,
    ),
    "firefox_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone="America/New_York",
        platform="MacIntel",
        color_depth=30,
        pixel_ratio=2.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
    ),
    "edge_windows": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
        platform="Win32",
        color_depth=24,
        pixel_ratio=1.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        mobile=False,
        primary_pointer="fine",
        hover_capable=True,
        prefers_reduced_motion=False,
    ),
    "mobile_android": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        viewport={"width": 412, "height": 915},
        locale="zh-CN",
        timezone="Asia/Shanghai",
        platform="Linux armv8l",
        color_depth=24,
        pixel_ratio=2.625,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=5,
        mobile=True,
        primary_pointer="coarse",
        hover_capable=False,
        prefers_reduced_motion=False,
    ),
    "mobile_ios": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Mobile/15E148 Safari/604.1"
        ),
        viewport={"width": 393, "height": 852},
        locale="en-US",
        timezone="America/New_York",
        platform="iPhone",
        color_depth=32,
        pixel_ratio=3.0,
        hardware_concurrency=6,
        device_memory=6,
        max_touch_points=5,
        mobile=True,
        primary_pointer="coarse",
        hover_capable=False,
        prefers_reduced_motion=False,
    ),
}
