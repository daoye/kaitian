from dataclasses import dataclass, field
from typing import Literal, Protocol


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
NoiseLevel = Literal["low", "medium", "high"]
RiskLevel = Literal["none", "low", "medium", "high"]
PatchContext = Literal["main", "iframe", "worker"]


@dataclass(frozen=True, slots=True)
class StealthProfile:
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

    def to_context_options(self) -> dict[str, object]:
        return {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": self.timezone,
            "extra_http_headers": self.extra_headers,
        }


@dataclass(frozen=True, slots=True)
class StealthConfig:
    enabled: bool = False
    fingerprint_preset: FingerprintPreset = "chrome_windows"


@dataclass(frozen=True, slots=True)
class StealthPlan:
    profile: StealthProfile
    init_scripts: list[str] = field(default_factory=list)
    launch_args: list[str] = field(default_factory=list)
    behavior_delays: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StealthSitePolicy:
    name: str


class StealthHook(Protocol):
    async def __call__(self, context: object) -> None: ...


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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    ),
    "chrome_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    ),
    "safari_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Safari/605.1.15"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    ),
    "firefox_mac": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone="Asia/Shanghai",
        platform="MacIntel",
        color_depth=30,
        pixel_ratio=2.0,
        hardware_concurrency=8,
        device_memory=8,
        max_touch_points=0,
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    ),
    "mobile_ios": StealthProfile(
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Mobile/15E148 Safari/604.1"
        ),
        viewport={"width": 393, "height": 852},
        locale="zh-CN",
        timezone="Asia/Shanghai",
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
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    ),
}
