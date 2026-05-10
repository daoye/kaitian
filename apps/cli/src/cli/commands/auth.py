import asyncio
from pathlib import Path

import typer
from auth import AuthManager, SessionRepository, ThreeDBruteAuthenticator, ZnzmoAuthenticator
from auth.exceptions import AuthError, SessionNotFoundError, SiteNotSupportedError
from browser import BrowserLaunchOptions, BrowserManager
from browser.exceptions import BrowserError
from core import get_config
from rich.console import Console

router = typer.Typer(help="认证与会话管理")
console = Console(stderr=True)


def _default_auth_db_path() -> Path:
    return Path(get_config().database.path)


def _default_headless() -> bool:
    return get_config().browser.headless


def _default_enable_cdp() -> bool:
    return get_config().browser.enable_cdp


def _default_browser_proxy() -> dict[str, str] | None:
    browser_config = get_config().browser
    if not browser_config.proxy_server:
        return None
    proxy = {"server": browser_config.proxy_server}
    if browser_config.proxy_username:
        proxy["username"] = browser_config.proxy_username
    if browser_config.proxy_password:
        proxy["password"] = browser_config.proxy_password
    if browser_config.proxy_bypass:
        proxy["bypass"] = browser_config.proxy_bypass
    return proxy


def _create_auth_manager(db_path: Path) -> AuthManager:
    """创建认证管理器（不创建 BrowserManager）."""
    resolved = db_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return AuthManager(SessionRepository(str(resolved)))


def _create_browser_manager(
    headless: bool,
    enable_cdp: bool = False,
    cdp_endpoint: str | None = None,
    cdp_port: int | None = None,
) -> BrowserManager:
    """创建浏览器管理器.

    Args:
        headless: 是否无头模式
        enable_cdp: 是否启用 CDP 模式
        cdp_endpoint: CDP 端点 URL，未指定则使用默认 http://localhost:{cdp_port}
        cdp_port: CDP 端口，未指定则使用 9222
    """
    # 处理 CDP 端口
    port = cdp_port or 9222

    # 处理 CDP 端点
    endpoint = cdp_endpoint or f"http://localhost:{port}"

    return BrowserManager(
        BrowserLaunchOptions(
            headless=headless,
            proxy=_default_browser_proxy(),
            enable_cdp=enable_cdp,
            remote_debugging_port=port,
            cdp_endpoint_url=endpoint,
        )
    )


def _register_authenticators(
    manager: AuthManager,
    headless: bool,
    enable_cdp: bool,
) -> None:
    """注册站点认证器."""
    manager.register_authenticator(
        "3dbrute",
        ThreeDBruteAuthenticator(),
    )
    manager.register_authenticator(
        "znzmo",
        ZnzmoAuthenticator(),
    )


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
    enable_cdp: bool = typer.Option(
        False, "--enable-cdp", help="启用 CDP 模式（自动检测并连接，没有则自动启动）"
    ),
    cdp_endpoint: str | None = typer.Option(
        None,
        "--cdp-endpoint",
        help="CDP 端点 URL（默认 http://localhost:9222）",
    ),
    cdp_port: int | None = typer.Option(None, "--cdp-port", help="CDP 端口（默认 9222）"),
) -> None:
    manager = _create_auth_manager(db_path)
    _register_authenticators(manager, headless, enable_cdp)

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

    async def _run() -> None:
        browser_manager = _create_browser_manager(
            headless=headless,
            enable_cdp=enable_cdp,
            cdp_endpoint=cdp_endpoint,
            cdp_port=cdp_port,
        )
        await browser_manager.start()
        try:
            session = await manager.login(site, account, credentials, browser_manager)
            return session
        finally:
            await browser_manager.close()

    try:
        session = asyncio.run(_run())
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
    headless: bool = typer.Option(_default_headless(), "--headless/--no-headless"),
    enable_cdp: bool = typer.Option(
        _default_enable_cdp(), "--enable-cdp", help="启用 CDP 模式（开启远程调试端口）"
    ),
) -> None:
    manager = _create_auth_manager(db_path)
    _register_authenticators(manager, headless, enable_cdp)

    async def _run() -> None:
        browser_manager = _create_browser_manager(headless, enable_cdp)
        await browser_manager.start()
        try:
            return await manager.verify(site, account, browser_manager)
        finally:
            await browser_manager.close()

    try:
        is_valid = asyncio.run(_run())
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if not is_valid:
        _exit_with_error(f"会话无效: {site}/{account}", 10)
    typer.echo(f"会话有效: {site}/{account}")


