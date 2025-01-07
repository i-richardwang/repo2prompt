# src/nodes/cleanup.py
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any

from ..schemas import State

logger = logging.getLogger(__name__)


async def cleanup_node(state: State) -> Dict[str, Any]:
    """清理节点。

    职责：
    1. 只清理当前请求创建的资源
    2. 保持共享目录结构
    3. 安全地处理并发情况
    """
    cleaned = []

    try:
        paths_to_clean = state.get("paths_to_clean", [])

        for path in paths_to_clean:
            try:
                repo_path = Path(path)
                uuid_tmp_path = repo_path.parent

                logger.info(f"Starting cleanup of request resources...")

                # 只清理当前请求的目录
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
            "paths_to_clean": [],  # 清空待清理列表
            "cleaned_paths": cleaned  # 更新已清理列表
        }

async def _safe_cleanup_path(path: str) -> bool:
    """安全地清理指定路径。
    
    Args:
        path: 要清理的路径

    Returns:
        bool: 清理是否成功
    """
    try:
        # 验证路径合法性
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
    """检查路径是否安全。
    
    Args:
        path: 要检查的路径

    Returns:
        bool: 路径是否安全
    """
    try:
        # 转换为绝对路径
        abs_path = os.path.abspath(path)
        
        # 基本安全检查
        if not abs_path or abs_path == "/" or abs_path == "\\":
            return False
            
        # 检查路径是否包含可疑模式
        suspicious_patterns = [".", "..", "~", "@", "$", "%", "*", "?"]
        return not any(pattern in os.path.basename(abs_path) for pattern in suspicious_patterns)
        
    except Exception:
        return False