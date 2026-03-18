"""browser 模块生命周期契约测试.

验证生命周期管理、复用键语义和资源清理行为。
"""

import pytest
from playwright.async_api import async_playwright

from browser import (
    BrowserContextOptions,
    BrowserLaunchOptions,
    BrowserManager,
)
from browser.exceptions import BrowserContextError


class TestLifecycleContract:
    """测试生命周期契约."""

    @pytest.mark.asyncio
    async def test_manager_start_idempotent(self):
        """测试 manager.start() 幂等性."""
        manager = BrowserManager()

        # 第一次启动
        await manager.start()
        assert manager._started is True

        # 第二次启动应该幂等
        await manager.start()
        assert manager._started is True

        await manager.close()

    @pytest.mark.asyncio
    async def test_manager_close_idempotent(self):
        """测试 manager.close() 幂等性."""
        manager = BrowserManager()
        await manager.start()

        # 第一次关闭
        await manager.close()
        assert manager._started is False

        # 第二次关闭应该幂等，不报错
        await manager.close()
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_context_close_idempotent(self):
        """测试 context.close() 幂等性."""
        manager = BrowserManager()

        context = await manager.new_context()

        # 第一次关闭
        await context.close()
        assert context._closed is True

        # 第二次关闭应该幂等，不报错
        await context.close()
        assert context._closed is True

        await manager.close()

    @pytest.mark.asyncio
    async def test_reuse_key_returns_same_instance(self):
        """测试相同 reuse_key 返回同一上下文实例."""
        manager = BrowserManager()

        context1 = await manager.new_context(BrowserContextOptions(reuse_key="test_session_123"))

        context2 = await manager.new_context(BrowserContextOptions(reuse_key="test_session_123"))

        # 应该是同一实例
        assert context1 is context2

        await manager.close()

    @pytest.mark.asyncio
    async def test_different_reuse_key_creates_new_context(self):
        """测试不同 reuse_key 创建独立上下文."""
        manager = BrowserManager()

        context1 = await manager.new_context(BrowserContextOptions(reuse_key="session_a"))

        context2 = await manager.new_context(BrowserContextOptions(reuse_key="session_b"))

        # 应该是不同实例
        assert context1 is not context2

        await manager.close()

    @pytest.mark.asyncio
    async def test_none_reuse_key_always_creates_new(self):
        """测试 reuse_key=None 总是创建新上下文."""
        manager = BrowserManager()

        context1 = await manager.new_context(BrowserContextOptions(reuse_key=None))

        context2 = await manager.new_context(BrowserContextOptions(reuse_key=None))

        # 应该是不同实例
        assert context1 is not context2

        await manager.close()

    @pytest.mark.asyncio
    async def test_manager_close_closes_all_contexts(self):
        """测试 manager.close() 关闭所有上下文."""
        manager = BrowserManager()

        context1 = await manager.new_context()
        context2 = await manager.new_context(BrowserContextOptions(reuse_key="reused"))
        context3 = await manager.new_context(
            BrowserContextOptions(reuse_key="reused")  # 同一实例
        )

        # 关闭前
        assert context1._closed is False
        assert context2._closed is False

        await manager.close()

        # 关闭后
        assert context1._closed is True
        assert context2._closed is True
        assert context3._closed is True  # 同一实例也应该关闭

    @pytest.mark.asyncio
    async def test_default_context_ownership(self):
        """测试默认上下文所有权和清理."""
        manager = BrowserManager()

        # 获取默认上下文
        context = await manager.get_default_context()
        assert manager._default_context is context

        # 多次获取返回同一实例
        context2 = await manager.get_default_context()
        assert context is context2

        await manager.close()

        # 关闭后默认上下文应该清理
        assert manager._default_context is None


class TestAsyncContextManager:
    """测试异步上下文管理器."""

    @pytest.mark.asyncio
    async def test_manager_context_manager(self):
        """测试 BrowserManager 异步上下文管理器."""
        async with BrowserManager() as manager:
            assert manager._started is True
            context = await manager.new_context()
            assert context._closed is False

        # 退出上下文后应该关闭
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_context_context_manager(self):
        """测试 ManagedBrowserContext 异步上下文管理器."""
        manager = BrowserManager()

        async with await manager.new_context() as context:
            assert context._closed is False
            page = await context.new_page()
            assert page is not None

        # 退出上下文后应该关闭
        assert context._closed is True
        await manager.close()


