from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
_UNSET = object()


class DummySession:
    def __init__(self, site: str = "znzmo", account_id: str = "tester") -> None:
        self.site = site
        self.account_id = account_id
        self.session_id = "session-001"
        self.expires_at = None


class DummyOpenPage:
    def __init__(self) -> None:
        self.waited_events: list[str] = []

    async def wait_for_event(self, name: str) -> None:
        self.waited_events.append(name)


class DummyManager:
    def __init__(
        self,
        login_result=None,
        verify_result=True,
        refresh_result=_UNSET,
        logout_result=True,
        list_result=None,
        open_error: Exception | None = None,
    ) -> None:
        self.login_result = login_result or DummySession()
        self.verify_result = verify_result
        self.refresh_result = self.login_result if refresh_result is _UNSET else refresh_result
        self.logout_result = logout_result
        self.list_result = list_result if list_result is not None else [self.login_result]
        self.open_error = open_error
        self.login_args = None
        self.verify_args = None
        self.refresh_args = None
        self.logout_args = None
        self.list_args = None
        self.open_args = None
        self.open_page = DummyOpenPage()

    async def login(self, site, account, credentials):
        self.login_args = (site, account, credentials)
        return self.login_result

    async def verify(self, site, account):
        self.verify_args = (site, account)
        return self.verify_result

    async def refresh(self, site, account):
        self.refresh_args = (site, account)
        return self.refresh_result

    async def logout(self, site, account):
        self.logout_args = (site, account)
        return self.logout_result

    def list_sessions(self, site):
        self.list_args = (site,)
        return self.list_result

    async def open_site(self, session_id, url, browser_manager):
        self.open_args = (session_id, url, browser_manager)
        if self.open_error is not None:
            raise self.open_error
        return self.open_page


class DummyBrowserManager:
    def __init__(self):
        self.started = False
        self.closed = False

    async def start(self):
        self.started = True
        return self

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_help_shows_p0_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "doctor" in result.output
    assert "auth" in result.output


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "KaiTian CLI" in result.output


def test_doctor_command():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "cli_version=" in result.output
    assert "package_auth=" in result.output


def test_auth_login_password(monkeypatch):
    manager = DummyManager()
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--site",
            "znzmo",
            "--account",
            "tester",
            "--mode",
            "password",
            "--password",
            "secret",
        ],
    )

    assert result.exit_code == 0
    assert "登录成功" in result.output
    assert manager.login_args == (
        "znzmo",
        "tester",
        {"login_mode": "password", "username": "tester", "password": "secret"},
    )


def test_auth_login_sms(monkeypatch):
    manager = DummyManager()
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--site",
            "znzmo",
            "--account",
            "13800138000",
            "--mode",
            "sms",
        ],
    )

    assert result.exit_code == 0
    assert manager.login_args == (
        "znzmo",
        "13800138000",
        {"login_mode": "sms", "phone": "13800138000"},
    )


def test_auth_login_no_headless_passed_to_manager(monkeypatch):
    manager = DummyManager()
    captured: dict[str, object] = {}

    def fake_create_auth_manager(db_path, headless=None):
        captured["headless"] = headless
        return manager

    monkeypatch.setattr("cli.commands.auth._create_auth_manager", fake_create_auth_manager)

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--site",
            "znzmo",
            "--account",
            "13800138000",
            "--mode",
            "sms",
            "--no-headless",
        ],
    )

    assert result.exit_code == 0
    assert captured["headless"] is False


def test_auth_verify_invalid(monkeypatch):
    manager = DummyManager(verify_result=False)
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        ["auth", "verify", "--site", "znzmo", "--account", "tester"],
    )

    assert result.exit_code == 10
    assert "会话无效" in result.output


def test_auth_refresh(monkeypatch):
    manager = DummyManager(refresh_result=DummySession(account_id="tester"))
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        ["auth", "refresh", "--site", "znzmo", "--account", "tester"],
    )

    assert result.exit_code == 0
    assert "刷新成功" in result.output
    assert manager.refresh_args == ("znzmo", "tester")


def test_auth_refresh_failed(monkeypatch):
    manager = DummyManager(refresh_result=None)
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        ["auth", "refresh", "--site", "znzmo", "--account", "tester"],
    )

    assert result.exit_code == 10
    assert "刷新失败" in result.output


def test_auth_logout(monkeypatch):
    manager = DummyManager(logout_result=True)
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(
        app,
        ["auth", "logout", "--site", "znzmo", "--account", "tester"],
    )

    assert result.exit_code == 0
    assert "登出成功" in result.output


def test_auth_list_sessions(monkeypatch):
    manager = DummyManager(list_result=[DummySession(account_id="tester")])
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(app, ["auth", "list", "--site", "znzmo"])

    assert result.exit_code == 0
    assert "session_id=session-001" in result.output
    assert "account=tester" in result.output
    assert manager.list_args == ("znzmo",)


def test_auth_list_sessions_all_sites(monkeypatch):
    manager = DummyManager(
        list_result=[DummySession(site="znzmo", account_id="tester"), DummySession(site="other")]
    )
    manager.list_result[1].session_id = "session-002"
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(app, ["auth", "list"])

    assert result.exit_code == 0
    assert "session_id=session-001 site=znzmo" in result.output
    assert "session_id=session-002 site=other" in result.output
    assert manager.list_args == (None,)


def test_auth_list_sessions_empty(monkeypatch):
    manager = DummyManager(list_result=[])
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(app, ["auth", "list", "--site", "znzmo"])

    assert result.exit_code == 0
    assert "未找到会话" in result.output


def test_auth_list_sessions_empty_all_sites(monkeypatch):
    manager = DummyManager(list_result=[])
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )

    result = runner.invoke(app, ["auth", "list"])

    assert result.exit_code == 0
    assert result.output.strip() == "未找到会话"


def test_auth_open(monkeypatch):
    manager = DummyManager()
    browser_manager = DummyBrowserManager()
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )
    monkeypatch.setattr(
        "cli.commands.auth._create_browser_manager", lambda headless: browser_manager
    )

    result = runner.invoke(
        app,
        ["auth", "open", "--session-id", "session-001", "--url", "https://example.com"],
    )

    assert result.exit_code == 0
    assert "打开成功" in result.output
    assert manager.open_args == ("session-001", "https://example.com", browser_manager)
    assert browser_manager.started is True
    assert browser_manager.closed is True
    assert manager.open_page.waited_events == ["close"]


def test_auth_open_not_found(monkeypatch):
    from auth.exceptions import SessionNotFoundError

    manager = DummyManager(open_error=SessionNotFoundError("missing"))
    browser_manager = DummyBrowserManager()
    monkeypatch.setattr(
        "cli.commands.auth._create_auth_manager", lambda db_path, headless=None: manager
    )
    monkeypatch.setattr(
        "cli.commands.auth._create_browser_manager", lambda headless: browser_manager
    )

    result = runner.invoke(
        app,
        ["auth", "open", "--session-id", "missing", "--url", "https://example.com"],
    )

    assert result.exit_code == 10
    assert "会话不存在" in result.output
