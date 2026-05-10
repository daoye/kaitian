# 批量爬虫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现 `kaitian crawl batch` 命令，支持批处理和守护模式自动下载免费模型。

**Architecture:** ListingFetcher 通过 AJAX `apply_custom_filters` 端点获取免费模型列表；CrawlOrchestrator 遍历页和 URL，调用现有 `crawl model` 逻辑处理每个模型；通过 `kaitian record` 实现去重和中断恢复。

**Tech Stack:** Python 3.12, httpx, BeautifulSoup, typer, SQLite (kaitian record)

---

### Task 1: ListingFetcher

**Files:**
- Create: `packages/downloader/src/downloader/listing.py`

**Responsibility:** 从首页提取 nonce → AJAX 分页获取免费模型列表 → 返回模型 URL 列表。

- [ ] **Step 1: Create listing.py with ListingFetcher class**

```python
"""通过 AJAX apply_custom_filters 端点获取免费模型列表。"""

import re
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .client import build_client


class ListingFetcher:
    """免费模型列表获取器。

    用法:
        fetcher = ListingFetcher(cookies={...})
        for page_cards in fetcher.iter_pages(start=1, sort_by="newest"):
            for card in page_cards:
                print(card["url"])
    """

    AJAX_URL = "https://3dbrute.com/wp-admin/admin-ajax.php"

    def __init__(self, cookies: dict[str, str], delay: float = 3.0):
        self.client = build_client(cookies=cookies, headers={
            "Referer": "https://3dbrute.com/?type=free",
            "X-Requested-With": "XMLHttpRequest",
        })
        self.delay = delay
        self.nonce = self._fetch_nonce()

    def _fetch_nonce(self) -> str:
        """从首页提取 apply_custom_filters_nonce。"""
        r = self.client.get("https://3dbrute.com/?type=free")
        m = re.search(r'apply_custom_filters_nonce["\']\s*:\s*["\']([^"\']+)', r.text)
        if not m:
            raise RuntimeError("无法提取 apply_custom_filters_nonce")
        return m.group(1)

    def fetch_page(self, page: int = 1, sort_by: str = "newest") -> list[dict]:
        """获取指定页的模型卡片列表。"""
        r = self.client.post(self.AJAX_URL, data={
            "action": "apply_custom_filters",
            "paged": str(page),
            "types[]": "free",
            "sort-by": sort_by,
            "apply_custom_filters_nonce": self.nonce,
        })
        data = r.json()
        html = data["data"]["posts"]
        soup = BeautifulSoup(html, "html.parser")

        cards = []
        for c in soup.select(".thumbnail-item-wrapper"):
            link = c.select_one("a.ajax-load-post")
            title = c.select_one(".thumbnail-title")
            fmt = c.select_one(".formats")
            typ = c.select_one(".type")
            cards.append({
                "post_id": c.get("data-post-id"),
                "url": link.get("href") if link else "",
                "title": title.text.strip() if title else "",
                "format": fmt.text.strip() if fmt else "",
                "type": typ.text.strip() if typ else "",
            })

        # 提取总页数
        last_link = soup.select_one("a.last")
        total_pages = 1
        if last_link:
            m = re.search(r'paged=(\d+)', last_link.get("href", ""))
            if m:
                total_pages = int(m.group(1))

        return cards, total_pages

    def iter_pages(self, start: int = 1, sort_by: str = "newest"):
        """遍历所有页，逐个 yield 页面卡片列表。"""
        _cards, total_pages = self.fetch_page(start, sort_by)
        for p in range(start, total_pages + 1):
            cards, _ = self.fetch_page(p, sort_by)
            yield cards, p, total_pages
            if p < total_pages:
                time.sleep(self.delay)
```

- [ ] **Step 2: Verify no syntax errors**

Run: `uv run ruff check packages/downloader/src/downloader/listing.py`
Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add packages/downloader/src/downloader/listing.py
git commit -m "feat: add ListingFetcher for AJAX model listing"
```

---

### Task 2: CrawlOrchestrator

**Files:**
- Create: `packages/downloader/src/downloader/orchestrator.py`

**Responsibility:** 编排批量下载流程：遍历列表、检查记录、调用 crawl model 下载、处理 daemon 循环。

- [ ] **Step 1: Create orchestrator.py**

```python
"""批量爬虫编排器，支持 batch 和 daemon 模式。"""

import logging
import time
from typing import Callable, Optional

from core.config import get_config
from .listing import ListingFetcher

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
        process_model: Callable,
        delay: float = 3.0,
    ):
        self.fetcher = ListingFetcher(cookies, delay)
        self.process_model = process_model
        self.delay = delay
        self.config = get_config().crawl

    def run_batch(self, limit: int = 20, start_page: int = 1) -> int:
        """批量模式：处理 limit 个模型后退出。返回处理数。"""
        count = 0
        for cards, page, total in self.fetcher.iter_pages(start=start_page):
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

        # 有新模型，从第 1 页开始下载
        seen_done = False
        for card in cards:
            if seen_done:
                break
            record = repo.get("3dbrute.com", card["url"])
            if record and record.status == "completed":
                seen_done = True
                continue
            result = self.process_model(card["url"], card["title"], card["post_id"])
            time.sleep(self.delay)
```

- [ ] **Step 2: Verify syntax**

Run: `uv run ruff check packages/downloader/src/downloader/orchestrator.py`
Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add packages/downloader/src/downloader/orchestrator.py
git commit -m "feat: add CrawlOrchestrator for batch/daemon mode"
```

