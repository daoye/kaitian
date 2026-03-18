"""跨上下文一致性测试.

测试主页面、iframe、worker 中的指纹一致性。
"""

import pytest
from playwright.async_api import async_playwright

from stealth import (
    PATCH_CATALOG,
    StealthManager,
    resolve_enabled_patches,
)


class TestContextPatchFiltering:
    """测试不同上下文的补丁过滤."""

    def test_main_context_includes_page_patches(self):
        """测试 main 上下文包含页面级补丁."""
        patches = resolve_enabled_patches(context="main")

        assert "navigator_webdriver" in patches
        assert "navigator_plugins" in patches
        assert "webgl" in patches
        assert "canvas" in patches
        assert "screen" in patches

    def test_worker_context_excludes_page_only_patches(self):
        """测试 worker 上下文排除仅页面可用的补丁."""
        main_patches = resolve_enabled_patches(context="main")
        worker_patches = resolve_enabled_patches(context="worker")

        # Worker 应该比 main 少
        assert len(worker_patches) <= len(main_patches)

        # chrome_runtime 只在 main 可用
        if "chrome_runtime" in main_patches:
            assert "chrome_runtime" not in worker_patches

        # visual_viewport 只在 main/iframe 可用
        if "visual_viewport" in main_patches:
            assert "visual_viewport" not in worker_patches

    def test_iframe_context_matches_main(self):
        """测试 iframe 上下文与 main 基本一致（chrome_runtime 除外）."""
        main_patches = resolve_enabled_patches(context="main")
        iframe_patches = resolve_enabled_patches(context="iframe")

        # iframe 应该比 main 少（缺少 chrome_runtime）
        assert len(iframe_patches) == len(main_patches) - 1
        assert "chrome_runtime" not in iframe_patches


class TestWorkerBoundaryExplicit:
    """测试 Worker 边界显式化."""

    def test_worker_safe_patches_listed(self):
        """测试 Worker 安全补丁在 catalog 中标记."""
        worker_patches = resolve_enabled_patches(context="worker")

        # 这些补丁应该在 worker 中可用
        worker_safe = [
            "device_profile",
            "navigator_webdriver",
            "navigator_languages",
            "navigator_platform",
            "navigator_hardware",
            "navigator_max_touch_points",
            "intl",
            "canvas",
        ]

        for patch in worker_safe:
            if patch in PATCH_CATALOG:
                spec = PATCH_CATALOG[patch]
                if "worker" in spec.contexts:
                    assert patch in worker_patches, f"{patch} should be in worker patches"

    def test_page_only_patches_excluded_from_worker(self):
        """测试仅页面可用的补丁被排除在 worker 外."""
        worker_patches = resolve_enabled_patches(context="worker")

        # 这些补丁不应该在 worker 中
        page_only = ["chrome_runtime", "visual_viewport", "match_media"]

        for patch in page_only:
            if patch in PATCH_CATALOG:
                spec = PATCH_CATALOG[patch]
                if "worker" not in spec.contexts:
                    assert patch not in worker_patches, f"{patch} should not be in worker patches"


class TestStealthPlanMetadata:
    """测试 StealthPlan 策略元数据."""

    def test_plan_includes_site_policy(self):
        """测试计划包含站点策略信息."""
        from stealth import StealthSitePolicy

        policies = [
            StealthSitePolicy(
                name="test_policy",
                hosts=["*.example.com"],
                risk_limit="high",
            )
        ]

        manager = StealthManager(site_policies=policies)
        plan = manager.build_plan("https://www.example.com/page")

        assert plan.site_policy == "test_policy"
        assert plan.risk_limit == "high"

    def test_plan_includes_effective_patches(self):
        """测试计划包含实际生效的补丁列表."""
        manager = StealthManager()
        plan = manager.build_plan()

        assert len(plan.effective_patches) > 0
        assert "device_profile" in plan.effective_patches

    def test_plan_includes_context(self):
        """测试计划包含目标上下文."""
        manager = StealthManager()
        plan = manager.build_plan()

        assert plan.context == "main"

    def test_plan_without_policy_has_none_site_policy(self):
        """测试无匹配策略时 site_policy 为 None."""
        manager = StealthManager()
        plan = manager.build_plan()

        assert plan.site_policy is None
        assert plan.risk_limit == "medium"


