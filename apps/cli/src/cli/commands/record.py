"""下载记录管理 CLI。

以站点为维度，记录和查询各站点下 URL 的下载进度。
供 agent 做去重和中断恢复。
"""

import typer
from core import get_config
from core.types import WorkflowStep
from downloader.repository import InvalidStepError, SiteRepository
from rich.console import Console
from rich.table import Table

router = typer.Typer(help="下载记录管理（以站点为维度）")
console = Console()

_STEP_HELP = (
    f"当前完成到的步骤，可选: {', '.join(WorkflowStep.valid_steps())}"
)


def _db_path() -> str:
    return str(get_config().database.path)


@router.command()
def set(
    site: str = typer.Argument(..., help="站点域名，如 3dbrute.com"),
    url: str = typer.Argument(..., help="模型 URL"),
    step: str = typer.Option("pending", "--step", "-s", help=_STEP_HELP),
    name: str = typer.Option(None, "--name", "-n", help="模型名称"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """在指定站点下记录或更新一个 URL 的下载进度。"""
    repo = SiteRepository(db_path)
    try:
        wf = repo.set(site=site, source_url=url, step=step, name=name)
    except InvalidStepError as e:
        console.print(f"[red]错误:[/red] {e}")
        raise typer.Exit(1) from None
    console.print(f"[green]已记录:[/green] [{site}] {wf.source_url}")
    console.print(f"  步骤: {wf.step.value}  状态: {wf.status.value}")


@router.command()
def check(
    site: str = typer.Argument(..., help="站点域名"),
    url: str = typer.Argument(..., help="模型 URL"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """查询指定站点下某个 URL 的下载进度。"""
    repo = SiteRepository(db_path)
    wf = repo.get(site, url)
    if wf is None:
        console.print(f"[yellow]未找到记录:[/yellow] [{site}] {url}")
        return
    if wf.is_done():
        console.print(f"[green]已完成:[/green] {wf.name or url}")
    else:
        console.print(f"[blue]进行中:[/blue] {wf.name or url}")
    console.print(f"  步骤: {wf.step.value}  状态: {wf.status.value}")


@router.command()
def list(
    site: str = typer.Argument(..., help="站点域名"),
    status: str = typer.Option(None, "--status", "-S", help="按状态筛选"),
    limit: int = typer.Option(100, "--limit", "-l"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """列出指定站点下的所有 URL 记录。"""
    repo = SiteRepository(db_path)
    records = repo.list(site, status=status, limit=limit)
    if not records:
        console.print(f"[yellow]站点 '{site}' 下无记录[/yellow]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("名称")
    table.add_column("URL")
    table.add_column("步骤")
    table.add_column("状态")
    for r in records:
        style = {"completed": "green", "failed": "red", "running": "blue"}.get(r.status.value, "white")
        short_url = r.source_url[:60] + "..." if len(r.source_url) > 60 else r.source_url
        table.add_row(
            r.name or "-", short_url,
            r.step.value,
            f"[{style}]{r.status.value}[/{style}]",
        )
    console.print(table)
    console.print(f"[dim]共 {len(records)} 条[/dim]")


@router.command()
def status(
    site: str = typer.Argument(..., help="站点域名"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """查看指定站点的下载进度统计。"""
    repo = SiteRepository(db_path)
    s = repo.status(site)
    if s["total"] == 0:
        console.print(f"[yellow]站点 '{site}' 暂无记录[/yellow]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("站点")
    table.add_column("总计", justify="right")
    table.add_column("已完成", justify="right")
    table.add_column("进行中", justify="right")
    table.add_column("失败", justify="right")
    table.add_column("待处理", justify="right")
    table.add_row(
        s["site"], str(s["total"]),
        f"[green]{s['completed']}[/green]",
        f"[blue]{s['running']}[/blue]",
        f"[red]{s['failed']}[/red]",
        str(s["pending"]),
    )
    console.print(table)


@router.command()
def sites(
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """列出所有有下载记录的站点。"""
    repo = SiteRepository(db_path)
    all_sites = repo.list_sites()
    if not all_sites:
        console.print("[yellow]暂无站点记录[/yellow]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("站点")
    table.add_column("总计", justify="right")
    table.add_column("已完成", justify="right")
    table.add_column("进行中", justify="right")
    table.add_column("失败", justify="right")
    for s in all_sites:
        table.add_row(
            s["site"], str(s["total"]),
            f"[green]{s['completed']}[/green]",
            f"[blue]{s['running']}[/blue]",
            f"[red]{s['failed']}[/red]",
        )
    console.print(table)


@router.command()
def done(
    site: str = typer.Argument(..., help="站点域名"),
    url: str = typer.Argument(..., help="模型 URL"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """标记指定站点下某 URL 为已完成。"""
    repo = SiteRepository(db_path)
    wf = repo.done(site, url)
    if wf:
        console.print(f"[green]已标记完成:[/green] [{site}] {url}")
    else:
        console.print(f"[yellow]未找到记录:[/yellow] [{site}] {url}")


@router.command()
def remove(
    site: str = typer.Argument(..., help="站点域名"),
    url: str = typer.Argument(..., help="模型 URL"),
    db_path: str = typer.Option(None, "--db-path", callback=lambda p: p or _db_path()),
):
    """删除指定站点下某 URL 的记录。"""
    repo = SiteRepository(db_path)
    if repo.remove(site, url):
        console.print(f"[green]已删除:[/green] [{site}] {url}")
    else:
        console.print(f"[yellow]未找到记录:[/yellow] [{site}] {url}")
