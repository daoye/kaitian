"""stealth 模块单元测试."""

import pytest

from stealth import (
    PRESET_PROFILES,
    PATCH_CATALOG,
    PatchSpec,
    PatchContext,
    RiskLevel,
    FingerprintPreset,
    NoiseLevel,
    StealthConfig,
    StealthManager,
    StealthPlan,
    StealthProfile,
    StealthSitePolicy,
    apply_site_policy,
    get_available_scripts,
    get_available_patches,
    get_patch_spec,
    match_host,
    resolve_enabled_patches,
    resolve_site_policy,
)
from stealth.patch_loader import PatchLoader


class TestStealthProfile:
    """测试指纹画像数据模型."""

    def test_profile_creation(self):
        """测试创建指纹画像."""
        profile = StealthProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone="Asia/Shanghai",
            platform="Win32",
        )
        assert profile.user_agent.startswith("Mozilla/5.0")
        assert profile.viewport["width"] == 1920
        assert profile.locale == "zh-CN"
        assert profile.timezone == "Asia/Shanghai"
        assert profile.platform == "Win32"

    def test_profile_to_context_options(self):
        """测试转换为 Playwright context options."""
        profile = StealthProfile(
            user_agent="Test UA",
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone="America/New_York",
            extra_headers={"X-Custom": "value"},
        )
        options = profile.to_context_options()

        assert options["user_agent"] == "Test UA"
        assert options["viewport"] == {"width": 1366, "height": 768}
        assert options["locale"] == "en-US"
        assert options["timezone_id"] == "America/New_York"
        assert options["extra_http_headers"] == {"X-Custom": "value"}

    def test_profile_defaults(self):
        """测试默认属性值."""
        profile = StealthProfile(user_agent="Test")
        assert profile.color_depth == 24
        assert profile.pixel_ratio == 1.0
        assert profile.hardware_concurrency == 8
        assert profile.device_memory == 8
        assert profile.max_touch_points == 0


class TestStealthConfig:
    """测试反检测配置."""

    def test_config_defaults(self):
        """测试默认配置."""
        config = StealthConfig()
        assert config.enabled is True
        assert config.fingerprint_preset == "chrome_windows"
        assert config.human_like is True
        assert config.noise_level == "medium"
        assert "navigator_webdriver" in config.enabled_patches
        assert "navigator_vendor" in config.enabled_patches
        assert "navigator_user_agent_data" in config.enabled_patches
        assert "navigator_max_touch_points" in config.enabled_patches
        assert "navigator_permissions" in config.enabled_patches
        assert "chrome_runtime" in config.enabled_patches

    def test_config_customization(self):
        """测试自定义配置."""
        config = StealthConfig(
            enabled=False,
            fingerprint_preset="safari_mac",
            human_like=False,
            noise_level="high",
            enabled_patches=["navigator_webdriver"],
        )
        assert config.enabled is False
        assert config.fingerprint_preset == "safari_mac"
        assert config.human_like is False
        assert config.noise_level == "high"
        assert config.enabled_patches == ["navigator_webdriver"]


class TestPresetProfiles:
    """测试预设指纹模板."""

    def test_all_presets_exist(self):
        """测试所有预设模板都存在."""
        presets = [
            "chrome_windows",
            "chrome_mac",
            "safari_mac",
            "firefox_windows",
            "firefox_mac",
            "edge_windows",
            "mobile_android",
            "mobile_ios",
        ]
        for preset in presets:
            assert preset in PRESET_PROFILES

    def test_preset_consistency(self):
        """测试预设模板的一致性."""
        for name, profile in PRESET_PROFILES.items():
            # 验证基本字段
            assert profile.user_agent
            assert profile.viewport["width"] > 0
            assert profile.viewport["height"] > 0
            assert profile.locale
            assert profile.timezone
            assert profile.platform

            # 验证 UA 和 platform 的一致性（仅桌面端）
            if "Windows" in profile.user_agent:
                assert profile.platform == "Win32"
            elif "Macintosh" in profile.user_agent and "iPhone" not in profile.user_agent:
                assert profile.platform == "MacIntel"

            # 验证 viewport 合理性
            if "mobile" in name or "Mobile" in profile.user_agent:
                assert profile.viewport["width"] < 500  # 移动端视口较小
            else:
                assert profile.viewport["width"] >= 1000  # 桌面端视口较大


