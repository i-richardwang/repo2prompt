# src/nodes/clone.py
import asyncio
from typing import Tuple
from urllib.parse import unquote

from ..schemas import State
from ..config import CLONE_TIMEOUT
from ..utils import async_timeout

async def clone_node(state: State) -> dict:
    """Repository cloning node.
    
    Responsibilities:
    1. Validate repository URL
    2. Checkout specific branch or commit
    3. Use secure cloning options
    4. Asynchronous execution with timeout control
    
    Args:
        state: Current graph state

    Returns:
        dict: Updated state fields

    Raises:
        ValueError: Invalid repository URL or missing required parameters
        RuntimeError: Git command execution failed
        AsyncTimeoutError: Clone operation timed out
    """
    url = _normalize_url(state["url"])
    local_path = state["local_path"]

    if not url:
        raise ValueError("The 'url' parameter is required.")
    if not local_path:
        raise ValueError("The 'local_path' parameter is required.")

    # Check if repository exists and is accessible
    if not await _check_repo_exists(url):
        raise ValueError("Repository not found or not accessible, make sure it is public")

    try:
        # Parse URL to get possible branch or commit information
        commit, branch = await _parse_git_ref(url)

        if commit:
            # Scenario 1: Clone and checkout specific commit
            # No depth limit to ensure any commit can be checked out
            clone_cmd = ["git", "clone", "--single-branch", url, local_path]
            await _run_git_command(*clone_cmd)
            
            # Checkout specific commit
            checkout_cmd = ["git", "-C", local_path, "checkout", commit]
            await _run_git_command(*checkout_cmd)

        elif branch and branch.lower() not in ("main", "master"):
            # Scenario 2: Clone specific branch
            clone_cmd = [
                "git", "clone", "--depth=1", "--single-branch",
                "--branch", branch, url, local_path
            ]
            await _run_git_command(*clone_cmd)

        else:
            # Scenario 3: Clone default branch
            clone_cmd = ["git", "clone", "--depth=1", "--single-branch", url, local_path]
            await _run_git_command(*clone_cmd)

        # Add local path to cleanup list
        return {
            "paths_to_clean": [local_path]
        }

    except (RuntimeError, asyncio.TimeoutError) as e:
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

@async_timeout(CLONE_TIMEOUT)
async def _run_git_command(*args: str) -> Tuple[bytes, bytes]:
    """Execute git command and capture output."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        error_message = stderr.decode().strip()
        raise RuntimeError(f"Git command failed: {' '.join(args)}\nError: {error_message}")

    return stdout, stderr

async def _check_repo_exists(url: str) -> bool:
    """Check if repository exists and is accessible."""
    proc = await asyncio.create_subprocess_exec(
        "curl",
        "-I",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return False
    
    stdout_str = stdout.decode()
    return "HTTP/1.1 404" not in stdout_str and "HTTP/2 404" not in stdout_str

async def _parse_git_ref(url: str) -> Tuple[str | None, str | None]:
    """Parse git reference information (commit or branch) from URL."""
    url = unquote(url)
    if not url.startswith("https://"):
        url = "https://" + url

    path_parts = url.split("/")[3:]
    if len(path_parts) < 4:
        return None, None  # Use default branch

    ref_type = path_parts[2]  # Usually 'tree' or 'blob'
    ref = path_parts[3]  # Commit hash or branch name

    if _is_valid_git_commit_hash(ref):
        return ref, None
    else:
        return None, ref

def _is_valid_git_commit_hash(ref: str) -> bool:
    """Validate if it's a valid git commit hash."""
    return len(ref) == 40 and all(c in "0123456789abcdefABCDEF" for c in ref)

def _normalize_url(url: str) -> str:
    """Normalize git repository URL."""
    url = url.split(" ")[0]  # Remove possible extra parameters
    url = unquote(url)  # Decode URL encoded characters
    
    if not url.startswith("https://"):
        url = "https://" + url

    return url