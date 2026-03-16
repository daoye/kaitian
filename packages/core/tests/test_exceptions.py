from core.exceptions import BrowserError, ConfigError, KaitianError


def test_base_exception_keeps_metadata() -> None:
    error = KaitianError("boom", error_code="E1", details={"x": 1})
    assert str(error) == "boom"
    assert error.error_code == "E1"
    assert error.details == {"x": 1}


def test_exception_hierarchy() -> None:
    assert issubclass(ConfigError, KaitianError)
    assert issubclass(BrowserError, KaitianError)