class TestStealthManager:
    """测试反检测管理器."""

    def test_manager_creation(self):
        """测试创建管理器."""
        manager = StealthManager()
        assert manager._config.enabled is True
        assert manager._plan is None

    def test_build_plan_when_disabled(self):
        """测试禁用状态下的计划生成."""
        config = StealthConfig(enabled=False)
        manager = StealthManager(config)
        plan = manager.build_plan()

        assert isinstance(plan, StealthPlan)
        assert plan.init_scripts == []
        assert plan.launch_args == []

    def test_build_plan_when_enabled(self):
        """测试启用状态下的计划生成."""
        manager = StealthManager()
        plan = manager.build_plan()

        assert isinstance(plan, StealthPlan)
        assert plan.profile is not None
        assert len(plan.init_scripts) > 0
        assert len(plan.launch_args) > 0
        assert len(plan.behavior_delays) > 0

    def test_build_plan_returns_consistent_result(self):
        """测试计划生成结果一致性."""
        manager = StealthManager()
        plan1 = manager.build_plan()
        plan2 = manager.build_plan()
        # 验证两次生成的 plan 内容一致
        assert plan1.profile == plan2.profile
        assert plan1.init_scripts == plan2.init_scripts

    def test_get_profile_from_preset(self):
        """测试从预设获取指纹画像."""
        config = StealthConfig(fingerprint_preset="chrome_mac")
        manager = StealthManager(config)
        profile = manager._get_profile()

        assert profile.platform == "MacIntel"
        assert "Macintosh" in profile.user_agent

    def test_get_profile_custom(self):
        """测试使用自定义指纹画像."""
        custom = StealthProfile(user_agent="Custom UA", platform="Custom")
        manager = StealthManager(custom_profile=custom)
        profile = manager._get_profile()

        assert profile.user_agent == "Custom UA"
        assert profile.platform == "Custom"

    def test_generate_init_scripts(self):
        """测试生成初始化脚本."""
        manager = StealthManager()
        profile = manager._get_profile()
        scripts = manager._generate_init_scripts(profile)

        assert len(scripts) > 0
        # 验证包含 navigator.webdriver 隐藏脚本
        assert any("navigator" in script for script in scripts)

    def test_generate_launch_args(self):
        """测试生成启动参数."""
        manager = StealthManager()
        args = manager._generate_launch_args()

        assert "--disable-blink-features=AutomationControlled" in args

    def test_generate_behavior_delays(self):
        """测试生成行为延迟配置."""
        # 测试低噪声
        config_low = StealthConfig(noise_level="low")
        manager_low = StealthManager(config_low)
        delays_low = manager_low._generate_behavior_delays()

        assert delays_low["click"][0] < delays_low["click"][1]
        assert delays_low["click"][1] <= 0.15  # 低噪声延迟较短

        # 测试高噪声
        config_high = StealthConfig(noise_level="high")
        manager_high = StealthManager(config_high)
        delays_high = manager_high._generate_behavior_delays()

        assert delays_high["click"][1] >= 0.6  # 高噪声延迟较长

    def test_get_random_delay(self):
        """测试获取随机延迟."""
        manager = StealthManager()
        delay = manager.get_random_delay("click")

        plan = manager._plan
        min_delay, max_delay = plan.behavior_delays["click"]
        assert min_delay <= delay <= max_delay

    def test_get_random_delay_different_values(self):
        """测试随机延迟值有变化."""
        manager = StealthManager()
        delays = [manager.get_random_delay("click") for _ in range(10)]

        # 验证至少有两个不同的值
        assert len(set(delays)) > 1


