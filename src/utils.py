# src/utils.py
import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, Optional
from pathlib import Path

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

def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path

    Returns:
        Path: Path object for the directory
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def normalize_path(path: str) -> str:
    """Normalize file system path.
    
    Args:
        path: Original path

    Returns:
        str: Normalized path
    """
    return str(Path(path).resolve())

def calculate_directory_size(path: str) -> Optional[int]:
    """Calculate total size of a directory.
    
    Args:
        path: Directory path

    Returns:
        Optional[int]: Total size in bytes, None if error occurs
    """
    try:
        total_size = 0
        for entry in Path(path).rglob('*'):
            if entry.is_file():
                total_size += entry.stat().st_size
        return total_size
    except Exception as e:
        logger.error(f"Failed to calculate directory size: {str(e)}")
        return None

def format_size(size_bytes: int) -> str:
    """Format file size for display.
    
    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary.
    
    Args:
        file_path: Path to the file

    Returns:
        bool: True if file is binary, False if text
        
    Note:
        Returns True on error as a safety measure
    """
    try:
        with open(file_path, 'rb') as file:
            chunk = file.read(1024)
            # Check for null bytes or other binary characters
            text_characters = bytes([7, 8, 9, 10, 12, 13, 27]) + bytes(range(0x20, 0x100))
            return bool(chunk.translate(None, text_characters))
    except Exception as e:
        logger.error(f"Failed to check file type: {str(e)}")
        return True  # Treat as binary file for safety on error

def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate long string with ellipsis.
    
    Args:
        text: Original string
        max_length: Maximum length before truncation

    Returns:
        str: Truncated string with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."