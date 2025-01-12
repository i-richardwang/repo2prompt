# src/nodes/process.py
import os
import tiktoken
from typing import Any, Dict, List, Optional

from ..schemas import State
from ..config import DEFAULT_MAX_FILE_SIZE

async def process_node(state: State) -> Dict[str, Any]:
    """Content processing node.
    
    Responsibilities:
    1. Extract and filter file contents
    2. Generate file content summary
    3. Estimate token count
    4. Generate final processing report
    
    Args:
        state: Current graph state

    Returns:
        dict: State update containing processing results
    """
    try:
        max_file_size = state.get("max_file_size", DEFAULT_MAX_FILE_SIZE)
        scan_result = state["scan_result"]
        
        # Extract file contents
        files = await _extract_files_content(
            scan_result,
            state.get("patterns", []),
            state.get("pattern_type", "exclude"),
            max_file_size
        )
        
        # Generate content string
        content = _create_file_content_string(files)
        
        # Generate summary
        summary = _create_summary_string(scan_result, state)
        
        # Estimate token count
        formatted_tokens = _generate_token_string(content)
        if formatted_tokens:
            summary += f"\nEstimated tokens: {formatted_tokens}"
            
        return {
            "content": content,
            "summary": summary
        }
        
    except Exception as e:
        raise ValueError(f"Content processing failed: {str(e)}")

async def _extract_files_content(
    node: Dict[str, Any],
    patterns: List[str],
    pattern_type: str,
    max_file_size: int,
    base_path: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Recursively extract file contents."""
    if files is None:
        files = []
    if base_path is None:
        base_path = node["path"]

    if node["type"] == "file":
        file_path = node["path"]
        rel_path = os.path.relpath(file_path, base_path)
        
        # Apply filter patterns
        should_process = _should_process(rel_path, patterns, pattern_type)
        if not should_process:
            return files

        if _is_text_file(file_path):
            content = None
            if node["size"] <= max_file_size:
                content = _read_file_content(file_path)
            
            files.append({
                "path": rel_path,
                "content": content,
                "size": node["size"],
            })
            
    elif node["type"] == "directory" and not node.get("ignore_content", False):
        for child in node["children"]:
            await _extract_files_content(
                node=child,
                patterns=patterns,
                pattern_type=pattern_type,
                max_file_size=max_file_size,
                base_path=base_path,
                files=files
            )
    
    return files

def _create_file_content_string(files: List[Dict[str, Any]]) -> str:
    """Create formatted file content string."""
    output = ""
    separator = "=" * 48 + "\n"

    for file in files:
        if not file["content"]:
            continue

        output += separator
        output += f"File: {file['path']}\n"
        output += separator
        output += f"{file['content']}\n\n"

    return output


def _create_summary_string(node: Dict[str, Any], state: Dict[str, Any]) -> str:
    """Create repository summary string."""
    parts = []

    # Repository information
    repo_name = state.get("repo_name", os.path.basename(state["local_path"]))
    parts.append(f"Repository: {repo_name}")

    # File statistics
    parts.append(f"Files analyzed: {node['file_count']}")

    # Filter pattern information (only for manually specified patterns)
    if not state.get("generated_patterns") and state.get("patterns"):
        parts.append(f"Pattern type: {state['pattern_type']}")
        parts.append("Applied patterns:")
        for pattern in state["patterns"]:
            parts.append(f"  - {pattern}")

    return "\n".join(parts)

def _generate_token_string(context_string: str) -> Optional[str]:
    """Estimate and format token count."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        total_tokens = len(encoding.encode(context_string, disallowed_special=()))
        
        if total_tokens > 1_000_000:
            return f"{total_tokens / 1_000_000:.1f}M"
        elif total_tokens > 1_000:
            return f"{total_tokens / 1_000:.1f}k"
        else:
            return str(total_tokens)
            
    except Exception:
        return None

def _should_process(path: str, patterns: List[str], pattern_type: str) -> bool:
    """Determine if the file should be processed."""
    from fnmatch import fnmatch
    
    if not patterns:
        return True
        
    matches = any(fnmatch(path, pattern) for pattern in patterns)
    return matches if pattern_type == "include" else not matches

def _is_text_file(file_path: str) -> bool:
    """Determine if the file is a text file."""
    try:
        with open(file_path, "rb") as file:
            chunk = file.read(1024)
        return not bool(chunk.translate(None, bytes([7, 8, 9, 10, 12, 13, 27] + list(range(0x20, 0x100)))))
    except OSError:
        return False

def _read_file_content(file_path: str) -> str:
    """Read file content."""
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"