"""爬虫编排 — 按站点选择解析器提取元数据。"""

import json
from pathlib import Path
from typing import Any

from .client import fetch_page
from .parsers import parse as parse_html


def crawl_detail(
    source: str,
    url: str,
    cookies: dict[str, str] | None = None,
) -> dict[str, Any]:
    """爬取模型详情页，返回 Meta Schema。

    通过 HTTP 获取页面 HTML，按 source 选择对应解析器。

    Args:
        source: 站点名称，如 "3dbrute"。
        url: 模型详情页 URL。
        cookies: 可选的登录 cookie。

    Returns:
        统一格式的 Meta Schema dict。
    """
    html = fetch_page(url, cookies=cookies)
    return parse_html(source, html)


def save_meta(meta: dict[str, Any], output_dir: str | Path) -> Path:
    """将 Meta Schema 保存为 JSON 文件。"""
    path = Path(output_dir) / "meta.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
