from importlib import import_module
import random
from typing import Any

from .types import PRESET_PROFILES, StealthConfig, StealthPlan, StealthProfile


class StealthManager:
    def __init__(
        self,
        config: StealthConfig | None = None,
        custom_profile: StealthProfile | None = None,
        site_policies: list[object] | None = None,
    ):
        self._config = config or StealthConfig()
        self._custom_profile = custom_profile
        self._site_policies = site_policies or []
        self._plan: StealthPlan | None = None

    def build_plan(
        self,
        url: str | None = None,
        context: str = "main",
    ) -> StealthPlan:
        plan = StealthPlan(profile=self._get_profile())
        self._plan = plan
        return plan

    async def apply_to_context(self, context: Any, url: str | None = None) -> None:
        if not self._config.enabled:
            return
        stealth_module = import_module("playwright_stealth")
        stealth = stealth_module.Stealth()
        await stealth.apply_stealth_async(context)

    async def apply_to_page(self, page: Any, url: str | None = None) -> None:
        return

    def get_random_delay(self, action: str) -> float:
        ranges = {
            "click": (0.1, 0.3),
            "type": (0.05, 0.15),
            "scroll": (0.2, 0.5),
            "wait": (1.0, 3.0),
        }
        lower, upper = ranges.get(action, (0.1, 0.3))
        return random.uniform(lower, upper)

    def _get_profile(self) -> StealthProfile:
        if self._custom_profile is not None:
            return self._custom_profile
        return PRESET_PROFILES[self._config.fingerprint_preset]
