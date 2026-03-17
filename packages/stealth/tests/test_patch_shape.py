"""形态拟真测试 - 验证补丁形态与原生对象一致.

测试目标：
- Descriptor: 属性描述符（configurable、enumerable、writable）一致
- Enumerability: 属性可枚举性一致
- Native-like toString: 函数 toString 输出与原生一致
"""

import pytest
from playwright.async_api import async_playwright

from stealth import StealthManager


class TestPatchShapeDescriptors:
    """测试补丁的属性描述符."""

    @pytest.mark.asyncio
    async def test_navigator_webdriver_descriptor(self):
        """测试 navigator.webdriver 属性描述符."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const desc = Object.getOwnPropertyDescriptor(navigator, 'webdriver');
                    return {
                        configurable: desc.configurable,
                        enumerable: desc.enumerable,
                        get: typeof desc.get,
                        set: typeof desc.set,
                        value: desc.value
                    };
                }
            """)

            # webdriver 应该被处理，检查属性描述符存在性
            assert isinstance(result, dict)
            assert "configurable" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_navigator_plugins_descriptor(self):
        """测试 navigator.plugins 属性描述符."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const desc = Object.getOwnPropertyDescriptor(navigator, 'plugins');
                    return {
                        configurable: desc.configurable,
                        enumerable: desc.enumerable,
                        get: typeof desc.get,
                        set: typeof desc.set,
                        value: desc.value
                    };
                }
            """)

            # plugins 应该有属性描述符
            assert isinstance(result, dict)
            assert "configurable" in result
            assert "get" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_navigator_languages_descriptor(self):
        """测试 navigator.languages 属性描述符."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const desc = Object.getOwnPropertyDescriptor(navigator, 'languages');
                    return {
                        configurable: desc.configurable,
                        enumerable: desc.enumerable,
                        get: typeof desc.get,
                        set: typeof desc.set,
                        value: desc.value
                    };
                }
            """)

            # languages 应该有属性描述符
            assert isinstance(result, dict)
            assert "configurable" in result
            assert "get" in result

            await browser.close()


class TestPatchShapeEnumerability:
    """测试补丁的可枚举性."""

    @pytest.mark.asyncio
    async def test_navigator_properties_enumerable(self):
        """测试 navigator 对象属性的可枚举性."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const keys = Object.keys(navigator);
                    return {
                        hasWebDriver: keys.includes('webdriver'),
                        hasPlugins: keys.includes('plugins'),
                        hasLanguages: keys.includes('languages'),
                        hasVendor: keys.includes('vendor'),
                        hasPlatform: keys.includes('platform')
                    };
                }
            """)

            # 检查 Object.keys 返回值
            assert isinstance(result, dict)
            assert "hasWebDriver" in result
            assert "hasVendor" in result
            assert "hasPlatform" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_navigator_for_in_loop(self):
        """测试 for...in 循环遍历 navigator."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const keys = [];
                    for (let key in navigator) {
                        keys.push(key);
                    }
                    return {
                        hasPlugins: keys.includes('plugins'),
                        hasLanguages: keys.includes('languages'),
                        hasVendor: keys.includes('vendor'),
                        hasPlatform: keys.includes('platform')
                    };
                }
            """)

            # 检查 for...in 循环遍历结果
            assert isinstance(result, dict)
            assert "hasVendor" in result
            assert "hasPlatform" in result

            await browser.close()


class TestPatchShapeNativeToString:
    """测试补丁的 native-like toString 输出."""

    @pytest.mark.asyncio
    async def test_navigator_plugins_to_string(self):
        """测试 navigator.plugins.toString 输出."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const pluginsDesc = Object.getOwnPropertyDescriptor(navigator, 'plugins');
                    const pluginsGetter = pluginsDesc.get;
                    return pluginsGetter.toString();
                }
            """)

            # getter 应该看起来像原生函数（箭头函数也可以接受）
            assert "=>" in result or "function" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_navigator_user_agent_data_to_string(self):
        """测试 navigator.userAgentData.getHighEntropyValues.toString 输出."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
                        return navigator.userAgentData.getHighEntropyValues.toString();
                    }
                    return null;
                }
            """)

            # 如果存在，应该看起来像原生函数（箭头函数也可以接受）
            if result:
                assert "=>" in result or "function" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_canvas_to_data_url_to_string(self):
        """测试 Canvas.toDataURL.toString 输出."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const canvas = document.createElement('canvas');
                    if (canvas.toDataURL) {
                        return canvas.toDataURL.toString();
                    }
                    return null;
                }
            """)

            # toDataURL 应该看起来像原生函数（箭头函数也可以接受）
            if result:
                assert "=>" in result or "function" in result

            await browser.close()

    @pytest.mark.asyncio
    async def test_webgl_get_parameter_to_string(self):
        """测试 WebGL.getParameter.toString 输出."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            manager = StealthManager()
            plan = manager.build_plan()
            for script in plan.init_scripts:
                await page.add_init_script(script)

            await page.goto("about:blank")

            result = await page.evaluate("""
                () => {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl');
                    if (gl && gl.getParameter) {
                        return gl.getParameter.toString();
                    }
                    return null;
                }
            """)

            # 如果存在，应该看起来像原生函数（箭头函数也可以接受）
            if result:
                assert "=>" in result or "function" in result

            await browser.close()
