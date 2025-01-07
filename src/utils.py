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
    """异步操作超时装饰器。
    
    为异步函数添加超时限制，超过时间限制抛出 TimeoutError。

    Args:
        seconds: 超时时间（秒）

    Returns:
        装饰后的异步函数

    Raises:
        TimeoutError: 操作超时时抛出
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
    """确保目录存在，如果不存在则创建。
    
    Args:
        path: 目录路径

    Returns:
        Path: 目录路径对象
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def normalize_path(path: str) -> str:
    """规范化路径。
    
    Args:
        path: 原始路径

    Returns:
        str: 规范化后的路径
    """
    return str(Path(path).resolve())

def calculate_directory_size(path: str) -> Optional[int]:
    """计算目录总大小。
    
    Args:
        path: 目录路径

    Returns:
        Optional[int]: 总大小（字节），出错返回 None
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
    """格式化文件大小显示。
    
    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def is_binary_file(file_path: str) -> bool:
    """检查是否为二进制文件。
    
    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为二进制文件
    """
    try:
        with open(file_path, 'rb') as file:
            chunk = file.read(1024)
            # 检查是否包含空字节或其他二进制字符
            text_characters = bytes([7, 8, 9, 10, 12, 13, 27]) + bytes(range(0x20, 0x100))
            return bool(chunk.translate(None, text_characters))
    except Exception as e:
        logger.error(f"Failed to check file type: {str(e)}")
        return True  # 出错时安全起见当作二进制文件

def truncate_string(text: str, max_length: int = 100) -> str:
    """截断长字符串。
    
    Args:
        text: 原始字符串
        max_length: 最大长度

    Returns:
        str: 截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."