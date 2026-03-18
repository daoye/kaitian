"""Profile 字段转换工具.

统一处理 StealthProfile 到 JavaScript 变量的转换。
"""

from .types import StealthProfile


class ProfileConverter:
    """Profile 字段转换器.

    统一处理 profile 到 JavaScript 变量的转换逻辑。
    """

    @staticmethod
    def to_js_vars(profile: StealthProfile) -> dict:
        """将 StealthProfile 转换为 JavaScript 变量字典.

        Args:
            profile: 指纹画像

        Returns:
            JavaScript 变量字典，用于模板替换
        """
        return {
            "USER_AGENT": profile.user_agent,
            "PLATFORM": profile.platform,
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
            "PREFERS_REDUCED_MOTION_BOOL": "true" if profile.prefers_reduced_motion else "false",
            "DEVICE_SEED": f"{profile.platform}_{profile.viewport['width']}_{profile.hardware_concurrency}",
        }

    @staticmethod
    def infer_vendor(user_agent: str) -> str:
        """从 User-Agent 推断 vendor.

        Args:
            user_agent: User-Agent 字符串

        Returns:
            Vendor 字符串
        """
        if "Chrome" in user_agent or "Edg/" in user_agent:
            return "Google Inc."
        if "Safari" in user_agent and "Chrome" not in user_agent:
            return "Apple Computer, Inc."
        return ""

    @staticmethod
    def infer_ua_data_brands(user_agent: str) -> list[dict[str, str]]:
        """从 User-Agent 推断 UA-CH brands.

        Args:
            user_agent: User-Agent 字符串

        Returns:
            brands 列表
        """
        version = ProfileConverter._extract_browser_version(user_agent).split(".")[0]
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

    @staticmethod
    def _extract_browser_version(user_agent: str) -> str:
        """从 User-Agent 提取浏览器版本.

        Args:
            user_agent: User-Agent 字符串

        Returns:
            版本字符串
        """
        markers = ["Edg/", "Chrome/", "Version/", "Firefox/"]
        for marker in markers:
            if marker in user_agent:
                tail = user_agent.split(marker, maxsplit=1)[1]
                return tail.split(" ", maxsplit=1)[0]
        return "120.0.0.0"
