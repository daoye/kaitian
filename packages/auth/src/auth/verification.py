import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class VerificationCodeChallenge:
    site: str
    account_id: str
    channel: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VerificationCodeProvider(Protocol):
    async def wait_for_code(self, challenge: VerificationCodeChallenge) -> str: ...


class ConsoleVerificationCodeProvider:
    async def wait_for_code(self, challenge: VerificationCodeChallenge) -> str:
        return await asyncio.to_thread(input, challenge.prompt)
