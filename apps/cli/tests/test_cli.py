def test_cli_import():
    """测试 CLI 模块导入."""
    from cli.main import app
    assert app is not None