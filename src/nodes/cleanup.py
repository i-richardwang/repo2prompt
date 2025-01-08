# src/nodes/cleanup.py
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any

from ..schemas import State

logger = logging.getLogger(__name__)


async def cleanup_node(state: State) -> Dict[str, Any]:
    """Cleanup node.

    Responsibilities:
    1. Only clean resources created by the current request
    2. Maintain shared directory structure
    3. Safely handle concurrent operations
    """
    cleaned = []

    try:
        paths_to_clean = state.get("paths_to_clean", [])

        for path in paths_to_clean:
            try:
                repo_path = Path(path)
                uuid_tmp_path = repo_path.parent

                logger.info(f"Starting cleanup of request resources...")

                # Only clean the current request directory
                if await _safe_cleanup_path(str(uuid_tmp_path)):
                    logger.info(f"Successfully cleaned request directory: {uuid_tmp_path}")
                    cleaned.append(str(uuid_tmp_path))
                else:
                    logger.warning(f"Failed to clean request directory: {uuid_tmp_path}")

            except Exception as e:
                logger.error(f"Error cleaning path {path}: {str(e)}")

    except Exception as e:
        logger.error(f"Cleanup process failed: {str(e)}")
        raise

    finally:
        return {
            "paths_to_clean": [],  # Clear the cleanup list
            "cleaned_paths": cleaned  # Update cleaned list
        }

async def _safe_cleanup_path(path: str) -> bool:
    """Safely clean up the specified path.
    
    Args:
        path: Path to clean up

    Returns:
        bool: Whether cleanup was successful
    """
    try:
        # Validate path safety
        if not _is_safe_path(path):
            logger.warning(f"Unsafe path detected, skipping: {path}")
            return False
            
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=False)
        else:
            logger.warning(f"Path does not exist: {path}")
            return False
            
        return True
        
    except PermissionError:
        logger.error(f"Permission denied when cleaning: {path}")
        return False
    except Exception as e:
        logger.error(f"Error cleaning path {path}: {str(e)}")
        return False

def _is_safe_path(path: str) -> bool:
    """Check if the path is safe.
    
    Args:
        path: Path to check

    Returns:
        bool: Whether the path is safe
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Basic safety checks
        if not abs_path or abs_path == "/" or abs_path == "\\":
            return False
            
        # Check for suspicious patterns
        suspicious_patterns = [".", "..", "~", "@", "$", "%", "*", "?"]
        return not any(pattern in os.path.basename(abs_path) for pattern in suspicious_patterns)
        
    except Exception:
        return False