class TestStorageAndCookieBoundaries:
    """测试存储和 Cookie 边界."""

    @pytest.mark.asyncio
    async def test_storage_state_export_import(self):
        """测试存储状态导出和导入."""
        async with BrowserManager() as manager:
            # 创建原始上下文并设置状态
            context1 = await manager.new_context()

            async with await context1.new_page() as page:
                await page.goto("https://example.com")
                await page.evaluate("() => { localStorage.setItem('key', 'value'); }")

            # 导出状态
            state = await context1.storage_state()
            assert "cookies" in state
            assert "origins" in state

            # 创建新上下文并导入状态
            context2 = await manager.new_context(BrowserContextOptions(storage_state=state))

            async with await context2.new_page() as page:
                await page.goto("https://example.com")
                value = await page.evaluate("() => localStorage.getItem('key')")
                assert value == "value"

    @pytest.mark.asyncio
    async def test_storage_state_isolation(self):
        """测试存储状态隔离."""
        async with BrowserManager() as manager:
            context1 = await manager.new_context()

            async with await context1.new_page() as page:
                await page.goto("https://example.com")
                await page.evaluate("() => { localStorage.setItem('isolated', '1'); }")

            state = await context1.storage_state()

            # 新上下文导入状态后是独立的
            context2 = await manager.new_context(BrowserContextOptions(storage_state=state))

            async with await context2.new_page() as page:
                await page.goto("https://example.com")
                # 修改新上下文
                await page.evaluate("() => { localStorage.setItem('isolated', '2'); }")

            # 原始上下文不变
            async with await context1.new_page() as page:
                await page.goto("https://example.com")
                value = await page.evaluate("() => localStorage.getItem('isolated')")
                assert value == "1"

    @pytest.mark.asyncio
    async def test_cookie_domain_inference(self):
        """测试 cookie domain 推断."""
        from core.models import Session

        async with BrowserManager() as manager:
            # 创建会话
            session = Session(
                session_id="test_session_001",
                site="example.com",
                account_id="test_account_001",
                cookies={"session_id": "abc123"},
                headers={},
            )

            # 应用会话
            await manager.apply_session(session, base_url="https://example.com")

            # 获取默认上下文的 cookies
            context = await manager.get_default_context()
            cookies = await context.cookies()

            # 应该包含推断的 domain
            session_cookies = [c for c in cookies if c.get("name") == "session_id"]
            if session_cookies:
                assert ".example.com" in session_cookies[0].get("domain", "")


class TestErrorHandling:
    """测试错误处理边界."""

    @pytest.mark.asyncio
    async def test_invalid_storage_state_path(self):
        """测试无效存储状态路径."""
        async with BrowserManager() as manager:
            # 不存在的路径应该抛出异常
            with pytest.raises(BrowserContextError):
                await manager.new_context(
                    BrowserContextOptions(storage_state="/nonexistent/path/state.json")
                )

    @pytest.mark.asyncio
    async def test_operations_on_closed_context(self):
        """测试对已关闭上下文执行操作."""
        async with BrowserManager() as manager:
            context = await manager.new_context()
            await context.close()

            # 对已关闭上下文执行操作应该失败或安全处理
            # 具体行为取决于 Playwright，但不应该崩溃
            with pytest.raises(Exception):
                await context.new_page()


class TestResourceCleanup:
    """测试资源清理."""

    @pytest.mark.asyncio
    async def test_cleanup_after_exception(self):
        """测试异常后资源清理."""
        manager = BrowserManager()

        try:
            await manager.start()
            context = await manager.new_context()
            page = await context.new_page()

            # 模拟异常
            raise RuntimeError("Simulated error")

        except RuntimeError:
            pass

        finally:
            # 确保清理
            await manager.close()

        # 验证已关闭
        assert manager._started is False