class TestPatches:
    """测试反检测补丁生成."""

    def test_patch_navigator_webdriver(self):
        """测试 navigator.webdriver 隐藏补丁."""
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["navigator_webdriver"])

        assert "navigator" in script
        assert "webdriver" in script
        assert "undefined" in script

    def test_patch_navigator_plugins(self):
        """测试 navigator.plugins 模拟补丁."""
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["navigator_plugins"])

        assert "navigator" in script
        assert "plugins" in script
        assert "Chrome PDF Plugin" in script

    def test_patch_navigator_languages(self):
        """测试 navigator.languages 补丁."""
        profile = StealthProfile(user_agent="Test", locale="zh-CN")
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_languages"])

        assert "navigator" in script
        assert "languages" in script
        assert "zh-CN" in script

    def test_patch_navigator_vendor(self):
        profile = StealthProfile(user_agent=PRESET_PROFILES["chrome_windows"].user_agent)
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_vendor"])

        assert "navigator" in script
        assert "vendor" in script
        assert "Google Inc." in script

    def test_patch_navigator_platform(self):
        profile = StealthProfile(user_agent="Test", platform="Win32")
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_platform"])

        assert "navigator" in script
        assert "platform" in script
        assert "Win32" in script

    def test_patch_navigator_hardware(self):
        profile = StealthProfile(user_agent="Test", hardware_concurrency=12, device_memory=16)
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_hardware"])

        assert "hardwareConcurrency" in script
        assert "deviceMemory" in script
        assert "12" in script
        assert "16" in script

    def test_patch_navigator_max_touch_points(self):
        profile = StealthProfile(user_agent="Test", max_touch_points=5)
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_max_touch_points"])
        assert "maxTouchPoints" in script
        assert "5" in script

    def test_patch_navigator_user_agent_data(self):
        profile = PRESET_PROFILES["chrome_windows"]
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["navigator_user_agent_data"])
        assert "userAgentData" in script
        assert "brands" in script
        assert "getHighEntropyValues" in script

    def test_patch_navigator_permissions(self):
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["navigator_permissions"])
        assert "permissions" in script
        assert "notifications" in script

    def test_patch_chrome_runtime(self):
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["chrome_runtime"])
        assert "chrome" in script
        assert "runtime" in script

    def test_patch_iframe_content_window(self):
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["iframe_content_window"])
        assert "iframe" in script.lower()
        assert "contentWindow" in script

    def test_patch_media_codecs(self):
        loader = PatchLoader(StealthProfile(user_agent="Test"))
        script = loader.load_patch(PATCH_CATALOG["media_codecs"])
        assert "canPlayType" in script
        assert "video/mp4" in script

    def test_patch_webgl(self):
        """测试 WebGL 指纹补丁."""
        profile = StealthProfile(user_agent="Test", platform="Win32")
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["webgl"])

        assert "WebGLRenderingContext" in script
        assert "getParameter" in script

    def test_patch_canvas(self):
        profile = StealthProfile(user_agent="Test")
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["canvas"])

        assert "HTMLCanvasElement" in script
        assert "toDataURL" in script

    def test_patch_screen(self):
        """测试 screen 对象补丁."""
        profile = StealthProfile(
            user_agent="Test",
            viewport={"width": 1920, "height": 1080},
            color_depth=24,
            pixel_ratio=1.0,
        )
        loader = PatchLoader(profile)
        script = loader.load_patch(PATCH_CATALOG["screen"])

        assert "screen" in script
        assert "width" in script
        assert "1920" in script


class TestStealthPlan:
    """测试反检测执行计划."""

    def test_plan_creation(self):
        """测试创建执行计划."""
        profile = StealthProfile(user_agent="Test")
        plan = StealthPlan(
            profile=profile,
            init_scripts=["script1", "script2"],
            launch_args=["--arg1"],
            behavior_delays={"click": (0.1, 0.2)},
        )

        assert plan.profile.user_agent == "Test"
        assert len(plan.init_scripts) == 2
        assert plan.launch_args == ["--arg1"]
        assert plan.behavior_delays["click"] == (0.1, 0.2)


class TestNoiseLevels:
    """测试噪声级别."""

    @pytest.mark.parametrize("level", ["low", "medium", "high"])
    def test_all_noise_levels(self, level):
        """测试所有噪声级别配置."""
        config = StealthConfig(noise_level=level)
        manager = StealthManager(config)
        delays = manager._generate_behavior_delays()

        for action, (min_delay, max_delay) in delays.items():
            assert min_delay < max_delay
            assert min_delay >= 0

    def test_noise_level_affects_delays(self):
        """测试噪声级别确实影响延迟范围."""
        config_low = StealthConfig(noise_level="low")
        config_high = StealthConfig(noise_level="high")

        manager_low = StealthManager(config_low)
        manager_high = StealthManager(config_high)

        delays_low = manager_low._generate_behavior_delays()
        delays_high = manager_high._generate_behavior_delays()

        # 高噪声的最大延迟应该大于低噪声
        assert delays_high["click"][1] > delays_low["click"][1]
        assert delays_high["type"][1] > delays_low["type"][1]


class TestIntegration:
    """集成测试."""

    def test_full_workflow(self):
        """测试完整工作流程."""
        # 创建配置
        config = StealthConfig(
            fingerprint_preset="chrome_windows",
            noise_level="medium",
            enabled_patches=[
                "navigator_webdriver",
                "navigator_plugins",
                "navigator_languages",
            ],
        )

        # 创建管理器并生成计划
        manager = StealthManager(config)
        plan = manager.build_plan()

        # 验证计划完整性
        assert plan.profile.user_agent
        assert plan.profile.viewport["width"] == 1920
        assert plan.profile.locale == "zh-CN"
        assert len(plan.init_scripts) == 3  # 启用了 3 个补丁
        assert "--disable-blink-features=AutomationControlled" in plan.launch_args
        assert "click" in plan.behavior_delays

        # 验证延迟值在范围内
        delay = manager.get_random_delay("click")
        assert 0.1 <= delay <= 0.6  # medium 级别的范围


