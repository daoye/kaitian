"""3dbrute.com 文件下载 — 通过 AJAX 获取 presigned URL 后 HTTP 下载。"""

import re
from pathlib import Path

import httpx
from downloader.client import build_client


def get_archive(
    file_url: str,
    post_id: str,
    nonce: str,
    cookies: dict[str, str],
    output_path: str | Path,
    timeout: int | None = None,
) -> dict:
    """获取模型文件并保存到本地。

    通过 AJAX record_free_download 获取 presigned S3 URL，然后用 HTTP 下载。
    """
    from core import get_config

    download_timeout = timeout or get_config().download.timeout_seconds

    client = build_client(cookies=cookies)
    resp = client.post("https://3dbrute.com/wp-admin/admin-ajax.php", data={
        "action": "record_free_download",
        "file_url": file_url, "nonce": nonce, "post_id": post_id, "is_direct_link": "false",
    })
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"获取下载链接失败: {data}")

    presigned_url = data["data"]["presigned_url"]
    m = re.search(r"/([^/]+\.\w+)(?:\?|$)", presigned_url)
    filename = m.group(1) if m else Path(output_path).name

    output_path = Path(output_path).parent / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", presigned_url, follow_redirects=True, timeout=download_timeout) as stream:
        stream.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in stream.iter_bytes(chunk_size=8192):
                f.write(chunk)

    return {"path": str(output_path), "size": output_path.stat().st_size}
