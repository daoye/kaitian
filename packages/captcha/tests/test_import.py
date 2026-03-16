"""导入测试."""

def test_import():
    from captcha import __version__
    assert __version__ == "0.1.0"
