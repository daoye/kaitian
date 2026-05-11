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
    nonce: str = typer.Option(..., "--nonce",
                              help="window.nonce_download_nonce（从 BrowserOS 获取）"),
    output: str = typer.Option(..., "--output", "-o", help="保存路径"),
    site: str = typer.Option("3dbrute.com", "--site", help="站点"),
    account: str = typer.Option("default", "--account", help="账号"),
    db_path: str = typer.Option(
        None, "--db-path", help="数据库路径（默认 data/kaitian.db）"),
):
    """下载模型文件（需先通过 BrowserOS 获取 nonce）。"""
    from auth.repository import SessionRepository
    from sites.three_dbrute.download import get_archive as get_download_info

    repo = SessionRepository(db_path) if db_path else SessionRepository()
    session = repo.get_by_account(site, account)
    if not session:
        console.print("[red]未找到登录会话，请先导入 cookie[/red]")
        raise typer.Exit(1)
    resolved_nonce = _resolve_meta(
        session, "download_nonce", nonce, "download_nonce")
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

    console.print(
        f"[green]已下载:[/green] {result['path']} ({result['size']:,} bytes)")


def _resolve_meta(session, key: str, arg_value, label: str):
    """从参数或 session metadata 获取值。"""
    if arg_value:
        return arg_value
    meta = session.metadata or {}
    stored = meta.get(key)
    if stored:
        return stored
    console.print(f"[yellow]未提供 --{key}，也不在 session metadata 中[/yellow]")
    console.print(
        f"[yellow]请先执行: kaitian auth set-meta {session.site} {session.account_id} {key} <值>[/yellow]")
    return None


@router.command()
def model(
    url: str = typer.Argument(..., help="模型详情页 URL"),
    source: str = typer.Option("3dbrute", "--source", "-s", help="站点"),
    account: str = typer.Option(
        "daoye.more@gmail.com", "--account", help="账号"),
    output_dir: str = typer.Option(None, "--output", "-o", help="输出目录"),
    db_path: str = typer.Option(None, "--db-path"),
):
    """完整采集一个模型：提取 meta + 下载文件/预览图 + 后处理。"""
    from auth.repository import SessionRepository

    repo = SessionRepository(db_path) if db_path else SessionRepository()
    session = repo.get_by_account(
        source + ".com", account) or repo.get_by_account(source, account)
    if not session:
        console.print("[red]未找到登录会话，请先导入 cookie[/red]")
        raise typer.Exit(1)

    # 获取模型标题（从 URL 中提取 slug 作为临时标题）
    import urllib.parse
    slug = urllib.parse.urlparse(url).path.strip("/").split("/")[-1] or "model"

    import asyncio
    from sites.three_dbrute.batch_processor import download_model

    try:
        success = asyncio.run(download_model(
            url=url,
            title=slug,
            post_id="",
            session=session,
            site=source + ".com",
            account=account,
            output_base=output_dir or "data/models",
        ))
        if success:
            console.print(f"[bold green]完成:[/bold green] {url}")
        else:
            console.print(f"[yellow]跳过:[/yellow] {url}")
    except Exception as e:
        console.print(f"[red]失败:[/red] {e}")
        raise typer.Exit(1) from None


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

    import asyncio
    from sites.three_dbrute.batch_processor import download_model

    def process(url: str, title: str, post_id: str) -> bool | None:
        console.print(f"[blue]处理:[/blue] {title}")
        console.print(f"  URL: {url}")

        try:
            success = asyncio.run(download_model(
                url=url,
                title=title,
                post_id=post_id,
                session=session,
                site=site,
                account=account,
            ))
            if success is False:
                console.print("  [yellow]已跳过[/yellow]")
                return False
            return True
        except Exception as e:
            console.print(f"  [red]失败:[/red] {e}")
            return False

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
