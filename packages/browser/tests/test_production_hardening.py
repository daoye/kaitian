"""生产场景硬化测试.

验证并发、稳定性、资源限制等生产级场景。
"""

import asyncio

import pytest

from browser import BrowserContextOptions, BrowserLaunchOptions, BrowserManager
from browser.exceptions import BrowserContextError


class TestConcurrencyAndRaceConditions:
    """测试并发和竞态条件."""

    @pytest.mark.asyncio
    async def test_concurrent_context_creation_with_same_reuse_key(self):
        """测试并发创建相同 reuse_key 的上下文."""
        async with BrowserManager() as manager:
            # 并发创建多个相同 reuse_key 的上下文
            tasks = [
                manager.new_context(BrowserContextOptions(reuse_key="shared")) for _ in range(5)
            ]
            contexts = await asyncio.gather(*tasks)

            # 所有任务应该返回同一实例
            first = contexts[0]
            for ctx in contexts[1:]:
                assert ctx is first

    @pytest.mark.asyncio
    async def test_context_limit_enforced(self):
        """测试上下文数量限制生效."""
        async with BrowserManager(BrowserLaunchOptions(max_contexts=3)) as manager:
            # 创建 3 个上下文（应该成功）
            ctx1 = await manager.new_context()
            ctx2 = await manager.new_context()
            ctx3 = await manager.new_context()

            # 第 4 个应该失败
            with pytest.raises(BrowserContextError) as exc_info:
                await manager.new_context()

            assert "max contexts limit reached" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_limit_resets_after_close(self):
        """测试关闭后上下文限制重置."""
        async with BrowserManager(BrowserLaunchOptions(max_contexts=2)) as manager:
            # 创建 2 个上下文
            ctx1 = await manager.new_context()
            ctx2 = await manager.new_context()

            # 关闭一个
            await ctx1.close()

            # 现在可以创建新的
            ctx3 = await manager.new_context()
            assert ctx3 is not None


class TestResourceCleanupAfterInterruption:
    """测试中断后资源清理."""

    @pytest.mark.asyncio
    async def test_cleanup_after_exception_during_context_creation(self):
        """测试上下文创建异常后的资源清理."""
        manager = BrowserManager()

        try:
            await manager.start()
            # 故意创建大量上下文触发限制
            async with BrowserManager(BrowserLaunchOptions(max_contexts=1)) as limited_manager:
                ctx1 = await limited_manager.new_context()

                # 这应该失败
                with pytest.raises(BrowserContextError):
                    await limited_manager.new_context()

        finally:
            await manager.close()

        # 验证 manager 已完全关闭
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_double_close_is_safe(self):
        """测试双关关闭是安全的."""
        manager = BrowserManager()
        await manager.start()

        ctx = await manager.new_context()
        await ctx.close()

        # 多次关闭不应报错
        await ctx.close()
        await ctx.close()

        await manager.close()
        await manager.close()


class TestLongRunningStability:
    """测试长时运行稳定性."""

    @pytest.mark.asyncio
    async def test_repeated_create_close_cycles(self):
        """测试反复创建关闭循环."""
        async with BrowserManager() as manager:
            # 进行 10 轮创建/关闭
            for i in range(10):
                ctx = await manager.new_context()
                page = await ctx.new_page()
                await page.goto("about:blank")
                await ctx.close()

    @pytest.mark.asyncio
    async def test_repeated_reused_context_acquire_release(self):
        """测试复用上下文的反复获取释放."""
        async with BrowserManager() as manager:
            reuse_key = "stable_session"

            for i in range(10):
                # 获取上下文
                ctx = await manager.new_context(BrowserContextOptions(reuse_key=reuse_key))

                # 使用
                page = await ctx.new_page()
                await page.goto("about:blank")

                # 注意：对于复用的上下文，我们不应该关闭它
                # 这里只是验证反复获取同一上下文是稳定的

            # 最终关闭所有
            await manager.close()


class TestInvalidInputs:
    """测试无效输入处理."""

    @pytest.mark.asyncio
    async def test_invalid_cookie_shape(self):
        """测试无效 cookie 形状."""
        async with BrowserManager() as manager:
            context = await manager.new_context()

            # 缺少必需字段的 cookie 应该失败
            with pytest.raises(Exception):
                await context.add_cookies([{"name": "test"}])  # 缺少 value 和 domain

    @pytest.mark.asyncio
    async def test_invalid_storage_state_structure(self):
        """测试无效 storage_state 结构."""
        async with BrowserManager() as manager:
            # 无效的结构应该失败
            invalid_state = {"invalid": "structure"}

            # Playwright 可能会接受或失败，但不应崩溃
            try:
                ctx = await manager.new_context(BrowserContextOptions(storage_state=invalid_state))
                await ctx.close()
            except Exception as e:
                # 应该抛出有意义的异常
                assert "storage" in str(e).lower() or "state" in str(e).lower()


class TestTimeoutBehavior:
    """测试超时行为."""

    @pytest.mark.asyncio
    async def test_launch_timeout_respected(self):
        """测试启动超时被尊重."""
        # 使用极短的超时应该快速失败
        manager = BrowserManager(BrowserLaunchOptions(timeout_ms=1))

        with pytest.raises(Exception):
            await manager.start()

    @pytest.mark.asyncio
    async def test_page_creation_timeout(self):
        """测试页面创建超时."""
        async with BrowserManager() as manager:
            # 使用极短的页面创建超时
            context = await manager.new_context(BrowserContextOptions(page_creation_timeout_ms=1))

            # 应该超时
            with pytest.raises(Exception) as exc_info:
                await context.new_page()

            assert "timed out" in str(exc_info.value).lower()


class TestRetryBehavior:
    """测试重试行为（间接测试）."""

    @pytest.mark.asyncio
    async def test_successful_start_after_transient_failure(self):
        """测试瞬态失败后成功启动."""
        # 正常启动应该成功（内部有重试机制）
        async with BrowserManager() as manager:
            assert manager._started is True
            ctx = await manager.new_context()
            assert ctx is not None
