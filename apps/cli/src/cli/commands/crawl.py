"""爬虫 CLI — 通过 HTTP 直接提取模型元数据，不依赖浏览器。"""

import json
from pathlib import Path

import typer
from downloader.crawler import crawl_detail, save_meta
from downloader.parsers import _PARSERS
from rich.console import Console

router = typer.Typer(help="模型爬虫（HTTP 直连，非浏览器）")
console = Console()


@router.command()
def detail(
    source: str = typer.Option("3dbrute", "--source", "-s", help="站点名称"),
    url: str = typer.Argument(..., help="模型详情页 URL"),
    output: str = typer.Option(None, "--output", "-o", help="保存目录（可选）"),
):
    """爬取模型详情页，提取完整元数据。"""
    try:
        meta = crawl_detail(source=source, url=url)
    except Exception as e:
        console.print(f"[red]请求失败:[/red] {e}")
        raise typer.Exit(1) from None

    console.print_json(json.dumps(meta, ensure_ascii=False))

    if output:
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = save_meta(meta, out_dir)
        console.print(f"[green]已保存:[/green] {path}")


@router.command()
def download(
    file_url: str = typer.Option(..., "--file-url", help="data-file-urls"),
    post_id: str = typer.Option(..., "--post-id", help="data-order-id"),
    nonce: str = typer.Option(..., "--nonce", help="window.nonce_download_nonce（从 BrowserOS 获取）"),
    output: str = typer.Option(..., "--output", "-o", help="保存路径"),
    site: str = typer.Option("3dbrute.com", "--site", help="站点"),
    account: str = typer.Option("default", "--account", help="账号"),
    db_path: str = typer.Option(None, "--db-path", help="数据库路径（默认 data/kaitian.db）"),
):
    """下载模型文件（需先通过 BrowserOS 获取 nonce）。"""
    from auth.repository import SessionRepository
    from sites.three_dbrute.download import get_archive as get_download_info

    repo = SessionRepository(db_path) if db_path else SessionRepository()
    session = repo.get_by_account(site, account)
    if not session:
        console.print("[red]未找到登录会话，请先导入 cookie[/red]")
        raise typer.Exit(1)
    resolved_nonce = _resolve_meta(session, "download_nonce", nonce, "download_nonce")
    if not resolved_nonce:
        raise typer.Exit(1)

    try:
        result = get_download_info(
            file_url=file_url,
            post_id=post_id,
            nonce=resolved_nonce,
            cookies=session.cookies,
            output_path=output,
        )
    except Exception as e:
        console.print(f"[red]下载失败:[/red] {e}")
        raise typer.Exit(1) from None

    console.print(f"[green]已下载:[/green] {result['path']} ({result['size']:,} bytes)")


def _resolve_meta(session, key: str, arg_value, label: str):
    """从参数或 session metadata 获取值。"""
    if arg_value:
        return arg_value
    meta = session.metadata or {}
    stored = meta.get(key)
    if stored:
        return stored
    console.print(f"[yellow]未提供 --{key}，也不在 session metadata 中[/yellow]")
    console.print(f"[yellow]请先执行: kaitian auth set-meta {session.site} {session.account_id} {key} <值>[/yellow]")
    return None


