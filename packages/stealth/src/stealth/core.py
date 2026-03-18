"""stealth 核心实现."""

import json
import random
from typing import Any

from .patch_loader import PatchLoader
from .scripts import load_script, load_script_with_vars
from .types import (
    NoiseLevel,
    PATCH_CATALOG,
    PRESET_PROFILES,
    PatchContext,
    RiskLevel,
    StealthConfig,
    StealthPlan,
    StealthProfile,
    StealthSitePolicy,
    apply_site_policy,
    resolve_enabled_patches,
    resolve_site_policy,
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
        site_policies: list[StealthSitePolicy] | None = None,
    ):
        """初始化反检测管理器.

        Args:
            config: 反检测配置，使用默认配置如果未提供
            custom_profile: 自定义指纹画像，覆盖预设模板
            site_policies: 站点特定策略列表，用于根据 URL 动态调整补丁
        """
        self._config = config or StealthConfig()
        self._custom_profile = custom_profile
        self._site_policies = site_policies or []
        self._plan: StealthPlan | None = None

    def build_plan(
        self,
        url: str | None = None,
        context: PatchContext = "main",
    ) -> StealthPlan:
        """构建反检测执行计划.

        根据配置生成完整的执行计划，包括指纹配置、初始化脚本、启动参数等。
        如果提供了 URL，会根据匹配的站点策略动态调整补丁列表和风险级别。

        Args:
            url: 目标 URL，用于匹配站点策略，如果为 None 则使用默认配置
            context: 目标执行上下文，默认为 main

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

        # 解析站点策略
        site_policy = resolve_site_policy(url, self._site_policies) if url else None

        # 根据策略调整补丁列表
        if site_policy:
            enabled_patches = apply_site_policy(self._config.enabled_patches, site_policy)
            risk_limit = site_policy.risk_limit
        else:
            enabled_patches = self._config.enabled_patches
            risk_limit = "medium"

        effective_patches = resolve_enabled_patches(
            enabled_patches=enabled_patches,
            risk_limit=risk_limit,
            context=context,
        )

        init_scripts = self._generate_init_scripts(profile, effective_patches, risk_limit, context)
        launch_args = self._generate_launch_args()
        behavior_delays = self._generate_behavior_delays()

        self._plan = StealthPlan(
            profile=profile,
            init_scripts=init_scripts,
            launch_args=launch_args,
            behavior_delays=behavior_delays,
            site_policy=site_policy.name if site_policy else None,
            effective_patches=effective_patches,
            risk_limit=risk_limit,
            context=context,
        )
        return self._plan

    async def apply_to_context(self, context: Any, url: str | None = None) -> None:
        """应用反检测设置到 Playwright 上下文.

        在 BrowserManager 创建上下文后调用，注入反检测脚本。
        如果提供了 URL，会根据站点策略动态调整补丁。

        Args:
            context: Playwright BrowserContext 实例
            url: 目标 URL，用于匹配站点策略
        """
        if not self._config.enabled:
            return

        plan = self.build_plan(url) if url else (self._plan or self.build_plan())

        for script in plan.init_scripts:
            await context.add_init_script(script)

    async def apply_to_page(self, page: Any, url: str | None = None) -> None:
        """应用反检测设置到页面.

        将初始化脚本注入到指定页面，确保新页面也应用反检测设置。
        如果提供了 URL，会根据站点策略动态调整补丁。

        Args:
            page: Playwright Page 实例
            url: 目标 URL，用于匹配站点策略
        """
        if not self._config.enabled:
            return

        plan = self.build_plan(url) if url else (self._plan or self.build_plan())

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

    def _generate_init_scripts(
        self,
        profile: StealthProfile,
        enabled_patches: list[str] | None = None,
        risk_limit: RiskLevel = "medium",
        context: PatchContext = "main",
    ) -> list[str]:
        """生成初始化脚本列表.

        根据启用的补丁生成对应的 JavaScript 脚本。
        第一个脚本必须是 device_profile，为其他补丁提供共享数据。
        使用 Patch 解析器来验证和过滤补丁列表。
        使用 PatchLoader 统一加载逻辑，消除重复代码。
        """
        self._validate_profile(profile)

        patches = enabled_patches or []
        loader = PatchLoader(profile)

        scripts = [
            loader.load_patch(PATCH_CATALOG[name]) for name in patches if name in PATCH_CATALOG
        ]

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
