from stealth import PRESET_PROFILES, StealthConfig, StealthManager, StealthProfile


def test_import() -> None:
    assert StealthManager is not None


def test_config_defaults_disabled() -> None:
    config = StealthConfig()
    assert config.enabled is False
    assert config.fingerprint_preset == "chrome_windows"


def test_build_plan_is_empty_by_default() -> None:
    manager = StealthManager()
    plan = manager.build_plan()

    assert plan.profile == PRESET_PROFILES["chrome_windows"]
    assert plan.init_scripts == []
    assert plan.launch_args == []
    assert plan.behavior_delays == {}


def test_custom_profile_is_preserved() -> None:
    profile = StealthProfile(user_agent="Custom UA", platform="Custom")
    manager = StealthManager(custom_profile=profile)

    assert manager.build_plan().profile == profile


def test_get_random_delay_returns_supported_range() -> None:
    manager = StealthManager()

    value = manager.get_random_delay("click")

    assert 0.1 <= value <= 0.3
