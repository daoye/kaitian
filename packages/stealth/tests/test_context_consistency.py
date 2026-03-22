from stealth import StealthConfig, StealthManager


class DummyContext:
    def __init__(self) -> None:
        self.called = False


async def test_apply_to_context_skips_when_disabled() -> None:
    manager = StealthManager()
    context = DummyContext()

    await manager.apply_to_context(context)

    assert context.called is False


async def test_apply_to_context_uses_playwright_stealth(monkeypatch) -> None:
    called: list[object] = []

    class FakeStealth:
        async def apply_stealth_async(self, context):
            context.called = True
            called.append(context)

    class FakeModule:
        Stealth = FakeStealth

    monkeypatch.setattr("stealth.core.import_module", lambda name: FakeModule)
    manager = StealthManager(StealthConfig(enabled=True))
    context = DummyContext()

    await manager.apply_to_context(context)

    assert context.called is True
    assert called == [context]
