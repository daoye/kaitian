"""3dbrute 批量下载 — 封装站点特定逻辑。"""

import asyncio
import urllib.parse
from contextlib import suppress
from pathlib import Path

from auth.repository import SessionRepository
from core.types import WorkflowStatus, WorkflowStep
from downloader.crawler import crawl_detail, save_meta
from downloader.downloader import (
    convert_previews,
    download_preview,
    extract_archive,
    update_archive_path,
)
from downloader.repository import RecordRepository

from .download_auto import download_with_nonce


async def download_model(
    url: str,
    title: str,
    post_id: str,
    session,
    site: str = "3dbrute.com",
    account: str = "daoye.more@gmail.com",
    output_base: str = "data/models",
) -> bool:
    """下载单个模型：提取 meta + 下载文件/预览图 + 后处理。

    Returns:
        True: 成功
        False: 失败（非免费或其他可跳过原因）
    """
    rec = RecordRepository()
    record = rec.get(site, url)
    if record:
        if record.status == WorkflowStatus.COMPLETED:
            return False
        if record.status == WorkflowStatus.RUNNING:
            return False

    safe_name = title.replace("/", "_").replace(":", "").replace(" ", "_")[:100]
    base = Path(f"{output_base}/{site}/{urllib.parse.quote(safe_name, safe='_')}")
    for sub in ["originals", "previews"]:
        (base / sub).mkdir(parents=True, exist_ok=True)

    try:
        meta = crawl_detail(site.split(".")[0] if "." in site else site, url, cookies=session.cookies)
    except Exception as e:
        rec.set(site, url, step=WorkflowStep.FAILED, name=title, status=WorkflowStatus.FAILED)
        raise RuntimeError(f"meta 提取失败: {e}")

    if meta.get("license") != "free":
        rec.set(site, url, step=WorkflowStep.COMPLETED, name=title, status=WorkflowStatus.COMPLETED)
        return False

    save_meta(meta, base)

    for i, p in enumerate(meta.get("previews", [])):
        img_url = p.get("url", "")
        if not img_url:
            continue
        ext = img_url.rsplit(".", 1)[-1].split("?")[0]
        out = base / "previews" / f"{title}_{i+1:02d}.{ext}"
        if not out.exists():
            with suppress(Exception):
                download_preview(img_url, str(out))

    file_url = meta.get("files", [{}])[0].get("archive", {}).get("url", "")
    post_id_val = meta.get("product_id", "")
    if file_url and post_id_val:
        placeholder = base / "originals" / f"{post_id_val}.bin"
        try:
            await download_with_nonce(
                file_url, post_id_val, session.cookies, str(placeholder),
                site=site, account=account,
            )
        except Exception as e:
            rec.set(site, url, step=WorkflowStep.FAILED, name=title, status=WorkflowStatus.FAILED)
            raise RuntimeError(f"下载失败: {e}")

    update_archive_path(str(base))
    extract_archive(str(base))
    convert_previews(str(base))

    rec.set(site, url, step=WorkflowStep.COMPLETED, name=title, status=WorkflowStatus.COMPLETED)
    return True
