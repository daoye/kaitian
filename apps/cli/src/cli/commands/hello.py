"""Hello 命令 - 测试用."""

import typer
from rich.console import Console

router = typer.Typer()
console = Console()

@router.command()
def world():
    """打印 Hello World."""
    console.print("[bold green]Hello World from KaiTian![/bold green]")

@router.command()
def kai():
    """打印 KaiTian 信息."""
    console.print("[bold blue]KaiTian (开天) - 模块化自动化采集与搬运工具集[/bold blue]")
    console.print("Version: 0.1.0")
