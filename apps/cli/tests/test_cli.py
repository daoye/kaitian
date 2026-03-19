from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


class DummySession:
    def __init__(self, site: str = "znzmo", account_id: str = "tester") -> None:
        self.site = site
        self.account_id = account_id
        self.session_id = "session-001"


class DummyManager:
    def __init__(self, login_result=None, verify_result=True, logout_result=True) -> None:
        self.login_result = login_result or DummySession()
        self.verify_result = verify_result
        self.logout_result = logout_result
        self.login_args = None
        self.verify_args = None
        self.logout_args = None

    async def login(self, site, account, credentials):
        self.login_args = (site, account, credentials)
        return self.login_result

    async def verify(self, site, account):
        self.verify_args = (site, account)
        return self.verify_result

    async def logout(self, site, account):
        self.logout_args = (site, account)
        return self.logout_result


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