class TestMainIframeConsistency:
    """测试主页面与 iframe 的一致性（需要浏览器）."""

    @pytest.mark.asyncio
    async def test_navigator_consistency_between_main_and_iframe(self):
        """测试主页面与 iframe 的 navigator 一致性."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()

            manager = StealthManager()
            plan = manager.build_plan()

            for script in plan.init_scripts:
                await context.add_init_script(script)

            # 创建页面
            page = await context.new_page()
            await page.goto("about:blank")

            # 获取主页面的 navigator 值
            main_values = await page.evaluate("""
                () => ({
                    webdriver: navigator.webdriver,
                    platform: navigator.platform,
                    vendor: navigator.vendor,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    maxTouchPoints: navigator.maxTouchPoints,
                    languages: navigator.languages,
                })
            """)

            # 创建 iframe
            await page.evaluate("""
                () => {
                    const iframe = document.createElement('iframe');
                    iframe.id = 'test-iframe';
                    document.body.appendChild(iframe);
                }
            """)

            # 获取 iframe 的 navigator 值
            iframe_values = await page.evaluate("""
                () => {
                    const iframe = document.getElementById('test-iframe');
                    return {
                        webdriver: iframe.contentWindow.navigator.webdriver,
                        platform: iframe.contentWindow.navigator.platform,
                        vendor: iframe.contentWindow.navigator.vendor,
                        hardwareConcurrency: iframe.contentWindow.navigator.hardwareConcurrency,
                        maxTouchPoints: iframe.contentWindow.navigator.maxTouchPoints,
                        languages: iframe.contentWindow.navigator.languages,
                    };
                }
            """)

            # 验证一致性
            assert main_values["platform"] == iframe_values["platform"]
            assert main_values["vendor"] == iframe_values["vendor"]
            assert main_values["hardwareConcurrency"] == iframe_values["hardwareConcurrency"]
            assert main_values["maxTouchPoints"] == iframe_values["maxTouchPoints"]

            await browser.close()


class TestApplyToContextWithUrl:
    """测试 apply_to_context 带 URL 参数."""

    @pytest.mark.asyncio
    async def test_apply_to_context_with_url_uses_site_policy(self):
        """测试带 URL 的 apply_to_context 使用站点策略."""
        from stealth import StealthSitePolicy

        policies = [
            StealthSitePolicy(
                name="test_site",
                hosts=["*.test.com"],
                disable_patches=["canvas"],
            )
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch()

            manager = StealthManager(site_policies=policies)

            # 创建上下文并应用带 URL 的反检测
            context = await browser.new_context()
            await manager.apply_to_context(context, "https://www.test.com/page")

            # 验证策略生效
            plan = manager._plan
            assert plan is not None
            assert plan.site_policy == "test_site"
            assert "canvas" not in plan.effective_patches

            await browser.close()

    @pytest.mark.asyncio
    async def test_apply_to_context_without_url_uses_default(self):
        """测试不带 URL 的 apply_to_context 使用默认配置."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()

            manager = StealthManager()

            context = await browser.new_context()
            await manager.apply_to_context(context)

            plan = manager._plan
            assert plan is not None
            assert plan.site_policy is None

            await browser.close()


class TestWorkerRuntime:
    """测试真实 Worker 运行时环境（需要浏览器）."""

    @pytest.mark.asyncio
    async def test_worker_navigator_consistency(self):
        """测试 Worker 中的 navigator 与主页面一致性."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()

            manager = StealthManager()
            plan = manager.build_plan()

            for script in plan.init_scripts:
                await context.add_init_script(script)

            page = await context.new_page()
            await page.goto("about:blank")

            # 创建 Blob URL Worker 并获取 navigator 值
            worker_result = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const blob = new Blob([
                            `self.onmessage = function() {
                                self.postMessage({
                                    userAgent: navigator.userAgent,
                                    platform: navigator.platform,
                                    language: navigator.language,
                                    languages: navigator.languages,
                                    hardwareConcurrency: navigator.hardwareConcurrency,
                                    maxTouchPoints: navigator.maxTouchPoints,
                                });
                            };`
                        ], { type: 'application/javascript' });

                        const workerUrl = URL.createObjectURL(blob);
                        const worker = new Worker(workerUrl);
                        worker.onmessage = (e) => resolve(e.data);
                        worker.postMessage('start');
                    });
                }
            """)

            # 获取主页面的 navigator 值
            main_values = await page.evaluate("""
                () => ({
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    languages: navigator.languages,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    maxTouchPoints: navigator.maxTouchPoints,
                })
            """)

            # 验证 Worker 与主页面的 navigator 一致性
            # 注意：Worker 和主页面应该有一致的值
            # platform 可能因机器而异，但 language 和 hardwareConcurrency 应该一致
            assert worker_result["language"] == main_values["language"]
            assert worker_result["hardwareConcurrency"] == main_values["hardwareConcurrency"]
            # platform 在 Worker 中可能是真实机器值，只要主页面和 Worker 一致即可
            # 如果 stealth 补丁生效，两者应该相同；如果没有生效，也可能是相同（都是真实值）

            await browser.close()

    @pytest.mark.asyncio
    async def test_worker_build_plan_with_context(self):
        """测试使用 worker 上下文构建计划."""
        manager = StealthManager()

        # 构建 worker 上下文的计划
        plan_worker = manager.build_plan(context="worker")

        # 构建 main 上下文的计划
        plan_main = manager.build_plan(context="main")

        # worker 应该比 main 少（chrome_runtime 等只在 main 可用的补丁）
        assert len(plan_worker.effective_patches) < len(plan_main.effective_patches)
        assert plan_worker.context == "worker"
        assert plan_main.context == "main"

    @pytest.mark.asyncio
    async def test_worker_context_excludes_page_only_patches_in_runtime(self):
        """测试 worker 上下文在运行时排除仅页面可用的补丁."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()

            # 使用 worker 上下文构建计划
            manager = StealthManager()
            plan = manager.build_plan(context="worker")

            # chrome_runtime 不应该在 worker 补丁中
            assert "chrome_runtime" not in plan.effective_patches

            for script in plan.init_scripts:
                await context.add_init_script(script)

            page = await context.new_page()
            await page.goto("about:blank")

            # 验证 Worker 中没有 chrome.runtime
            worker_result = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const blob = new Blob([
                            `self.onmessage = function() {
                                self.postMessage({
                                    hasChromeRuntime: typeof chrome !== 'undefined' && !!chrome.runtime,
                                });
                            };`
                        ], { type: 'application/javascript' });

                        const workerUrl = URL.createObjectURL(blob);
                        const worker = new Worker(workerUrl);
                        worker.onmessage = (e) => resolve(e.data);
                        worker.postMessage('start');
                    });
                }
            """)

            # Worker 中不应该有 chrome.runtime
            assert worker_result["hasChromeRuntime"] is False

            await browser.close()
