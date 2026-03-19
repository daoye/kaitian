import importlib
from pathlib import Path

import typer

from cli.__version__ import __version__
from cli.commands.auth import router as auth_router
from core import get_config

app = typer.Typer(help="KaiTian 模块化采集工具")
app.add_typer(auth_router, name="auth")


@app.command()
def version() -> None:
    typer.echo(f"KaiTian CLI {__version__}")


@app.command()
def doctor() -> None:
    config = get_config()
    auth_db_path = config.database.path.parent / "auth.db"
    typer.echo(f"cli_version={__version__}")
    typer.echo(f"database_path={config.database.path}")
    typer.echo(f"auth_db_path={auth_db_path}")
    typer.echo(f"browser_headless={config.browser.headless}")
    typer.echo(f"browser_timeout={config.browser.timeout}")
    for package_name in ("core", "auth", "browser", "downloader", "validator", "publisher"):
        try:
            importlib.import_module(package_name)
            status = "ok"
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
        typer.echo(f"package_{package_name}={status}")
    typer.echo(f"workspace_root={Path.cwd()}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
