"""File system utility functions."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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