---

### Task 3: Add `batch` CLI command

**Files:**
- Modify: `apps/cli/src/cli/commands/crawl.py` (add batch command)

- [ ] **Step 1: Add batch command**

在 `crawl.py` 底部、`sites` 命令前添加：

```python
@router.command()
def batch(
    limit: int = typer.Option(20, "--limit", "-l", help="批处理数量（daemon 模式下忽略）"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="守护模式"),
    start_page: int = typer.Option(1, "--page", "-p", help="起始页码"),
    delay: float = typer.Option(None, "--delay", help="请求间隔秒数（覆盖配置）"),
    site: str = typer.Option("3dbrute.com", "--site"),
    account: str = typer.Option("daoye.more@gmail.com", "--account"),
):
    """批量下载免费模型。"""
    from auth.repository import SessionRepository
    from downloader.orchestrator import CrawlOrchestrator
    from core import get_config

    repo = SessionRepository()
    session = repo.get_by_account(site, account)
    if not session:
        console.print("[red]未找到登录会话[/red]")
        raise typer.Exit(1)

    resolved_delay = delay if delay is not None else get_config().crawl.request_delay_seconds

    def process(url: str, title: str, post_id: str) -> bool | None:
        # 先检查记录
        from downloader.repository import SiteRepository
        rec = SiteRepository()
        r = rec.get(site, url)
        if r:
            if r.status == "completed":
                return None  # 已跳过
            if r.status == "running":
                return None  # 进行中

        console.print(f"[blue]处理:[/blue] {title}")
        console.print(f"  URL: {url}")

        nonce = (session.metadata or {}).get("download_nonce")
        if not nonce:
            console.print("  [yellow]无 download_nonce[/yellow]")
            return False

        # 获取详情页信息
        from downloader.crawler import crawl_detail, save_meta
        from downloader.downloader import convert_previews, download_preview, extract_archive, get_download_info, update_archive_path

        from pathlib import Path
        import urllib.parse

        base = Path(f"data/models/{site}/{urllib.parse.quote(title.replace('/', '_'), safe='')}")
        for sub in ["originals", "previews"]:
            (base / sub).mkdir(parents=True, exist_ok=True)

        try:
            meta = crawl_detail(url, cookies=session.cookies)
        except Exception as e:
            console.print(f"  [red]meta 提取失败:[/red] {e}")
            rec.set(site, url, step="failed", name=title, status="failed")
            return False

        # 只有免费模型才处理
        if meta.get("license") != "free":
            console.print(f"  [yellow]非免费模型:[/yellow] {meta.get('license')}")
            rec.set(site, url, step="completed", name=title, status="completed")
            return False

        save_meta(meta, base)

        # 预览图
        for i, p in enumerate(meta.get("previews", [])):
            img_url = p.get("url", "")
            if not img_url:
                continue
            ext = img_url.rsplit(".", 1)[-1].split("?")[0]
            out = base / "previews" / f"{title}_{i+1:02d}.{ext}"
            if not out.exists():
                try:
                    download_preview(img_url, str(out))
                except Exception:
                    pass

        # 下载
        file_url = meta.get("files", [{}])[0].get("archive", {}).get("url", "")
        post_id_val = meta.get("product_id", "")
        if nonce and file_url and post_id_val:
            placeholder = base / "originals" / f"{post_id_val}.bin"
            try:
                get_download_info(file_url, post_id_val, nonce, session.cookies, str(placeholder))
            except Exception as e:
                console.print(f"  [red]下载失败:[/red] {e}")
                rec.set(site, url, step="failed", name=title, status="failed")
                return False

        # 后处理
        update_archive_path(str(base))
        extract_archive(str(base))
        convert_previews(str(base))

        rec.set(site, url, step="completed", name=title, status="completed")
        return True

    orchestrator = CrawlOrchestrator(
        cookies=session.cookies,
        process_model=process,
        delay=resolved_delay,
    )

    if daemon:
        orchestrator.run_daemon()
    else:
        processed = orchestrator.run_batch(limit=limit, start_page=start_page)
        console.print(f"[green]完成:[/green] 处理 {processed} 个模型")
```

- [ ] **Step 2: Update __init__.py exports**

```python
# packages/downloader/src/downloader/__init__.py 中添加
from .listing import ListingFetcher
from .orchestrator import CrawlOrchestrator

# __all__ 中添加
"ListingFetcher",
"CrawlOrchestrator",
```

- [ ] **Step 3: Verify**

Run: `uv run ruff check packages/downloader/src/ apps/cli/src/cli/commands/crawl.py`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add packages/downloader/src/downloader/__init__.py packages/downloader/src/downloader/listing.py packages/downloader/src/downloader/orchestrator.py apps/cli/src/cli/commands/crawl.py
git commit -m "feat: implement batch crawler CLI command"
```

---

### Task 4: Quick smoke test

- [ ] **Step 1: Test CLI help**

Run: `uv run kaitian crawl batch --help`
Expected: Shows batch command with --limit, --daemon, --page, --delay options

- [ ] **Step 2: Test batch mode with 1 model**

Run: `uv run kaitian crawl batch --limit 1 --delay 1`
Expected: Processes 1 model (or skips if all are done)

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "chore: batch crawler implementation complete"
```
