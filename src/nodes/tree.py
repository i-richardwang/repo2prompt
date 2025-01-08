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
    """Directory tree generation node.
    
    Responsibilities:
    1. Scan repository directory structure
    2. Follow size and depth limits
    3. Apply initial filter patterns
    4. Check symlink security
    
    Args:
        state: Current graph state

    Returns:
        dict: State update containing directory tree
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

        # Generate text representation of directory tree
        tree = "Directory structure:\n" + _create_tree_structure(nodes)
        
        return {
            "tree": tree,
            "scan_result": nodes  # This value will be added to the state
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
    """Recursively scan directory and build node tree."""
    if seen_paths is None:
        seen_paths = set()
    if stats is None:
        stats = {"total_files": 0, "total_size": 0}

    # Check depth limit
    if depth > MAX_DIRECTORY_DEPTH:
        print(f"Skipping deep directory: {path} (max depth {MAX_DIRECTORY_DEPTH} reached)")
        return None

    # Check file count limit
    if stats["total_files"] >= MAX_FILES:
        print(f"Skipping further processing: maximum file limit ({MAX_FILES}) reached")
        return None

    # Check total size limit
    if stats["total_size"] >= MAX_TOTAL_SIZE_BYTES:
        print(f"Skipping further processing: maximum total size ({MAX_TOTAL_SIZE_BYTES/1024/1024:.1f}MB) reached")
        return None

    # Check for duplicate paths
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

            # Apply filter patterns
            should_process = _should_process(rel_path, patterns, pattern_type)
            if not should_process:
                continue

            # Handle symlinks
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
    """Create text representation of directory tree."""
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
    """Determine if path should be processed."""
    if not patterns:
        return True

    matches = any(fnmatch(path, pattern) for pattern in patterns)
    return matches if pattern_type == "include" else not matches

def _is_safe_symlink(symlink_path: str, base_path: str) -> bool:
    """Check if symlink points within base directory."""
    try:
        target_path = os.path.realpath(symlink_path)
        base_path = os.path.realpath(base_path)
        return os.path.commonpath([target_path, base_path]) == base_path
    except (OSError, ValueError):
        return False

def _sort_children(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort child nodes.
    
    Sort rules:
    1. README.md first
    2. Regular files
    3. Hidden files
    4. Regular directories
    5. Hidden directories
    All items within each group are sorted alphabetically
    """
    # Separate files and directories
    files = [child for child in children if child["type"] == "file"]
    directories = [child for child in children if child["type"] == "directory"]

    # Find README.md files
    readme_files = [f for f in files if f["name"].lower() == "readme.md"]
    other_files = [f for f in files if f["name"].lower() != "readme.md"]

    # Separate hidden and regular files/directories
    regular_files = [f for f in other_files if not f["name"].startswith(".")]
    hidden_files = [f for f in other_files if f["name"].startswith(".")]
    regular_dirs = [d for d in directories if not d["name"].startswith(".")]
    hidden_dirs = [d for d in directories if d["name"].startswith(".")]

    # Sort each group alphabetically
    regular_files.sort(key=lambda x: x["name"])
    hidden_files.sort(key=lambda x: x["name"])
    regular_dirs.sort(key=lambda x: x["name"])
    hidden_dirs.sort(key=lambda x: x["name"])

    # Combine in specified order
    return readme_files + regular_files + hidden_files + regular_dirs + hidden_dirs