"""Unit tests for core.wait polling helper.

Tests use deterministic time injection via _now and _sleep hooks to avoid
slow tests and ensure consistent behavior across different environments.
"""

import pytest

from core.wait import PollTimeoutError, poll_until


class TestPollUntilSuccessPath:
    """Test that poll_until returns first non-None result and stops."""

    @pytest.mark.asyncio
    async def test_sync_predicate_immediate_success(self):
        """Sync predicate returning non-None on first call should return that value."""
        result = await poll_until(lambda: 42, timeout=1.0)
        assert result == 42

    @pytest.mark.asyncio
    async def test_async_predicate_immediate_success(self):
        """Async predicate returning non-None on first call should return that value."""

        async def predicate():
            return "success"

        result = await poll_until(predicate, timeout=1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_predicate_returns_false_non_none(self):
        """Predicate returning False (non-None) should stop polling and return False."""
        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            # Return False on second call (truthy non-None)
            return False if call_count == 2 else None

        result = await poll_until(predicate, timeout=1.0, interval=0.01)
        assert result is False
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_predicate_returns_zero_non_none(self):
        """Predicate returning 0 (non-None) should stop polling and return 0."""
        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            return 0 if call_count == 3 else None

        result = await poll_until(predicate, timeout=1.0, interval=0.01)
        assert result == 0
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_calls_until_success(self):
        """Polling should continue until predicate returns non-None."""

        async def predicate():
            nonlocal attempts
            attempts += 1
            if attempts >= 5:
                return "finally_ready"
            return None

        attempts = 0
        result = await poll_until(predicate, timeout=10.0, interval=0.1)
        assert result == "finally_ready"
        assert attempts == 5

    @pytest.mark.asyncio
    async def test_returns_complex_object(self):
        """Predicate can return any non-None value, including complex objects."""

        class ComplexResult:
            def __init__(self, value: int):
                self.value = value

        def predicate():
            return ComplexResult(123)

        result = await poll_until(predicate, timeout=1.0)
        assert isinstance(result, ComplexResult)
        assert result.value == 123

    @pytest.mark.asyncio
    async def test_empty_string_non_none(self):
        """Empty string is non-None, so it stops polling and returns ''."""
        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            return "" if call_count == 2 else None

        result = await poll_until(predicate, timeout=1.0, interval=0.01)
        assert result == ""
        assert call_count == 2


class TestPollUntilTimeoutPath:
    """Test that poll_until raises PollTimeoutError when deadline is reached."""

    @pytest.mark.asyncio
    async def test_sync_predicate_always_none_raises_timeout(self):
        """Sync predicate that never returns non-None should timeout."""

        def always_none():
            return None

        with pytest.raises(PollTimeoutError) as exc_info:
            await poll_until(always_none, timeout=1.0, interval=0.01)

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_async_predicate_always_none_raises_timeout(self):
        """Async predicate that never returns non-None should timeout."""

        async def always_none():
            return None

        with pytest.raises(PollTimeoutError):
            await poll_until(always_none, timeout=1.0, interval=0.01)

    @pytest.mark.asyncio
    async def test_timeout_with_injected_time(self):
        """Timeout should work with injected time function."""

        # poll_until calls now() twice per loop iteration:
        # 1. At loop start to check timeout
        # 2. After predicate to calculate remaining sleep time

        # With 0.5s interval and 1.0s timeout:
        # - time 0.0: set deadline = 1.0 (initial now() call)
        # - Loop 1: now()=0.4 check (ok), predicate fails, now()=0.9 remaining=0.1, sleep(0.1)
        # - Loop 2: now()=1.0 check (TIMEOUT!)

        # time_values: [0.0, 0.4, 0.9, 1.0]
        time_values = [0.0, 0.4, 0.9, 1.0]

        def fake_now():
            return time_values.pop(0) if time_values else 2.0

        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            return None

        # Should timeout after 1.0s (1 predicate call at time 0.4)
        with pytest.raises(PollTimeoutError):
            await poll_until(predicate, timeout=1.0, interval=0.5, _now=fake_now)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_message_includes_duration(self):
        """Timeout error message should include configured timeout duration."""
        with pytest.raises(PollTimeoutError) as exc_info:
            await poll_until(lambda: None, timeout=5.5)

        assert "5.5" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_interval_respects_timeout(self):
        """Even with large interval, timeout should be respected."""

        # Small timeout, large interval - should timeout immediately
        with pytest.raises(PollTimeoutError):
            await poll_until(lambda: None, timeout=0.01, interval=10.0)


class TestPollUntilRetryPath:
    """Test retry_on_exception callback for handling transient errors."""

    @pytest.mark.asyncio
    async def test_retry_on_exception_true_continues_polling(self):
        """Exceptions matching retry condition should be suppressed and retried."""

        attempts = 0

        def predicate():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("transient error")
            return "success"

        def is_transient(exc):
            return "transient" in str(exc).lower()

        result = await poll_until(predicate, timeout=10.0, retry_on_exception=is_transient)
        assert result == "success"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_async_predicate_retry_on_exception(self):
        """Retry should work with async predicates."""

        attempts = 0

        async def predicate():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RuntimeError("network timeout")
            return "done"

        def is_network_timeout(exc):
            return "network" in str(exc).lower()

        result = await poll_until(predicate, timeout=10.0, retry_on_exception=is_network_timeout)
        assert result == "done"
        assert attempts == 2

    @pytest.mark.asyncio
    async def test_retry_count_respects_timeout(self):
        """Retry loop should stop at deadline even if predicate keeps failing."""

        def predicate():
            raise Exception("keeps failing")

        def always_retry(exc):
            return True

        # Fake time to control retry count
        # With 0.4s timeout and 0.1s interval:
        # - deadline = 0.4
        # - Loop 1: now()=0.05 (ok), now()=0.15 remaining=0.25, sleep(0.1)
        # - Loop 2: now()=0.25 (ok), now()=0.35 remaining=0.05, sleep(0.05)
        # - Loop 3: now()=0.48 (ok), now()=? remaining negative, sleep(0)
        # - Loop 4: now()=? (TIMEOUT)
        time_values = [0.0, 0.05, 0.15, 0.25, 0.35, 0.48]

        sleep_calls = []

        async def fake_sleep(delay):
            sleep_calls.append(delay)

        def fake_now():
            return time_values.pop(0) if time_values else 2.0

        with pytest.raises(PollTimeoutError):
            await poll_until(
                predicate,
                timeout=0.4,
                interval=0.1,
                retry_on_exception=always_retry,
                _sleep=fake_sleep,
                _now=fake_now,
            )

        # Should have made 2 sleep calls before timeout
        assert len(sleep_calls) == 2

    @pytest.mark.asyncio
    async def test_retry_false_propagates_immediately(self):
        """When retry callback returns False, exception should propagate immediately."""

        def predicate():
            raise ValueError("non-retryable error")

        def never_retry(exc):
            return False

        with pytest.raises(ValueError, match="non-retryable error"):
            await poll_until(predicate, timeout=10.0, retry_on_exception=never_retry)


class TestPollUntilPropagationPath:
    """Test that non-retryable exceptions propagate immediately."""

    @pytest.mark.asyncio
    async def test_exception_propagates_without_retry_callback(self):
        """Without retry_on_exception, all exceptions propagate immediately."""

        def predicate():
            raise RuntimeError("immediate failure")

        with pytest.raises(RuntimeError, match="immediate failure"):
            await poll_until(predicate, timeout=10.0)

    @pytest.mark.asyncio
    async def test_exception_message_preserved(self):
        """Original exception message should be preserved."""

        def predicate():
            raise ValueError("custom error message here")

        with pytest.raises(ValueError) as exc_info:
            await poll_until(predicate, timeout=10.0)

        assert str(exc_info.value) == "custom error message here"

    @pytest.mark.asyncio
    async def test_exception_type_preserved(self):
        """Original exception type should be preserved."""

        class CustomException(Exception):
            pass

        def predicate():
            raise CustomException("custom")

        with pytest.raises(CustomException):
            await poll_until(predicate, timeout=10.0)

    @pytest.mark.asyncio
    async def test_retry_callback_false_preserves_exception(self):
        """When retry returns False, original exception should propagate unchanged."""

        original_exc = ValueError("retry rejected")

        def predicate():
            raise original_exc

        def never_retry(exc):
            return False

        with pytest.raises(ValueError) as exc_info:
            await poll_until(predicate, timeout=10.0, retry_on_exception=never_retry)

        assert exc_info.value is original_exc


class TestPollUntilTestHooks:
    """Test that _sleep and _now hooks work for deterministic testing."""

    @pytest.mark.asyncio
    async def test_injected_sleep_avoids_real_waits(self):
        """Test should not wait for real time when _sleep is injected."""

        async def fake_sleep(delay):
            pass  # No actual waiting

        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            return "done" if call_count == 5 else None

        # Even with 100s interval, test completes instantly
        result = await poll_until(predicate, timeout=1000.0, interval=100.0, _sleep=fake_sleep)
        assert result == "done"
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_injected_now_controls_timeout(self):
        """Test can control when timeout occurs via _now injection."""

        # With 0.3s interval and 1.0s timeout:
        # - deadline = 1.0
        # - Loop 1: now()=0.25 (ok), now()=0.6 remaining=0.4, sleep(0.3)
        # - Loop 2: now()=0.9 (ok), now()=1.1 remaining=-0.1, sleep(0)
        # - Loop 3: now()=? (TIMEOUT)
        time_values = [0.0, 0.25, 0.6, 0.9, 1.1]

        call_count = 0

        def fake_now():
            return time_values.pop(0) if time_values else 2.0

        def predicate():
            nonlocal call_count
            call_count += 1
            return None

        with pytest.raises(PollTimeoutError):
            await poll_until(predicate, timeout=1.0, interval=0.3, _now=fake_now)

        # Should have tried 2 times before timeout
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_combined_injected_hooks(self):
        """Both _now and _sleep can work together for full control."""

        # With 0.2s interval and 1.0s timeout:
        # Need 3 predicate calls before success
        # - Loop 1: now()=0.15 (ok), call_count=1, now()=0.35, sleep(0.2)
        # - Loop 2: now()=0.55 (ok), call_count=2, now()=0.75, sleep(0.2)
        # - Loop 3: now()=0.95 (ok), call_count=3, success!
        time_values = [0.0, 0.15, 0.35, 0.55, 0.75, 0.95]
        sleep_calls = []

        async def fake_sleep(delay):
            sleep_calls.append(delay)

        def fake_now():
            return time_values.pop(0) if time_values else 2.0

        call_count = 0

        def predicate():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return "success"
            return None

        result = await poll_until(
            predicate, timeout=1.0, interval=0.2, _sleep=fake_sleep, _now=fake_now
        )
        assert result == "success"
        assert call_count == 3
        # Should have slept 2 times before success on 3rd call
        assert len(sleep_calls) == 2
