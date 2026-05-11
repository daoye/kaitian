"""发布 CLI — 通过 LangGraph 智能体上传模型到发布平台。"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

router = typer.Typer(help="模型发布（LangGraph + BrowserOS 自动化）")
console = Console()


@router.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("[yellow]可用命令:[/yellow] znzmo, recall")
        raise typer.Exit(0)


# ---------------------------------------------------------------------------
# znzmo 上传
# ---------------------------------------------------------------------------

@router.command()
def znzmo(
    model_dir: str = typer.Argument(
        None,
        help="模型目录路径。若为具体模型目录（含 meta.json）则单条上传；"
             "若为根目录或省略，则进入批量/守护模式扫描子目录。",
    ),
    limit: int = typer.Option(
        20, "--limit", "-l",
        help="批量模式上传数量（守护模式忽略）",
    ),
    daemon: bool = typer.Option(
        False, "--daemon", "-d",
        help="守护模式：循环扫描并上传新模型",
    ),
    interval: int = typer.Option(
        None, "--interval", "-i",
        help="守护模式扫描间隔（分钟，覆盖配置文件）",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="跳过最终提交（测试用，提交后立即撤销）",
    ),
):
    """上传模型到知末 — 支持单条、批量和守护模式。

    单条:  kaitian publish znzmo ./data/models/3dbrute.com/Model_A
    批量:  kaitian publish znzmo --limit 10
    守护:  kaitian publish znzmo --daemon --interval 30
    """
    model_path = Path(model_dir) if model_dir else Path("data/models")

    # 判断是否为单条上传：目录下存在 meta.json
    is_single = (model_path / "meta.json").exists()

    if is_single:
        # ---- 单条上传（保持原有行为） ----
        if not model_path.exists():
            console.print(f"[red]目录不存在:[/red] {model_path}")
            raise typer.Exit(1)

        name = model_path.name
        console.print(f"[blue]知末单条上传:[/blue] {name}")

        async def run_single() -> str:
            from sites.znzmo.upload_agent import run_znzmo_upload
            return await run_znzmo_upload(str(model_path), dry_run=dry_run)

        try:
            result = asyncio.run(run_single())
            if result.startswith("失败"):
                console.print(f"[red]{result}[/red]")
                raise typer.Exit(1)
            console.print(f"[green]{result}[/green]")
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]上传异常:[/red] {e}")
            raise typer.Exit(1) from e
        return

    # ---- 批量 / 守护模式 ----
    if not model_path.exists():
        console.print(f"[red]模型根目录不存在:[/red] {model_path}")
        raise typer.Exit(1)

    from sites.znzmo.batch_uploader import UploadOrchestrator

    orchestrator = UploadOrchestrator(
        model_root=model_path,
        dry_run=dry_run,
        scan_interval_minutes=interval,
    )

    if daemon:
        console.print(
            f"[blue]知末守护模式启动[/blue] 根目录: {model_path} "
            f"间隔: {orchestrator.scan_interval_minutes} 分钟"
        )
        try:
            orchestrator.run_daemon()
        except KeyboardInterrupt:
            console.print("\n[yellow]守护模式已停止[/yellow]")
    else:
        console.print(f"[blue]知末批量上传[/blue] 根目录: {model_path} 目标: {limit} 个")
        count = orchestrator.run_batch(limit=limit)
        console.print(f"[green]完成:[/green] 成功上传 {count} 个模型")


# ---------------------------------------------------------------------------
# recall 撤销
# ---------------------------------------------------------------------------

@router.command()
def recall(
    sku_id: int = typer.Argument(..., help="要撤销的 skuId"),
):
    """撤销已提交审核的知末模型。"""
    console.print(f"[blue]撤销 skuId={sku_id}...[/blue]")

    async def run() -> str:
        from sites.znzmo.upload_agent import run_znzmo_recall
        return await run_znzmo_recall(sku_id)

    try:
        result = asyncio.run(run())
        if result.startswith("撤销失败"):
            console.print(f"[red]{result}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]{result}[/green]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]撤销异常:[/red] {e}")
        raise typer.Exit(1) from e
