from pathlib import Path

from core.config import ConfigManager


def test_load_pyproject_tool_config() -> None:
    config = ConfigManager().load_config(Path("/Users/js6j/demos/kaitian/pyproject.toml"))
    assert config.browser.timeout == 30000
    assert config.browser.headless is True


def test_browser_proxy_env(monkeypatch) -> None:
    monkeypatch.setenv("KAITIAN_BROWSER_PROXY_SERVER", "http://127.0.0.1:7890")
    monkeypatch.setenv("KAITIAN_BROWSER_PROXY_USERNAME", "proxy-user")
    monkeypatch.setenv("KAITIAN_BROWSER_PROXY_PASSWORD", "proxy-pass")

    config = ConfigManager().load_config()

    assert config.browser.proxy_server == "http://127.0.0.1:7890"
    assert config.browser.proxy_username == "proxy-user"
    assert config.browser.proxy_password == "proxy-pass"
