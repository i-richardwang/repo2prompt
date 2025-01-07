# src/nodes/tree.py
import os
from fnmatch import fnmatch
from typing import Any, Optional

from ..schemas import State
from ..config import (
    MAX_DIRECTORY_DEPTH,
    MAX_FILES,
    MAX_TOTAL_SIZE_BYTES
)

async def tree_node(state: State) -> dict:
    """目录树生成节点。
    
    职责：
    1. 扫描仓库目录结构
    2. 遵循大小和深度限制
    3. 应用初始过滤模式
    4. 检测符号链接安全性
    
    Args:
        state: 当前图状态

    Returns:
        dict: 包含目录树的状态更新
    """
    try:
        nodes = await _scan_directory(
            path=state["local_path"],
            base_path=state["local_path"],
            patterns=state.get("patterns", []),
            pattern_type=state.get("pattern_type", "exclude")
        )
        
        if not nodes:
            raise ValueError(f"No files found in {state['local_path']}")

        # 生成目录树文本表示
        tree = "Directory structure:\n" + _create_tree_structure(nodes)
        
        return {
            "tree": tree,
            "scan_result": nodes  # 这个值会被添加到状态中
        }

    except Exception as e:
        raise ValueError(f"Failed to generate directory tree: {str(e)}")

async def _scan_directory(
    path: str,
    base_path: str,
    patterns: list[str],
    pattern_type: str,
    depth: int = 0,
    stats: Optional[dict[str, int]] = None,
    seen_paths: Optional[set[str]] = None
) -> Optional[dict[str, Any]]:
    """递归扫描目录并构建节点树。"""
    if seen_paths is None:
        seen_paths = set()
    if stats is None:
        stats = {"total_files": 0, "total_size": 0}

    # 检查深度限制
    if depth > MAX_DIRECTORY_DEPTH:
        print(f"Skipping deep directory: {path} (max depth {MAX_DIRECTORY_DEPTH} reached)")
        return None

    # 检查文件数量限制
    if stats["total_files"] >= MAX_FILES:
        print(f"Skipping further processing: maximum file limit ({MAX_FILES}) reached")
        return None

    # 检查总大小限制
    if stats["total_size"] >= MAX_TOTAL_SIZE_BYTES:
        print(f"Skipping further processing: maximum total size ({MAX_TOTAL_SIZE_BYTES/1024/1024:.1f}MB) reached")
        return None

    # 检查重复路径
    real_path = os.path.realpath(path)
    if real_path in seen_paths:
        print(f"Skipping already visited path: {path}")
        return None
    seen_paths.add(real_path)

    result = {
        "name": os.path.basename(path),
        "type": "directory",
        "size": 0,
        "children": [],
        "file_count": 0,
        "dir_count": 0,
        "path": path,
        "ignore_content": False,
    }

    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            rel_path = os.path.relpath(item_path, base_path)

            # 应用过滤模式
            should_process = _should_process(rel_path, patterns, pattern_type)
            if not should_process:
                continue

            # 处理符号链接
            if os.path.islink(item_path):
                if not _is_safe_symlink(item_path, base_path):
                    print(f"Skipping symlink that points outside base directory: {item_path}")
                    continue
                real_path = os.path.realpath(item_path)
                if real_path in seen_paths:
                    print(f"Skipping already visited symlink target: {item_path}")
                    continue

            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                if stats["total_size"] + file_size > MAX_TOTAL_SIZE_BYTES:
                    print(f"Skipping file {item_path}: would exceed total size limit")
                    continue

                stats["total_files"] += 1
                stats["total_size"] += file_size

                if stats["total_files"] > MAX_FILES:
                    print(f"Maximum file limit ({MAX_FILES}) reached")
                    return result

                child = {
                    "name": item,
                    "type": "file",
                    "size": file_size,
                    "path": item_path,
                }
                result["children"].append(child)
                result["size"] += file_size
                result["file_count"] += 1

            elif os.path.isdir(item_path):
                subdir = await _scan_directory(
                    path=item_path,
                    base_path=base_path,
                    patterns=patterns,
                    pattern_type=pattern_type,
                    depth=depth + 1,
                    stats=stats,
                    seen_paths=seen_paths,
                )
                if subdir:
                    result["children"].append(subdir)
                    result["size"] += subdir["size"]
                    result["file_count"] += subdir["file_count"]
                    result["dir_count"] += 1 + subdir["dir_count"]

        result["children"] = _sort_children(result["children"])
        return result

    except PermissionError:
        print(f"Permission denied: {path}")
        return None

def _create_tree_structure(
    node: dict[str, Any],
    prefix: str = "",
    is_last: bool = True
) -> str:
    """创建目录树的文本表示。"""
    tree = ""

    if not node["name"]:
        node["name"] = os.path.basename(node["path"])

    if node["name"]:
        current_prefix = "└── " if is_last else "├── "
        name = node["name"] + "/" if node["type"] == "directory" else node["name"]
        tree += prefix + current_prefix + name + "\n"

    if node["type"] == "directory":
        new_prefix = prefix + ("    " if is_last else "│   ") if node["name"] else prefix
        children = node["children"]
        for i, child in enumerate(children):
            tree += _create_tree_structure(child, new_prefix, i == len(children) - 1)

    return tree

def _should_process(path: str, patterns: list[str], pattern_type: str) -> bool:
    """判断路径是否应该被处理。"""
    if not patterns:
        return True

    matches = any(fnmatch(path, pattern) for pattern in patterns)
    return matches if pattern_type == "include" else not matches

def _is_safe_symlink(symlink_path: str, base_path: str) -> bool:
    """检查符号链接是否指向基础目录内。"""
    try:
        target_path = os.path.realpath(symlink_path)
        base_path = os.path.realpath(base_path)
        return os.path.commonpath([target_path, base_path]) == base_path
    except (OSError, ValueError):
        return False

def _sort_children(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """对子节点进行排序。
    
    排序规则：
    1. README.md 优先
    2. 普通文件
    3. 隐藏文件
    4. 普通目录
    5. 隐藏目录
    所有组内按字母顺序排序
    """
    # 分离文件和目录
    files = [child for child in children if child["type"] == "file"]
    directories = [child for child in children if child["type"] == "directory"]

    # 找出 README.md
    readme_files = [f for f in files if f["name"].lower() == "readme.md"]
    other_files = [f for f in files if f["name"].lower() != "readme.md"]

    # 分离隐藏和普通文件/目录
    regular_files = [f for f in other_files if not f["name"].startswith(".")]
    hidden_files = [f for f in other_files if f["name"].startswith(".")]
    regular_dirs = [d for d in directories if not d["name"].startswith(".")]
    hidden_dirs = [d for d in directories if d["name"].startswith(".")]

    # 各组内字母顺序排序
    regular_files.sort(key=lambda x: x["name"])
    hidden_files.sort(key=lambda x: x["name"])
    regular_dirs.sort(key=lambda x: x["name"])
    hidden_dirs.sort(key=lambda x: x["name"])

    # 按指定顺序组合
    return readme_files + regular_files + hidden_files + regular_dirs + hidden_dirs