from pathlib import Path

from core.config import ConfigManager


def test_load_pyproject_tool_config() -> None:
    config = ConfigManager().load_config(Path("/Users/js6j/demos/kaitian/pyproject.toml"))
    assert config.browser.timeout == 30000
    assert config.browser.headless is True
