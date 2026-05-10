"""通过 3dbrute.com AJAX 端点获取免费模型列表。"""

import re
import time

from bs4 import BeautifulSoup
from downloader.client import build_client


class ListingFetcher:
    """免费模型列表获取器。"""

    AJAX_URL = "https://3dbrute.com/wp-admin/admin-ajax.php"

    def __init__(self, cookies: dict[str, str], delay: float = 3.0):
        self.client = build_client(cookies=cookies, headers={
            "Referer": "https://3dbrute.com/?type=free",
            "X-Requested-With": "XMLHttpRequest",
        })
        self.delay = delay
        self.nonce = self._fetch_nonce()

    def _fetch_nonce(self) -> str:
        r = self.client.get("https://3dbrute.com/?type=free")
        m = re.search(r'apply_custom_filters_nonce["\']\s*:\s*["\']([^"\']+)', r.text)
        if not m:
            raise RuntimeError("无法提取 apply_custom_filters_nonce")
        return m.group(1)

    def fetch_page(self, page: int = 1, sort_by: str = "newest") -> tuple[list[dict], int]:
        r = self.client.post(self.AJAX_URL, data={
            "action": "apply_custom_filters", "paged": str(page),
            "types[]": "free", "sort-by": sort_by,
            "apply_custom_filters_nonce": self.nonce,
        })
        html = r.json()["data"]["posts"]
        soup = BeautifulSoup(html, "html.parser")
        cards = []
        for c in soup.select(".thumbnail-item-wrapper"):
            link = c.select_one("a.ajax-load-post")
            title = c.select_one(".thumbnail-title")
            cards.append({
                "post_id": c.get("data-post-id"),
                "url": link.get("href") if link else "",
                "title": title.text.strip() if title else "",
                "format": (c.select_one(".formats").text.strip() if c.select_one(".formats") else ""),
                "type": (c.select_one(".type").text.strip() if c.select_one(".type") else ""),
            })
        last_link = soup.select_one("a.last")
        total_pages = 1
        if last_link:
            m = re.search(r'paged=(\d+)', last_link.get("href", ""))
            if m:
                total_pages = int(m.group(1))
        return cards, total_pages

    def iter_pages(self, start: int = 1, sort_by: str = "newest"):
        _cards, total_pages = self.fetch_page(start, sort_by)
        for p in range(start, total_pages + 1):
            cards, _ = self.fetch_page(p, sort_by)
            yield cards, p, total_pages
            if p < total_pages:
                time.sleep(self.delay)