class TestScriptLoader:
    def test_available_scripts_contains_new_patches(self):
        scripts = get_available_scripts()
        assert "navigator_webdriver" in scripts
        assert "navigator_vendor" in scripts
        assert "navigator_max_touch_points" in scripts
        assert "navigator_user_agent_data" in scripts
        assert "navigator_permissions" in scripts
        assert "chrome_runtime" in scripts


class TestPatchCatalog:
    """测试 Patch Catalog 元数据结构."""

    def test_catalog_contains_all_patches(self):
        """测试目录包含所有补丁."""
        patches = list(PATCH_CATALOG.keys())
        assert len(patches) > 0
        assert "device_profile" in patches
        assert "navigator_webdriver" in patches
        assert "navigator_plugins" in patches
        assert "webgl" in patches
        assert "canvas" in patches
        assert "screen" in patches

    def test_all_patch_specs_valid(self):
        """测试所有补丁规范都有效."""
        for name, spec in PATCH_CATALOG.items():
            assert isinstance(spec, PatchSpec)
            assert spec.name == name
            assert spec.risk_level in RiskLevel.__args__
            assert all(ctx in PatchContext.__args__ for ctx in spec.contexts)
            assert isinstance(spec.default_enabled, bool)
            assert isinstance(spec.description, str)

    def test_device_profile_default_enabled(self):
        """测试 device_profile 默认启用."""
        spec = PATCH_CATALOG["device_profile"]
        assert spec.default_enabled is True

    def test_high_risk_patches_default_disabled(self):
        """测试高风险补丁默认禁用."""
        for name, spec in PATCH_CATALOG.items():
            if spec.risk_level == "high":
                assert spec.default_enabled is False, (
                    f"{name} is high risk but default_enabled=True"
                )

    def test_patch_catalog_imported(self):
        """测试 PATCH_CATALOG 可从 stealth 模块导入."""
        from stealth import PATCH_CATALOG as catalog_imported

        assert catalog_imported is PATCH_CATALOG


class TestPatchResolver:
    """测试 Patch 解析器 API."""

    def test_resolve_enabled_patches_default(self):
        """测试默认解析启用的补丁."""
        patches = resolve_enabled_patches()
        assert "device_profile" in patches
        assert "navigator_webdriver" in patches
        assert "navigator_plugins" in patches

    def test_resolve_enabled_patches_filters_high_risk(self):
        """测试过滤高风险补丁."""
        patches = resolve_enabled_patches(risk_limit="medium")
        high_risk_patches = [
            name for name, spec in PATCH_CATALOG.items() if spec.risk_level == "high"
        ]
        for patch_name in high_risk_patches:
            assert patch_name not in patches

    def test_resolve_enabled_patches_with_custom_list(self):
        """测试使用自定义补丁列表."""
        custom_list = ["navigator_webdriver", "webgl"]
        patches = resolve_enabled_patches(enabled_patches=custom_list)
        assert patches == custom_list

    def test_resolve_enabled_patches_filters_by_context(self):
        """测试根据上下文过滤."""
        main_only = resolve_enabled_patches(context="main")
        worker_patches = resolve_enabled_patches(context="worker")

        # 某些补丁只适用于 main
        assert len(main_only) >= len(worker_patches)

        # 确保所有 worker 补丁也在 main 中
        for patch in worker_patches:
            assert patch in main_only

    def test_get_available_patches(self):
        """测试获取所有可用补丁."""
        patches = get_available_patches()
        assert set(patches) == set(PATCH_CATALOG.keys())

    def test_get_patch_spec(self):
        """测试获取补丁规范."""
        spec = get_patch_spec("navigator_webdriver")
        assert spec is not None
        assert spec.name == "navigator_webdriver"
        assert spec.risk_level == "none"

    def test_get_patch_spec_nonexistent(self):
        """测试获取不存在的补丁规范."""
        spec = get_patch_spec("nonexistent_patch")
        assert spec is None

    def test_resolve_enabled_patches_maintains_catalog_order(self):
        """测试解析结果保持目录顺序."""
        patches = resolve_enabled_patches()
        catalog_order = list(PATCH_CATALOG.keys())

        for i, patch in enumerate(patches):
            if i > 0:
                current_idx = catalog_order.index(patch)
                prev_idx = catalog_order.index(patches[i - 1])
                assert current_idx > prev_idx


