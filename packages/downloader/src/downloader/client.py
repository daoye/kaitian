"""HTTP 客户端，用于直接从网站抓取页面（不依赖浏览器）。"""


import httpx

# 模拟浏览器 User-Agent，避免被屏蔽
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def build_client(
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> httpx.Client:
    """创建一个预配置的 httpx 客户端。

    Args:
        cookies: 可选的登录 cookie，从 auth 模块获取。
        headers: 额外的请求头。
        timeout: 请求超时秒数。
    """
    merged_headers = dict(_DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)

    return httpx.Client(
        cookies=cookies or {},
        headers=merged_headers,
        timeout=timeout,
        follow_redirects=True,
    )


def fetch_page(
    url: str,
    cookies: dict[str, str] | None = None,
    client: httpx.Client | None = None,
) -> str:
    """获取页面 HTML。

    优先使用传入的 client（可复用连接池），否则临时创建。

    Raises:
        httpx.HTTPStatusError: 非 2xx 状态码。
        httpx.RequestError: 网络错误。
    """
    if client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text

    with build_client(cookies=cookies) as c:
        resp = c.get(url)
        resp.raise_for_status()
        return resp.text
