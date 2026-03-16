def test_api_import():
    """测试 API 模块导入."""
    from api.main import app

    assert app is not None


def test_health_import():
    """测试健康检查路由导入."""
    from api.routers.health import router

    assert router is not None
