"""补丁加载器.

统一处理所有补丁的加载逻辑，消除重复代码。
"""

from .scripts import load_script, load_script_with_vars
from .types import PatchSpec, StealthProfile


class PatchLoader:
    """补丁加载器.

    根据 PatchSpec 元数据动态加载补丁脚本。
    """

    def __init__(self, profile: StealthProfile):
        """初始化补丁加载器.

        Args:
            profile: 指纹画像，用于需要 profile 的补丁
        """
        self._profile = profile

    def load_patch(self, spec: PatchSpec) -> str:
        """加载单个补丁脚本.

        根据 PatchSpec 元数据动态选择加载方法。

        Args:
            spec: 补丁规范

        Returns:
            JavaScript 脚本内容
        """
        # 特殊处理 device_profile，需要所有 profile 字段
        if spec.name == "device_profile":
            return self._load_device_profile()

        # 需要 profile 的补丁
        needs_profile = {
            "navigator_languages",
            "navigator_vendor",
            "navigator_platform",
            "navigator_hardware",
            "navigator_max_touch_points",
            "navigator_user_agent_data",
            "match_media",
            "visual_viewport",
            "intl",
            "media_capabilities",
            "webgl",
            "canvas",
            "screen",
        }

        if spec.name in needs_profile:
            return self._load_profile_dependent_patch(spec)

        # 不需要 profile 的补丁
        return load_script(spec.name)

    def _load_device_profile(self) -> str:
        """加载 device_profile 补丁."""
        from .profile_converter import ProfileConverter

        return load_script_with_vars(
            "device_profile",
            ProfileConverter.to_js_vars(self._profile),
        )

    def _load_profile_dependent_patch(self, spec: PatchSpec) -> str:
        """加载依赖 profile 的补丁."""
        from .profile_converter import ProfileConverter

        vars_mapping = {
            "navigator_languages": {
                "LOCALE": self._profile.locale,
                "LOCALE_SHORT": self._profile.locale.split("-")[0],
            },
            "navigator_vendor": {
                "VENDOR": ProfileConverter.infer_vendor(self._profile.user_agent),
            },
            "navigator_platform": {
                "PLATFORM": self._profile.platform,
            },
            "navigator_hardware": {
                "HARDWARE_CONCURRENCY": self._profile.hardware_concurrency,
                "DEVICE_MEMORY": self._profile.device_memory,
            },
            "navigator_max_touch_points": {
                "MAX_TOUCH_POINTS": self._profile.max_touch_points,
            },
            "navigator_user_agent_data": self._load_user_agent_data_patch(),
            "match_media": {
                "PRIMARY_POINTER": self._profile.primary_pointer,
                "HOVER_CAPABLE_BOOL": "true" if self._profile.hover_capable else "false",
                "PREFERS_REDUCED_MOTION_BOOL": "true"
                if self._profile.prefers_reduced_motion
                else "false",
                "MOBILE_BOOL": "true" if self._profile.mobile else "false",
                "PIXEL_RATIO": self._profile.pixel_ratio,
            },
            "visual_viewport": {
                "VIEWPORT_WIDTH": self._profile.viewport["width"],
                "VIEWPORT_HEIGHT": self._profile.viewport["height"],
                "MOBILE_BOOL": "true" if self._profile.mobile else "false",
            },
            "intl": {
                "LOCALE": self._profile.locale,
                "TIMEZONE": self._profile.timezone,
                "LOCALE_SHORT": self._profile.locale.split("-")[0],
            },
            "media_capabilities": {
                "MOBILE_BOOL": "true" if self._profile.mobile else "false",
                "DEVICE_MEMORY": self._profile.device_memory,
            },
            "webgl": self._load_webgl_patch(),
            "canvas": {
                "CANVAS_SEED": f"{self._profile.platform}_{self._profile.viewport['width']}_{self._profile.hardware_concurrency}",
            },
            "screen": {
                "SCREEN_WIDTH": self._profile.viewport["width"],
                "SCREEN_HEIGHT": self._profile.viewport["height"],
                "COLOR_DEPTH": self._profile.color_depth,
                "PIXEL_RATIO": self._profile.pixel_ratio,
            },
        }

        return load_script_with_vars(
            spec.name,
            vars_mapping.get(spec.name, {}),
        )

    def _load_user_agent_data_patch(self) -> dict:
        """加载 navigator_user_agent_data 补丁的变量."""
        from .profile_converter import ProfileConverter

        brands = ProfileConverter.infer_ua_data_brands(self._profile.user_agent)
        ua_full_version = ProfileConverter._extract_browser_version(self._profile.user_agent)
        is_mobile = "Mobile" in self._profile.user_agent or self._profile.max_touch_points > 0

        return {
            "BRANDS_JSON": brands,
            "MOBILE_BOOL": "true" if is_mobile else "false",
            "PLATFORM": self._profile.platform,
            "ARCHITECTURE": "arm" if "arm" in self._profile.platform.lower() else "x86",
            "BITNESS": "64",
            "MODEL": "" if not is_mobile else "Generic Mobile",
            "PLATFORM_VERSION": "15.0.0" if "iPhone" in self._profile.platform else "10.0.0",
            "UA_FULL_VERSION": ua_full_version,
        }

    def _load_webgl_patch(self) -> dict:
        """加载 webgl 补丁的变量."""
        is_intel = "Intel" in self._profile.platform or self._profile.platform in [
            "Win32",
            "MacIntel",
        ]
        vendor = "Intel Inc." if is_intel else "Google Inc. (NVIDIA)"
        renderer = (
            "Intel Iris OpenGL Engine"
            if is_intel
            else "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)"
        )

        return {
            "VENDOR": vendor,
            "RENDERER": renderer,
        }
