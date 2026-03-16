"""discovery 核心实现."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator

from .types import DiscoveryTask, DiscoveredResource


class DiscoveryAdapter(ABC):
    """资源发现适配器接口."""

    @abstractmethod
    async def discover(
        self, task: DiscoveryTask, cursor: Optional[str] = None
    ) -> Tuple[List[DiscoveredResource], Optional[str]]:
        """发现资源.

        Args:
            task: 发现任务配置
            cursor: 分页游标

        Returns:
            (资源列表, 下一页游标)
        """
        pass

    @abstractmethod
    async def get_latest(self, limit: int = 10) -> List[DiscoveredResource]:
        """获取最新资源."""
        pass

    @abstractmethod
    def supports_monitoring(self) -> bool:
        """是否支持持续监控."""
        pass


class DiscoveryManager:
    """发现管理器."""

    def __init__(self, db_path: str = "./data/discovery.db"):
        self.db_path = db_path
        self._adapters: Dict[str, DiscoveryAdapter] = {}

    def register_adapter(self, site: str, adapter: DiscoveryAdapter) -> None:
        """注册站点适配器."""
        self._adapters[site] = adapter

    async def discover(self, task: DiscoveryTask) -> List[DiscoveredResource]:
        """执行发现任务."""
        adapter = self._adapters.get(task.site)
        if not adapter:
            raise ValueError(f"No adapter registered for site: {task.site}")

        resources, _ = await adapter.discover(task)
        return resources

    async def monitor(self, task: DiscoveryTask) -> AsyncIterator[DiscoveredResource]:
        """持续监控（异步迭代器）."""
        adapter = self._adapters.get(task.site)
        if not adapter:
            raise ValueError(f"No adapter registered for site: {task.site}")

        if not adapter.supports_monitoring():
            raise ValueError(f"Site {task.site} does not support monitoring")

        # 基本实现，实际应该使用调度器
        import asyncio

        while True:
            resources = await adapter.get_latest(limit=10)
            for resource in resources:
                yield resource
            await asyncio.sleep(task.schedule.interval_minutes * 60 if task.schedule else 300)