class TestPatchRiskGrading:
    """测试 Patch 风险分级."""

    def test_risk_levels_valid(self):
        """测试所有风险级别有效."""
        levels = [spec.risk_level for spec in PATCH_CATALOG.values()]
        valid_levels = RiskLevel.__args__
        assert all(level in valid_levels for level in levels)

    def test_high_risk_patches_identified(self):
        """测试高风险补丁被正确识别."""
        high_risk = [name for name, spec in PATCH_CATALOG.items() if spec.risk_level == "high"]
        assert "iframe_content_window" in high_risk
        assert "media_codecs" in high_risk

    def test_default_config_no_high_risk(self):
        """测试默认配置不启用高风险补丁."""
        config = StealthConfig()
        high_risk_patches = [
            name for name, spec in PATCH_CATALOG.items() if spec.risk_level == "high"
        ]
        for patch_name in high_risk_patches:
            assert patch_name not in config.enabled_patches


class TestSitePolicy:
    """测试站点策略."""

    def test_match_host_exact(self):
        """测试精确匹配主机名."""
        assert match_host("example.com", "example.com") is True
        assert match_host("example.com", "other.com") is False

    def test_match_host_wildcard(self):
        """测试通配符匹配."""
        assert match_host("www.example.com", "*.example.com") is True
        assert match_host("sub.example.com", "*.example.com") is True
        assert match_host("example.com", "*.example.com") is True
        assert match_host("www.other.com", "*.example.com") is False

    def test_match_host_wildcard_all(self):
        """测试通配符 * 匹配所有."""
        assert match_host("any.com", "*") is True
        assert match_host("example.com", "*") is True

    def test_resolve_site_policy(self):
        """测试解析站点策略."""
        policies = [
            StealthSitePolicy(
                name="policy1",
                hosts=["*.example.com"],
                enable_patches=["patch_a"],
                disable_patches=["patch_b"],
            ),
            StealthSitePolicy(
                name="policy2",
                hosts=["*.test.com"],
            ),
        ]

        policy = resolve_site_policy("https://www.example.com/page", policies)
        assert policy is not None
        assert policy.name == "policy1"

    def test_resolve_site_policy_no_match(self):
        """测试没有匹配的策略."""
        policies = [
            StealthSitePolicy(
                name="policy1",
                hosts=["*.example.com"],
            )
        ]

        policy = resolve_site_policy("https://www.other.com/page", policies)
        assert policy is None

    def test_resolve_site_policy_priority(self):
        """测试策略优先级（第一个匹配的生效）."""
        policies = [
            StealthSitePolicy(
                name="policy1",
                hosts=["*"],
                enable_patches=["patch_a"],
            ),
            StealthSitePolicy(
                name="policy2",
                hosts=["*.example.com"],
                enable_patches=["patch_b"],
            ),
        ]

        policy = resolve_site_policy("https://www.example.com/page", policies)
        assert policy.name == "policy1"

    def test_resolve_site_policy_disabled(self):
        """测试禁用的策略不匹配."""
        policies = [
            StealthSitePolicy(
                name="policy1",
                hosts=["*.example.com"],
                enabled=False,
            ),
        ]

        policy = resolve_site_policy("https://www.example.com/page", policies)
        assert policy is None

    def test_apply_site_policy_enable(self):
        """测试站点策略启用额外补丁."""
        enabled = ["patch_a", "patch_b"]
        policy = StealthSitePolicy(
            name="policy1",
            hosts=["*.example.com"],
            enable_patches=["patch_c", "patch_d"],
        )

        result = apply_site_policy(enabled, policy)
        assert "patch_c" in result
        assert "patch_d" in result
        assert "patch_a" in result
        assert "patch_b" in result

    def test_apply_site_policy_disable(self):
        """测试站点策略禁用补丁."""
        enabled = ["patch_a", "patch_b", "patch_c"]
        policy = StealthSitePolicy(
            name="policy1",
            hosts=["*.example.com"],
            disable_patches=["patch_b"],
        )

        result = apply_site_policy(enabled, policy)
        assert "patch_a" in result
        assert "patch_b" not in result
        assert "patch_c" in result

    def test_apply_site_policy_both(self):
        """测试站点策略同时启用和禁用."""
        enabled = ["patch_a", "patch_b"]
        policy = StealthSitePolicy(
            name="policy1",
            hosts=["*.example.com"],
            enable_patches=["patch_c"],
            disable_patches=["patch_b"],
        )

        result = apply_site_policy(enabled, policy)
        assert "patch_a" in result
        assert "patch_b" not in result
        assert "patch_c" in result
