"""stealth 核心实现."""

import json
import random
from typing import Any

from .scripts import load_script, load_script_with_vars
from .types import (
    NoiseLevel,
    PRESET_PROFILES,
    StealthConfig,
    StealthPlan,
    StealthProfile,
    resolve_enabled_patches,
)


class StealthManager:
    """反检测管理器.

    负责生成反检测执行计划并应用到 Playwright 上下文。
    核心原则：会话内指纹一致性优先于高噪声随机化。
    """

    def __init__(
        self,
        config: StealthConfig | None = None,
        custom_profile: StealthProfile | None = None,
    ):
        """初始化反检测管理器.

        Args:
            config: 反检测配置，使用默认配置如果未提供
            custom_profile: 自定义指纹画像，覆盖预设模板
        """
        self._config = config or StealthConfig()
        self._custom_profile = custom_profile
        self._plan: StealthPlan | None = None

    def build_plan(self) -> StealthPlan:
        """构建反检测执行计划.

        根据配置生成完整的执行计划，包括指纹配置、初始化脚本、启动参数等。

        Returns:
            StealthPlan: 反检测执行计划
        """
        if not self._config.enabled:
            return StealthPlan(
                profile=self._get_profile(),
                init_scripts=[],
                launch_args=[],
                behavior_delays={},
            )

        profile = self._get_profile()
        init_scripts = self._generate_init_scripts(profile)
        launch_args = self._generate_launch_args()
        behavior_delays = self._generate_behavior_delays()

        self._plan = StealthPlan(
            profile=profile,
            init_scripts=init_scripts,
            launch_args=launch_args,
            behavior_delays=behavior_delays,
        )
        return self._plan

    async def apply_to_context(self, context: Any) -> None:
        """应用反检测设置到 Playwright 上下文.

        在 BrowserManager 创建上下文后调用，注入反检测脚本。

        Args:
            context: Playwright BrowserContext 实例
        """
        if not self._config.enabled:
            return

        plan = self._plan or self.build_plan()

        for script in plan.init_scripts:
            await context.add_init_script(script)

    async def apply_to_page(self, page: Any) -> None:
        """应用反检测设置到页面.

        将初始化脚本注入到指定页面，确保新页面也应用反检测设置。

        Args:
            page: Playwright Page 实例
        """
        if not self._config.enabled:
            return

        plan = self._plan or self.build_plan()

        for script in plan.init_scripts:
            await page.add_init_script(script)

    def _get_profile(self) -> StealthProfile:
        """获取指纹画像配置."""
        if self._custom_profile:
            return self._custom_profile
        return PRESET_PROFILES[self._config.fingerprint_preset]

    def _validate_profile(self, profile: StealthProfile) -> None:
        """验证设备画像一致性.

        检查跨 UA/UA-CH/platform/screen/touch 等字段的一致性。
        不一致时抛出 ValueError。
        """
        errors = []

        if profile.mobile and profile.max_touch_points == 0:
            errors.append("mobile=True but max_touch_points=0")
        if not profile.mobile and profile.max_touch_points > 0:
            errors.append("mobile=False but max_touch_points>0")

        if profile.mobile and profile.primary_pointer != "coarse":
            errors.append("mobile=True but primary_pointer is not 'coarse'")
        if not profile.mobile and profile.primary_pointer != "fine":
            errors.append("mobile=False but primary_pointer is not 'fine'")

        if profile.mobile and profile.hover_capable:
            errors.append("mobile=True but hover_capable=True")
        if not profile.mobile and not profile.hover_capable:
            errors.append("mobile=False but hover_capable=False")

        if "Windows" in profile.user_agent and profile.platform != "Win32":
            errors.append("UA contains Windows but platform is not Win32")
        if "Macintosh" in profile.user_agent and profile.platform not in [
            "MacIntel",
            "iPhone",
            "iPad",
        ]:
            errors.append("UA contains Macintosh but platform does not match")

        if errors:
            raise ValueError(f"Profile validation failed: {'; '.join(errors)}")

    def _generate_init_scripts(self, profile: StealthProfile) -> list[str]:
        """生成初始化脚本列表.

        根据启用的补丁生成对应的 JavaScript 脚本。
        第一个脚本必须是 device_profile，为其他补丁提供共享数据。
        使用 Patch 解析器来验证和过滤补丁列表。
        """
        self._validate_profile(profile)

        # 使用 Patch 解析器过滤和排序补丁
        patches = resolve_enabled_patches(
            enabled_patches=self._config.enabled_patches,
            risk_limit="medium",  # 默认只允许 medium 及以下风险
            context="main",  # 主上下文
        )

        scripts = []

        if "device_profile" in patches:
            scripts.append(self._patch_device_profile(profile))

        if "navigator_webdriver" in patches:
            scripts.append(self._patch_navigator_webdriver())

        if "navigator_plugins" in patches:
            scripts.append(self._patch_navigator_plugins())

        if "navigator_mime_types" in patches:
            scripts.append(self._patch_navigator_mime_types())

        if "navigator_languages" in patches:
            scripts.append(self._patch_navigator_languages(profile))

        if "navigator_vendor" in patches:
            scripts.append(self._patch_navigator_vendor(profile))

        if "navigator_platform" in patches:
            scripts.append(self._patch_navigator_platform(profile))

        if "navigator_hardware" in patches:
            scripts.append(self._patch_navigator_hardware(profile))

        if "navigator_max_touch_points" in patches:
            scripts.append(self._patch_navigator_max_touch_points(profile))

        if "navigator_user_agent_data" in patches:
            scripts.append(self._patch_navigator_user_agent_data(profile))

        if "navigator_permissions" in patches:
            scripts.append(self._patch_navigator_permissions())

        if "chrome_runtime" in patches:
            scripts.append(self._patch_chrome_runtime())

        if "iframe_content_window" in patches:
            scripts.append(self._patch_iframe_content_window())

        if "media_codecs" in patches:
            scripts.append(self._patch_media_codecs())

        if "match_media" in patches:
            scripts.append(self._patch_match_media(profile))

        if "visual_viewport" in patches:
            scripts.append(self._patch_visual_viewport(profile))

        if "intl" in patches:
            scripts.append(self._patch_intl(profile))

        if "media_capabilities" in patches:
            scripts.append(self._patch_media_capabilities(profile))

        if "webgl" in patches:
            scripts.append(self._patch_webgl(profile))

        if "canvas" in patches:
            scripts.append(self._patch_canvas(profile))

        if "screen" in patches:
            scripts.append(self._patch_screen(profile))

        return scripts

    def _generate_launch_args(self) -> list[str]:
        """生成浏览器启动参数."""
        args = [
            "--disable-blink-features=AutomationControlled",
        ]

        if self._config.human_like:
            args.extend(
                [
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ]
            )

        return args

    def _generate_behavior_delays(self) -> dict[str, tuple[float, float]]:
        """生成行为延迟配置.

        Returns:
            各行为的延迟范围 (min, max) 秒
        """
        noise = self._config.noise_level

        delays = {
            "click": (0.1, 0.3),
            "type": (0.05, 0.15),
            "scroll": (0.2, 0.5),
            "wait": (1.0, 3.0),
        }

        if noise == "low":
            delays = {
                "click": (0.05, 0.15),
                "type": (0.03, 0.08),
                "scroll": (0.1, 0.3),
                "wait": (0.5, 1.5),
            }
        elif noise == "high":
            delays = {
                "click": (0.2, 0.6),
                "type": (0.1, 0.25),
                "scroll": (0.4, 1.0),
                "wait": (2.0, 5.0),
            }

        return delays

    def get_random_delay(self, action: str) -> float:
        """获取随机行为延迟.

        Args:
            action: 行为类型 (click, type, scroll, wait)

        Returns:
            随机延迟秒数
        """
        plan = self._plan or self.build_plan()
        min_delay, max_delay = plan.behavior_delays.get(action, (0.1, 0.3))
        return random.uniform(min_delay, max_delay)

    def _patch_device_profile(self, profile: StealthProfile) -> str:
        """注入设备画像共享基础."""
        return load_script_with_vars(
            "device_profile",
            {
                "USER_AGENT": profile.user_agent,
                "PLATFORM": profile.platform,
                "VENDOR": self._infer_vendor(profile.user_agent),
                "VIEWPORT_WIDTH": profile.viewport["width"],
                "VIEWPORT_HEIGHT": profile.viewport["height"],
                "SCREEN_WIDTH": profile.viewport["width"],
                "SCREEN_HEIGHT": profile.viewport["height"],
                "COLOR_DEPTH": profile.color_depth,
                "PIXEL_RATIO": profile.pixel_ratio,
                "HARDWARE_CONCURRENCY": profile.hardware_concurrency,
                "DEVICE_MEMORY": profile.device_memory,
                "MAX_TOUCH_POINTS": profile.max_touch_points,
                "LOCALE": profile.locale,
                "TIMEZONE": profile.timezone,
                "LOCALE_SHORT": profile.locale.split("-")[0],
                "MOBILE_BOOL": "true" if profile.mobile else "false",
                "PRIMARY_POINTER": profile.primary_pointer,
                "HOVER_CAPABLE_BOOL": "true" if profile.hover_capable else "false",
                "PREFERS_REDUCED_MOTION_BOOL": "true"
                if profile.prefers_reduced_motion
                else "false",
                "DEVICE_SEED": f"{profile.platform}_{profile.viewport['width']}_{profile.hardware_concurrency}",
            },
        )

    def _patch_navigator_webdriver(self) -> str:
        """隐藏 navigator.webdriver 属性."""
        return load_script("navigator_webdriver")

    def _patch_navigator_plugins(self) -> str:
        """模拟 navigator.plugins."""
        return load_script("navigator_plugins")

    def _patch_navigator_languages(self, profile: StealthProfile) -> str:
        """设置 navigator.languages."""
        return load_script_with_vars(
            "navigator_languages",
            {
                "LOCALE": profile.locale,
                "LOCALE_SHORT": profile.locale.split("-")[0],
            },
        )

    def _patch_navigator_vendor(self, profile: StealthProfile) -> str:
        vendor = self._infer_vendor(profile.user_agent)
        return load_script_with_vars("navigator_vendor", {"VENDOR": vendor})

    def _patch_navigator_platform(self, profile: StealthProfile) -> str:
        return load_script_with_vars("navigator_platform", {"PLATFORM": profile.platform})

    def _patch_navigator_hardware(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "navigator_hardware",
            {
                "HARDWARE_CONCURRENCY": profile.hardware_concurrency,
                "DEVICE_MEMORY": profile.device_memory,
            },
        )

    def _patch_navigator_max_touch_points(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "navigator_max_touch_points",
            {"MAX_TOUCH_POINTS": profile.max_touch_points},
        )

    def _patch_navigator_user_agent_data(self, profile: StealthProfile) -> str:
        brands = self._infer_ua_data_brands(profile.user_agent)
        ua_full_version = self._extract_browser_version(profile.user_agent)
        is_mobile = "Mobile" in profile.user_agent or profile.max_touch_points > 0
        return load_script_with_vars(
            "navigator_user_agent_data",
            {
                "BRANDS_JSON": json.dumps(brands),
                "MOBILE_BOOL": "true" if is_mobile else "false",
                "PLATFORM": profile.platform,
                "ARCHITECTURE": "arm" if "arm" in profile.platform.lower() else "x86",
                "BITNESS": "64",
                "MODEL": "" if not is_mobile else "Generic Mobile",
                "PLATFORM_VERSION": "15.0.0" if "iPhone" in profile.platform else "10.0.0",
                "UA_FULL_VERSION": ua_full_version,
            },
        )

    def _patch_navigator_permissions(self) -> str:
        return load_script("navigator_permissions")

    def _patch_chrome_runtime(self) -> str:
        return load_script("chrome_runtime")

    def _patch_iframe_content_window(self) -> str:
        return load_script("iframe_content_window")

    def _patch_media_codecs(self) -> str:
        return load_script("media_codecs")

    def _patch_webgl(self, profile: StealthProfile) -> str:
        """修改 WebGL 指纹."""
        is_intel = "Intel" in profile.platform or profile.platform in ["Win32", "MacIntel"]
        vendor = "Intel Inc." if is_intel else "Google Inc. (NVIDIA)"
        renderer = (
            "Intel Iris OpenGL Engine"
            if is_intel
            else "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)"
        )

        return load_script_with_vars(
            "webgl",
            {
                "VENDOR": vendor,
                "RENDERER": renderer,
            },
        )

    def _patch_navigator_mime_types(self) -> str:
        return load_script("navigator_mime_types")

    def _patch_match_media(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "match_media",
            {
                "PRIMARY_POINTER": profile.primary_pointer,
                "HOVER_CAPABLE_BOOL": "true" if profile.hover_capable else "false",
                "PREFERS_REDUCED_MOTION_BOOL": "true"
                if profile.prefers_reduced_motion
                else "false",
                "MOBILE_BOOL": "true" if profile.mobile else "false",
                "PIXEL_RATIO": profile.pixel_ratio,
            },
        )

    def _patch_visual_viewport(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "visual_viewport",
            {
                "VIEWPORT_WIDTH": profile.viewport["width"],
                "VIEWPORT_HEIGHT": profile.viewport["height"],
                "MOBILE_BOOL": "true" if profile.mobile else "false",
            },
        )

    def _patch_intl(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "intl",
            {
                "LOCALE": profile.locale,
                "TIMEZONE": profile.timezone,
                "LOCALE_SHORT": profile.locale.split("-")[0],
            },
        )

    def _patch_media_capabilities(self, profile: StealthProfile) -> str:
        return load_script_with_vars(
            "media_capabilities",
            {
                "MOBILE_BOOL": "true" if profile.mobile else "false",
                "DEVICE_MEMORY": profile.device_memory,
            },
        )

    def _patch_canvas(self, profile: StealthProfile) -> str:
        seed = f"{profile.platform}_{profile.viewport['width']}_{profile.hardware_concurrency}"
        return load_script_with_vars(
            "canvas",
            {
                "CANVAS_SEED": seed,
            },
        )

    def _patch_screen(self, profile: StealthProfile) -> str:
        """修改 screen 对象."""
        return load_script_with_vars(
            "screen",
            {
                "SCREEN_WIDTH": profile.viewport["width"],
                "SCREEN_HEIGHT": profile.viewport["height"],
                "COLOR_DEPTH": profile.color_depth,
                "PIXEL_RATIO": profile.pixel_ratio,
            },
        )

    def _infer_vendor(self, user_agent: str) -> str:
        if "Chrome" in user_agent or "Edg/" in user_agent:
            return "Google Inc."
        if "Safari" in user_agent and "Chrome" not in user_agent:
            return "Apple Computer, Inc."
        return ""

    def _infer_ua_data_brands(self, user_agent: str) -> list[dict[str, str]]:
        version = self._extract_browser_version(user_agent).split(".")[0]
        if "Edg/" in user_agent:
            return [
                {"brand": "Chromium", "version": version},
                {"brand": "Microsoft Edge", "version": version},
                {"brand": "Not.A/Brand", "version": "24"},
            ]
        if "Chrome/" in user_agent:
            return [
                {"brand": "Chromium", "version": version},
                {"brand": "Google Chrome", "version": version},
                {"brand": "Not.A/Brand", "version": "24"},
            ]
        if "Safari" in user_agent and "Chrome" not in user_agent:
            return [
                {"brand": "WebKit", "version": "605"},
                {"brand": "Safari", "version": "17"},
            ]
        return [{"brand": "Chromium", "version": version}]

    def _extract_browser_version(self, user_agent: str) -> str:
        markers = ["Edg/", "Chrome/", "Version/", "Firefox/"]
        for marker in markers:
            if marker in user_agent:
                tail = user_agent.split(marker, maxsplit=1)[1]
                return tail.split(" ", maxsplit=1)[0]
        return "120.0.0.0"
