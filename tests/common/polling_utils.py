"""
Polling Utilities for Asynchronous Test Validation

Provides retry/polling mechanisms for validating asynchronous operations
like event processing, database updates, and service notifications.
"""

import time
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


def poll_until(
    condition: Callable[[], T], timeout: int = 60, interval: int = 2, description: str = "condition"
) -> Optional[T]:
    """
    Poll until a condition returns a truthy value or timeout is reached.
    Uses adaptive polling: fast initially (0.5s), then normal interval.

    Args:
        condition: Function that returns truthy value when condition is met
        timeout: Maximum time to wait in seconds (default: 60)
        interval: Time between checks in seconds (default: 2)
        description: Human-readable description for logging

    Returns:
        The truthy value returned by condition, or None if timeout reached

    Example:
        # Wait for escrow to appear in database
        escrow_data = poll_until(
            lambda: get_escrow_from_db(address),
            timeout=30,
            interval=2,
            description=f"Escrow {address} in database"
        )
        if escrow_data:
            print("✅ Escrow found!")
        else:
            print("❌ Timeout - escrow not found")
    """
    start_time = time.time()
    elapsed = 0
    attempts = 0
    # Use faster polling for first 20 seconds, then normal interval
    fast_poll_duration = 20
    fast_interval = min(0.5, interval / 2)  # Faster initial polling

    while elapsed < timeout:
        attempts += 1
        try:
            result = condition()
            if result:  # Truthy check
                print(f"✅ {description} met after {elapsed:.1f}s ({attempts} attempts)")
                return result
        except Exception as e:
            # Continue polling even if condition raises exception
            if attempts % 10 == 0:  # Only print every 10th failure to reduce noise
                print(f"   Attempt {attempts} failed: {e}")

        # Adaptive interval: fast for first N seconds, then normal
        current_interval = fast_interval if elapsed < fast_poll_duration else interval
        time.sleep(current_interval)
        elapsed = time.time() - start_time

    print(f"⏱️  Timeout after {timeout}s - {description} not met ({attempts} attempts)")
    return None


def poll_until_success(
    action: Callable[[], T],
    timeout: int = 60,
    interval: int = 2,
    description: str = "action",
    expected_exceptions: tuple = (Exception,),
) -> Optional[T]:
    """
    Poll until an action succeeds (doesn't raise exception) or timeout.

    Args:
        action: Function to execute
        timeout: Maximum time to wait in seconds
        interval: Time between attempts in seconds
        description: Human-readable description
        expected_exceptions: Tuple of exceptions to catch and retry

    Returns:
        Result of action if successful, None if timeout

    Example:
        # Wait for API endpoint to return 200
        response = poll_until_success(
            lambda: requests.get(f"{url}/escrows/{address}").json(),
            timeout=30,
            description=f"GET /escrows/{address}"
        )
    """
    start_time = time.time()
    elapsed = 0
    attempts = 0
    last_exception = None

    while elapsed < timeout:
        attempts += 1
        try:
            result = action()
            print(f"✅ {description} succeeded after {elapsed:.1f}s ({attempts} attempts)")
            return result
        except expected_exceptions as e:
            last_exception = e
            # Continue polling

        time.sleep(interval)
        elapsed = time.time() - start_time

    print(f"⏱️  Timeout after {timeout}s - {description} failed ({attempts} attempts)")
    if last_exception:
        print(f"   Last error: {last_exception}")
    return None


def retry_on_failure(
    action: Callable[[], T],
    max_attempts: int = 3,
    delay: int = 1,
    backoff: float = 2.0,
    description: str = "action",
) -> Optional[T]:
    """
    Retry an action with exponential backoff.

    Args:
        action: Function to execute
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay on each retry (exponential backoff)
        description: Human-readable description

    Returns:
        Result of action if successful, None if all attempts fail

    Example:
        # Retry API call up to 3 times with exponential backoff
        result = retry_on_failure(
            lambda: api_client.post_data(data),
            max_attempts=3,
            delay=1,
            backoff=2.0,
            description="POST /api/data"
        )
    """
    current_delay = delay

    for attempt in range(1, max_attempts + 1):
        try:
            result = action()
            if attempt > 1:
                print(f"✅ {description} succeeded on attempt {attempt}")
            return result
        except Exception as e:
            if attempt == max_attempts:
                print(f"❌ {description} failed after {max_attempts} attempts")
                print(f"   Final error: {e}")
                return None
            else:
                print(f"⚠️  Attempt {attempt}/{max_attempts} failed: {e}")
                print(f"   Retrying in {current_delay}s...")
                time.sleep(current_delay)
                current_delay *= backoff

    return None


def wait_for_condition(
    check: Callable[[], bool],
    timeout: int = 30,
    interval: int = 1,
    error_message: str = "Condition not met",
) -> bool:
    """
    Wait for a boolean condition to become True.

    Args:
        check: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout

    Returns:
        True if condition met, False if timeout

    Raises:
        TimeoutError: If condition not met within timeout (can be disabled)

    Example:
        # Wait for escrow to be created
        success = wait_for_condition(
            lambda: escrow_exists(address),
            timeout=30,
            error_message=f"Escrow {address} not created"
        )
    """
    result = poll_until(
        lambda: True if check() else None,
        timeout=timeout,
        interval=interval,
        description=error_message,
    )
    return result is not None


class PollingContext:
    """
    Context manager for polling operations with automatic cleanup.

    Example:
        with PollingContext(timeout=60, description="Database update") as poller:
            result = poller.poll(lambda: get_from_db(id))
            if not result:
                pytest.fail("Database not updated")
    """

    def __init__(self, timeout: int = 60, interval: int = 2, description: str = "operation"):
        self.timeout = timeout
        self.interval = interval
        self.description = description
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        print(f"🔍 Starting polling: {self.description} (timeout: {self.timeout}s)")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            print(f"✅ Polling completed in {elapsed:.1f}s")
        else:
            print(f"❌ Polling failed after {elapsed:.1f}s")
        return False

    def poll(self, condition: Callable[[], T]) -> Optional[T]:
        """Poll for a condition within this context."""
        return poll_until(
            condition, timeout=self.timeout, interval=self.interval, description=self.description
        )
