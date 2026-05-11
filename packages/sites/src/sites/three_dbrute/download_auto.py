"""3dbrute.com 下载辅助 — 自动处理 nonce 获取。"""

from pathlib import Path

from auth.repository import SessionRepository


async def download_with_nonce(
    file_url: str,
    post_id: str,
    cookies: dict[str, str],
    output_path: str | Path,
    site: str = "3dbrute.com",
    account: str = "daoye.more@gmail.com",
    timeout: int | None = None,
) -> dict:
    """下载模型文件，自动获取 nonce（如果需要）。"""
    from .download import get_archive

    # 检查 nonce
    repo = SessionRepository()
    session = repo.get_by_account(site, account)
    nonce = (session.metadata or {}).get("download_nonce") if session else None

    if not nonce:
        # 自动获取 nonce
        from .agent import run_get_nonce
        result = await run_get_nonce(site=site, account=account)
        if result.startswith("失败"):
            raise RuntimeError(f"无法获取 download_nonce: {result}")

        # 重新读取 session
        session = repo.get_by_account(site, account)
        nonce = (session.metadata or {}).get("download_nonce") if session else None
        if not nonce:
            raise RuntimeError("保存 nonce 后仍无法读取")

    return get_archive(file_url, post_id, nonce, cookies, output_path, timeout)
