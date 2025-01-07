# src/nodes/clone.py
import asyncio
from typing import Tuple
from urllib.parse import unquote

from ..schemas import State
from ..config import CLONE_TIMEOUT
from ..utils import async_timeout

async def clone_node(state: State) -> dict:
    """克隆仓库节点。
    
    职责:
    1. 验证仓库URL
    2. 检出特定分支或提交
    3. 使用安全的克隆选项
    4. 异步执行以及超时控制
    
    Args:
        state: 当前图状态

    Returns:
        dict: 更新后的状态字段

    Raises:
        ValueError: 仓库URL无效或必需参数缺失
        RuntimeError: Git命令执行失败
        AsyncTimeoutError: 克隆操作超时
    """
    url = _normalize_url(state["url"])
    local_path = state["local_path"]

    if not url:
        raise ValueError("The 'url' parameter is required.")
    if not local_path:
        raise ValueError("The 'local_path' parameter is required.")

    # 检查仓库是否存在且可访问
    if not await _check_repo_exists(url):
        raise ValueError("Repository not found or not accessible, make sure it is public")

    try:
        # 解析 URL 获取可能的分支或提交信息
        commit, branch = await _parse_git_ref(url)

        if commit:
            # 场景1: 克隆并检出特定提交
            # 不限制深度以确保可以检出任意提交
            clone_cmd = ["git", "clone", "--single-branch", url, local_path]
            await _run_git_command(*clone_cmd)
            
            # 检出特定提交
            checkout_cmd = ["git", "-C", local_path, "checkout", commit]
            await _run_git_command(*checkout_cmd)

        elif branch and branch.lower() not in ("main", "master"):
            # 场景2: 克隆特定分支
            clone_cmd = [
                "git", "clone", "--depth=1", "--single-branch",
                "--branch", branch, url, local_path
            ]
            await _run_git_command(*clone_cmd)

        else:
            # 场景3: 克隆默认分支
            clone_cmd = ["git", "clone", "--depth=1", "--single-branch", url, local_path]
            await _run_git_command(*clone_cmd)

        # 添加本地路径到清理列表
        return {
            "paths_to_clean": [local_path]
        }

    except (RuntimeError, asyncio.TimeoutError) as e:
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

@async_timeout(CLONE_TIMEOUT)
async def _run_git_command(*args: str) -> Tuple[bytes, bytes]:
    """执行 git 命令并捕获输出。"""
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
    """检查仓库是否存在且可访问。"""
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
    """从URL中解析git引用信息(commit或branch)。"""
    url = unquote(url)
    if not url.startswith("https://"):
        url = "https://" + url

    path_parts = url.split("/")[3:]
    if len(path_parts) < 4:
        return None, None  # 使用默认分支

    ref_type = path_parts[2]  # 通常是 'tree' 或 'blob'
    ref = path_parts[3]  # commit hash 或 branch 名称

    if _is_valid_git_commit_hash(ref):
        return ref, None
    else:
        return None, ref

def _is_valid_git_commit_hash(ref: str) -> bool:
    """验证是否为有效的git commit hash。"""
    return len(ref) == 40 and all(c in "0123456789abcdefABCDEF" for c in ref)

def _normalize_url(url: str) -> str:
    """标准化git仓库URL。"""
    url = url.split(" ")[0]  # 移除可能的额外参数
    url = unquote(url)  # 解码 URL 编码字符
    
    if not url.startswith("https://"):
        url = "https://" + url

    return url