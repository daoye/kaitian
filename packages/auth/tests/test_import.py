def test_import():
    """测试包是否可以正常导入."""
    from auth import __version__
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"