import asyncio
from pathlib import Path

import typer
from rich.console import Console

from auth import AuthManager, SessionRepository, ZnzmoAuthenticator
from auth.exceptions import AuthError, SiteNotSupportedError
from core import get_config

router = typer.Typer(help="认证与会话管理")
console = Console(stderr=True)


def _default_auth_db_path() -> Path:
    return get_config().database.path.parent / "auth.db"


def _default_headless() -> bool:
    return get_config().browser.headless


def _create_auth_manager(db_path: Path, headless: bool | None = None) -> AuthManager:
    resolved = db_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    manager = AuthManager(SessionRepository(str(resolved)))
    effective_headless = _default_headless() if headless is None else headless
    manager.register_authenticator("znzmo", ZnzmoAuthenticator(headless=effective_headless))
    return manager


def _exit_with_error(message: str, code: int) -> None:
    console.print(message)
    raise typer.Exit(code=code)


@router.command("login")
def login(
    site: str = typer.Option(..., "--site"),
    account: str = typer.Option(..., "--account"),
    mode: str = typer.Option("password", "--mode"),
    password: str | None = typer.Option(None, "--password", hide_input=True),
    sms_code: str | None = typer.Option(None, "--sms-code"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
    headless: bool = typer.Option(_default_headless(), "--headless/--no-headless"),
) -> None:
    manager = _create_auth_manager(db_path, headless=headless)
    if mode not in {"password", "sms"}:
        raise typer.BadParameter("mode 必须是 password 或 sms", param_hint="--mode")
    if mode == "password" and not password:
        raise typer.BadParameter("密码模式需要 --password", param_hint="--password")

    credentials = {"login_mode": mode}
    if mode == "password":
        credentials["username"] = account
        credentials["password"] = password
    else:
        credentials["phone"] = account
        if sms_code:
            credentials["sms_code"] = sms_code

    try:
        session = asyncio.run(manager.login(site, account, credentials))
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    typer.echo(f"登录成功: {session.site}/{session.account_id} session_id={session.session_id}")


@router.command("verify")
def verify(
    site: str = typer.Option(..., "--site"),
    account: str = typer.Option(..., "--account"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
) -> None:
    manager = _create_auth_manager(db_path)
    try:
        is_valid = asyncio.run(manager.verify(site, account))
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if not is_valid:
        _exit_with_error(f"会话无效: {site}/{account}", 10)
    typer.echo(f"会话有效: {site}/{account}")


@router.command("logout")
def logout(
    site: str = typer.Option(..., "--site"),
    account: str = typer.Option(..., "--account"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
) -> None:
    manager = _create_auth_manager(db_path)
    try:
        result = asyncio.run(manager.logout(site, account))
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if not result:
        _exit_with_error(f"登出失败: {site}/{account}", 10)
    typer.echo(f"登出成功: {site}/{account}")
