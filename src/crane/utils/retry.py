"""Retry and reliability utilities."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


def safe_execute(
    func: Callable[..., T],
    default: T,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    try:
        return func()
    except exceptions:
        return default
