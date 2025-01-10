"""Utility functions package."""
import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from .fs import (
    ensure_directory,
    normalize_path,
    calculate_directory_size,
    format_size,
    is_binary_file,
)
from .text import truncate_string

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")

def async_timeout(seconds: int = 10) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for adding timeout to async operations.
    
    Adds a timeout limit to async functions, raising TimeoutError if exceeded.

    Args:
        seconds: Timeout duration in seconds

    Returns:
        Decorated async function

    Raises:
        TimeoutError: When operation exceeds timeout limit
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
        return wrapper
    return decorator

__all__ = [
    'async_timeout',
    'ensure_directory',
    'normalize_path',
    'calculate_directory_size',
    'format_size',
    'is_binary_file',
    'truncate_string',
]