@router.command()
def model(
    url: str = typer.Argument(..., help="模型详情页 URL"),
    source: str = typer.Option("3dbrute", "--source", "-s", help="站点"),
    nonce: str = typer.Option(None, "--nonce", help="window.nonce_download_nonce（从 BrowserOS 获取）"),
    file_url: str = typer.Option(None, "--file-url", help="data-file-urls"),
    post_id: str = typer.Option(None, "--post-id", help="data-order-id"),
    account: str = typer.Option("daoye.more@gmail.com", "--account", help="账号"),
    output_dir: str = typer.Option(None, "--output", "-o", help="输出目录"),
    db_path: str = typer.Option(None, "--db-path"),
):
    """完整采集一个模型：提取 meta + 下载文件/预览图 + 后处理。

    nonce 自动从 auth.db session metadata 读取，也可通过 --nonce 覆盖。
    首次使用需：
        1. BrowserOS 打开网站
        2. 执行 window.nonce_download_nonce 获取 nonce
        3. kaitian auth set-nonce <值>
    """
    from auth.repository import SessionRepository
    from downloader.crawler import crawl_detail, save_meta
    from downloader.downloader import download_preview
    from sites.three_dbrute.download import get_archive as get_download_info

    repo = SessionRepository(db_path) if db_path else SessionRepository()
    session = repo.get_by_account(source + ".com", account) or repo.get_by_account(source, account)
    if not session:
        console.print("[red]未找到登录会话，请先导入 cookie[/red]")
        raise typer.Exit(1)
    resolved_nonce = _resolve_meta(session, "download_nonce", nonce, "download_nonce")
    if not resolved_nonce:
        raise typer.Exit(1)

    # 1. 提取 meta
    console.print(f"[blue]提取 meta:[/blue] {url}")
    meta = crawl_detail(source=source, url=url, cookies=session.cookies)
    model_name = meta["name"].replace("/", "_").replace(":", "").strip() or meta["slug"]
    console.print(f"  name: {model_name}")

    # 2. 创建目录
    base = Path(output_dir or f"data/models/{source}.com/{model_name}")
    for sub in ["originals", "previews"]:
        (base / sub).mkdir(parents=True, exist_ok=True)

    # 3. 保存 meta.json
    save_meta(meta, base)
    console.print(f"  meta: {base / 'meta.json'}")

    # 4. 下载预览图（HTTP 直连，无需 auth）
    previews_dir = base / "previews"
    for i, p in enumerate(meta.get("previews", [])):
        img_url = p.get("url", "")
        if not img_url:
            continue
        ext = img_url.rsplit(".", 1)[-1].split("?")[0]
        out = previews_dir / f"{model_name}_{i+1:02d}.{ext}"
        if out.exists():
            console.print(f"  preview {i+1}: 已存在，跳过")
            continue
        try:
            r = download_preview(img_url, str(out))
            console.print(f"  [green]preview {i+1}:[/green] {r['size']:,} bytes")
        except Exception as e:
            console.print(f"  [red]preview {i+1} 失败:[/red] {e}")

    # 5. 下载主文件（需 nonce）
    if resolved_nonce and file_url and post_id:
        archive_dir = base / "originals"
        archive_dir.mkdir(parents=True, exist_ok=True)
        placeholder = archive_dir / f"{post_id}.bin"
        console.print(f"[blue]下载文件:[/blue] {file_url[:60]}...")
        result = get_download_info(
            file_url=file_url, post_id=post_id, nonce=resolved_nonce,
            cookies=session.cookies, output_path=str(placeholder),
        )
        console.print(f"  [green]已下载:[/green] {result['path']} ({result['size']:,} bytes)")

    # 6. 后处理
    model_dir = str(base)
    from downloader.downloader import convert_previews, extract_archive, update_archive_path

    update_archive_path(model_dir)
    extract_archive(model_dir)
    convert_previews(model_dir)

    # 7. 记录
    from downloader.repository import SiteRepository
    record_repo = SiteRepository(db_path) if db_path else SiteRepository()
    record_repo.set(source + ".com", url, step="completed", name=model_name)
    console.print("  [green]记录已更新[/green]")
    console.print(f"[bold green]完成:[/bold green] {model_name}")


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
    from core import get_config
    from downloader.orchestrator import CrawlOrchestrator

    repo = SessionRepository()
    session = repo.get_by_account(site, account)
    if not session:
        console.print("[red]未找到登录会话[/red]")
        raise typer.Exit(1)

    resolved_delay = delay if delay is not None else get_config().crawl.request_delay_seconds

    def process(url: str, title: str, post_id: str) -> bool | None:
        from downloader.repository import SiteRepository
        rec = SiteRepository()
        r = rec.get(site, url)
        if r:
            if r.status == "completed":
                return None
            if r.status == "running":
                return None

        console.print(f"[blue]处理:[/blue] {title}")
        console.print(f"  URL: {url}")

        nonce = (session.metadata or {}).get("download_nonce")
        if not nonce:
            console.print("  [yellow]无 download_nonce[/yellow]")
            return False

        import urllib.parse
        from pathlib import Path

        from downloader.crawler import crawl_detail, save_meta
        from downloader.downloader import (
            convert_previews,
            download_preview,
            extract_archive,
            update_archive_path,
        )
        from sites.three_dbrute.download import get_archive as get_download_info

        safe_name = title.replace("/", "_").replace(":", "").replace(" ", "_")[:100]
        base = Path(f"data/models/{site}/{urllib.parse.quote(safe_name, safe='_')}")
        for sub in ["originals", "previews"]:
            (base / sub).mkdir(parents=True, exist_ok=True)

        try:
            meta = crawl_detail(site.split(".")[0] if "." in site else site, url, cookies=session.cookies)
        except Exception as e:
            console.print(f"  [red]meta 提取失败:[/red] {e}")
            rec.set(site, url, step="failed", name=title, status="failed")
            return False

        if meta.get("license") != "free":
            console.print(f"  [yellow]非免费模型:[/yellow] {meta.get('license')}")
            rec.set(site, url, step="completed", name=title, status="completed")
            return False

        save_meta(meta, base)

        from contextlib import suppress

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
        if nonce and file_url and post_id_val:
            placeholder = base / "originals" / f"{post_id_val}.bin"
            try:
                get_download_info(file_url, post_id_val, nonce, session.cookies, str(placeholder))
            except Exception as e:
                console.print(f"  [red]下载失败:[/red] {e}")
                rec.set(site, url, step="failed", name=title, status="failed")
                return False

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


@router.command()
def agent(
    task: str = typer.Argument(..., help="任务名 (text_clean)"),
    model_dir: str = typer.Option(None, "--model-dir", "-d", help="模型目录路径"),
):
    """运行 LangGraph 智能体任务。"""
    import asyncio

    if task != "text_clean":
        console.print(f"[red]未知任务: {task}[/red]")
        console.print("可用: text_clean")
        raise typer.Exit(1)

    if not model_dir:
        console.print("[red]text_clean 需要 --model-dir 参数[/red]")
        raise typer.Exit(1)

    from agent.tasks.text_clean import run_text_clean

    console.print(f"[blue]运行任务:[/blue] {task}")
    try:
        result = asyncio.run(run_text_clean(model_dir))
        console.print(result)
    except Exception as e:
        console.print(f"[red]任务失败:[/red] {e}")
        raise typer.Exit(1) from e


@router.command()
def postprocess(
    model_dir: str = typer.Argument(..., help="模型目录路径"),
    skip_extract: bool = typer.Option(False, "--skip-extract", help="跳过解压"),
    skip_convert: bool = typer.Option(False, "--skip-convert", help="跳过图片转换"),
):
    """后处理：更新 archive.path → 解压 → 转换预览图格式。"""
    from downloader.downloader import convert_previews, extract_archive, update_archive_path

    update_archive_path(model_dir)
    if not skip_extract:
        extract_archive(model_dir)
    if not skip_convert:
        convert_previews(model_dir)


@router.command()
def sites():
    """列出所有已注册的站点解析器。"""
    for name in _PARSERS:
        console.print(f"  {name}")
    console.print(f"\n共 {len(_PARSERS)} 个站点")