@router.command("refresh")
def refresh(
    site: str = typer.Option(..., "--site"),
    account: str = typer.Option(..., "--account"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
    headless: bool = typer.Option(_default_headless(), "--headless/--no-headless"),
    enable_cdp: bool = typer.Option(
        _default_enable_cdp(), "--enable-cdp", help="启用 CDP 模式（开启远程调试端口）"
    ),
) -> None:
    manager = _create_auth_manager(db_path)
    _register_authenticators(manager, headless, enable_cdp)

    async def _run() -> None:
        browser_manager = _create_browser_manager(headless, enable_cdp)
        await browser_manager.start()
        try:
            return await manager.refresh(site, account, browser_manager)
        finally:
            await browser_manager.close()

    try:
        session = asyncio.run(_run())
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except SessionNotFoundError as exc:
        _exit_with_error(f"会话不存在: {exc}", 10)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if session is None:
        _exit_with_error(f"刷新失败: {site}/{account}", 10)
    typer.echo(f"刷新成功: {session.site}/{session.account_id} session_id={session.session_id}")


@router.command("logout")
def logout(
    site: str = typer.Option(..., "--site"),
    account: str = typer.Option(..., "--account"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
    headless: bool = typer.Option(_default_headless(), "--headless/--no-headless"),
    enable_cdp: bool = typer.Option(
        _default_enable_cdp(), "--enable-cdp", help="启用 CDP 模式（开启远程调试端口）"
    ),
) -> None:
    manager = _create_auth_manager(db_path)
    _register_authenticators(manager, headless, enable_cdp)

    async def _run() -> None:
        browser_manager = _create_browser_manager(headless, enable_cdp)
        await browser_manager.start()
        try:
            return await manager.logout(site, account, browser_manager)
        finally:
            await browser_manager.close()

    try:
        result = asyncio.run(_run())
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if not result:
        _exit_with_error(f"登出失败: {site}/{account}", 10)
    typer.echo(f"登出成功: {site}/{account}")


@router.command("list")
def list_sessions(
    site: str | None = typer.Option(None, "--site"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
) -> None:
    manager = _create_auth_manager(db_path)

    try:
        sessions = manager.list_sessions(site)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)

    if not sessions:
        if site is None:
            typer.echo("未找到会话")
        else:
            typer.echo(f"未找到会话: {site}")
        return

    for session in sessions:
        expires_at = session.expires_at.isoformat() if session.expires_at else "never"
        typer.echo(
            f"session_id={session.session_id} site={session.site} account={session.account_id} expires_at={expires_at}"
        )


@router.command("import")
def import_cookies(
    cookies_dir: Path = typer.Option(
        Path("cookies"), "--cookies-dir", help="cookie 文件目录"
    ),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
):
    """从 cookies 目录批量导入站点 cookie。

    目录结构：每层子目录为一个账号，内含 {domain}.txt。

        cookies/
        ├── default/               # 账号 default
        │   ├── 3dbrute.com.txt
        │   └── znzmo.com.txt
        └── admin@example.com/     # 另一账号
            ├── 3dbrute.com.txt
            └── znzmo.com.txt

    每个 .txt 文件内容为 HTTP Cookie 头格式（一行）：
        key=value; key=value; ...
    """
    import uuid
    from datetime import datetime

    repo = SessionRepository(str(db_path.expanduser().resolve()))
    resolved = cookies_dir.expanduser().resolve()

    if not resolved.exists():
        _exit_with_error(f"cookies 目录不存在: {resolved}", 2)

    if not resolved.exists():
        _exit_with_error(f"cookies 目录不存在: {resolved}", 2)

    imported = 0
    for f in sorted(resolved.glob("*.txt")):
        site = f.stem
        lines = [line.strip() for line in f.read_text(encoding="utf-8-sig").splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        # lines 交替：账号名 → cookie行 → 账号名 → cookie行...
        for i in range(0, len(lines) - 1, 2):
            account = lines[i]
            raw_cookies = lines[i + 1]

            cookie_dict = {}
            for pair in raw_cookies.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    key, _, val = pair.partition("=")
                    cookie_dict[key.strip()] = val.strip()

            if not cookie_dict:
                continue

            from core.models import Session
            # 先删除旧会话（处理 UNIQUE(site, account_id) 约束）
            try:
                old = repo.get_by_account(site, account)
                if old:
                    repo.delete(old.session_id)
            except Exception:
                pass
            session = Session(
                session_id=uuid.uuid4().hex[:16],
                site=site,
                account_id=account,
                cookies=cookie_dict,
                metadata={
                    "source": "manual",
                    "imported_at": datetime.utcnow().isoformat(),
                },
            )
            repo.save(session)
            typer.echo(f"  {site}/{account}: {len(cookie_dict)} 个 cookie")
            imported += 1

    if imported:
        typer.echo(f"已导入 {imported} 个账号的 cookie")
    else:
        typer.echo(f"{resolved} 中无 cookie 文件")


@router.command("set-meta")
def set_meta(
    site: str = typer.Argument(..., help="站点"),
    account: str = typer.Argument(..., help="账号"),
    key: str = typer.Argument(..., help="metadata key"),
    value: str = typer.Argument(..., help="metadata value"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
):
    """设置会话的 metadata 信息，通用扩展点。

    可用于存储各站点特有的信息，如 download nonce、token 等。
    例如 3dbrute：kaitian auth set-meta 3dbrute.com user@mail.com download_nonce xxx
    """
    repo = SessionRepository(str(db_path.expanduser().resolve()))
    session = repo.get_by_account(site, account)
    if not session:
        _exit_with_error(f"未找到会话: {site}/{account}", 10)
    meta = dict(session.metadata)
    meta[key] = value
    from core.models import Session as SessModel
    updated = SessModel(
        session_id=session.session_id,
        site=session.site,
        account_id=session.account_id,
        cookies=session.cookies,
        headers=session.headers,
        expires_at=session.expires_at,
        metadata=meta,
    )
    repo.save(updated)
    typer.echo(f"  {key}={value}")


@router.command("open")
def open_site(
    session_id: str = typer.Option(..., "--session-id"),
    url: str = typer.Option(..., "--url"),
    db_path: Path = typer.Option(_default_auth_db_path(), "--db-path"),
    headless: bool = typer.Option(_default_headless(), "--headless/--no-headless"),
    enable_cdp: bool = typer.Option(
        _default_enable_cdp(), "--enable-cdp", help="启用 CDP 模式（开启远程调试端口）"
    ),
) -> None:
    manager = _create_auth_manager(db_path)
    _register_authenticators(manager, headless, enable_cdp)

    async def _run() -> None:
        browser_manager = _create_browser_manager(headless, enable_cdp)
        await browser_manager.start()
        try:
            page = await manager.open_site(session_id, url, browser_manager)
            typer.echo(f"打开成功: session_id={session_id} url={url}")
            await page.wait_for_event("close")
        finally:
            await browser_manager.close()

    try:
        asyncio.run(_run())
    except SessionNotFoundError as exc:
        _exit_with_error(f"会话不存在: {exc}", 10)
    except SiteNotSupportedError as exc:
        _exit_with_error(f"站点不支持: {exc}", 11)
    except AuthError as exc:
        _exit_with_error(f"认证失败: {exc}", 10)
    except BrowserError as exc:
        _exit_with_error(f"浏览器失败: {exc}", 20)
    except Exception as exc:
        _exit_with_error(f"未知错误: {exc}", 99)
