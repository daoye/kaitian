import typer
from rich.console import Console

app = typer.Typer(help="KaiTian 模块化采集工具")
console = Console()

@app.command()
def hello():
    """测试命令."""
    console.print("Hello from KaiTian!")

def main():
    app()

if __name__ == "__main__":
    main()