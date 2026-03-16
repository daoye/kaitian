from core.types import LogLevel, PublishTarget, ResourceStatus, ValidationLevel


def test_resource_status_values() -> None:
    assert ResourceStatus.PENDING.value == "pending"
    assert ResourceStatus.PUBLISHED.value == "published"


def test_log_level_values() -> None:
    assert LogLevel.INFO.value == "info"
    assert LogLevel.ERROR.value == "error"


def test_validation_and_publish_values() -> None:
    assert ValidationLevel.STRICT.value == "strict"
    assert PublishTarget.REMOTE.value == "remote"
