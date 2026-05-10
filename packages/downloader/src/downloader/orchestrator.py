"""批量爬虫编排器，支持 batch 和 daemon 模式。"""

import logging
import time
from collections.abc import Callable

from core.config import get_config
from sites.three_dbrute.listing import ListingFetcher

logger = logging.getLogger(__name__)


class CrawlOrchestrator:
    """批量爬虫编排器。

    Args:
        cookies: 登录 cookie。
        process_model: 处理单个模型的回调函数，接收 (url, title, post_id)。
                        返回 True 表示成功，False 表示失败，None 表示已跳过。
        delay: 请求间隔秒数。
    """

    def __init__(
        self,
        cookies: dict[str, str],
        process_model: Callable[[str, str, str], bool | None],
        delay: float = 3.0,
    ):
        self.fetcher = ListingFetcher(cookies, delay)
        self.process_model = process_model
        self.delay = delay
        self.config = get_config().crawl

    def run_batch(self, limit: int = 20, start_page: int = 1) -> int:
        """批量模式：处理 limit 个模型后退出。返回处理数。"""
        count = 0
        for cards, _page, _total in self.fetcher.iter_pages(start=start_page):
            for card in cards:
                if count >= limit:
                    return count
                result = self.process_model(card["url"], card["title"], card["post_id"])
                if result is not None:
                    count += 1
                time.sleep(self.delay)
        return count

    def run_daemon(self) -> None:
        """守护模式：首次全量，后续增量检查。"""
        logger.info("守护模式启动，首次全量遍历...")
        self._full_scan()

        while True:
            logger.info(f"全量完成，等待 {self.config.restart_delay_hours} 小时后增量检查")
            time.sleep(self.config.restart_delay_hours * 3600)
            self._incremental_check()

    def _full_scan(self) -> None:
        """首次全量遍历所有页。"""
        for cards, page, total in self.fetcher.iter_pages():
            logger.info(f"第 {page}/{total} 页，{len(cards)} 个模型")
            for card in cards:
                self.process_model(card["url"], card["title"], card["post_id"])
                time.sleep(self.delay)

    def _incremental_check(self) -> None:
        """增量检查：只取第 1 页，有新模型则下载直到遇到已下载的停止。"""
        cards, total_pages = self.fetcher.fetch_page(1, sort_by="newest")
        if not cards:
            return

        newest_url = cards[0]["url"]
        from .repository import SiteRepository
        repo = SiteRepository()
        record = repo.get("3dbrute.com", newest_url)

        if record and record.status == "completed":
            logger.info("第 1 页最新模型已下载，无新数据")
            return

        seen_done = False
        for card in cards:
            if seen_done:
                break
            record = repo.get("3dbrute.com", card["url"])
            if record and record.status == "completed":
                seen_done = True
                continue
            self.process_model(card["url"], card["title"], card["post_id"])
            time.sleep(self.delay)
