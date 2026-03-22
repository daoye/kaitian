"""Async polling/wait helper for all KaiTian modules.

This module provides a reusable polling primitive that eliminates duplicated
deadline-based loops across the codebase. It handles both sync and async
predicates, configurable timeouts, retry logic, and test hooks.

Typical usage in authenticators, downloaders, validators, etc.:

    # Wait for multiple selectors to be visible
    try:
        await poll_until(
            lambda: all_visible(page, selectors),
            timeout=8.0,
            interval=0.2
        )
    except PollTimeoutError:
        raise LoginFailedError("Selectors not visible", reason="not_ready")

    # Wait for file download completion with retry on transient errors
    def is_transient(exc):
        return "network" in str(exc).lower()

    await poll_until(
        lambda: check_download_complete(filepath),
        timeout=60.0,
        retry_on_exception=is_transient
    )

The predicate returns None to continue polling; any non-None value ends
polling and is returned to caller.
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class PollTimeoutError(TimeoutError):
    """Raised when polling reaches deadline without a truthy result."""

    pass


async def poll_until(
    predicate: Callable[[], T | None | Awaitable[T | None]],
    *,
    timeout: float,
    interval: float = 0.2,
    retry_on_exception: Callable[[Exception], bool] | None = None,
    _sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    _now: Callable[[], float] | None = None,
) -> T:
    """Return first non-None predicate result or raise PollTimeoutError.

    Polls the predicate repeatedly until it returns a non-None value,
    which is then returned to the caller. If timeout is reached,
    raises PollTimeoutError.

    Supports both sync and async predicates - detected automatically.

    Args:
        predicate: Callable that returns None to continue polling, or any
            non-None value to stop and return that value. Can be sync or async.
        timeout: Maximum wait duration in seconds.
        interval: Time between predicate checks (default 0.2).
        retry_on_exception: Optional callback that receives any exception raised
            by predicate. Returns True to retry after sleeping, False to
            propagate immediately. If None (default), all exceptions propagate.
        _sleep: Test hook for injected sleep function.
        _now: Test hook for injected time function. Defaults to monotonic time.

    Returns:
        The first non-None result returned by predicate.

    Raises:
        PollTimeoutError: If timeout is reached without a non-None result.
        Exception: Any exception from predicate not handled by retry_on_exception.

    Examples:
        >>> # Sync predicate, immediate success
        >>> result = await poll_until(lambda: 42, timeout=1.0)
        >>> assert result == 42

        >>> # Async predicate with retry
        >>> def is_transient(exc):
        ...     return "network" in str(exc).lower()
        >>>
        >>> result = await poll_until(
        ...     lambda: fetch_data(),
        ...     timeout=10.0,
        ...     retry_on_exception=is_transient
        ... )

        >>> # Continue polling until non-None
        >>> counter = 0
        >>> async def predicate():
        ...     nonlocal counter
        ...     counter += 1
        ...     return None if counter < 3 else "done"
        >>>
        >>> result = await poll_until(predicate, timeout=1.0, interval=0.01)
        >>> assert result == "done"
        >>> assert counter == 3
    """
    # Use provided time function or default to monotonic time
    now = _now or asyncio.get_running_loop().time
    deadline = now() + timeout

    async def _evaluate() -> T | None:
        """Evaluate predicate, handling both sync and async cases."""
        result = predicate()
        if inspect.isawaitable(result):
            return await result
        return result

    while True:
        # Check timeout at loop start
        if now() >= deadline:
            raise PollTimeoutError(f"Polling timeout after {timeout}s")

        try:
            result = await _evaluate()
            if result is not None:
                return result
        except Exception as exc:
            if retry_on_exception is None or not retry_on_exception(exc):
                raise

        # Sleep before next check, respecting deadline
        remaining = deadline - now()
        if remaining <= 0:
            raise PollTimeoutError(f"Polling timeout after {timeout}s")
        sleep_time = min(interval, remaining)
        await _sleep(sleep_time)
