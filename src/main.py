# src/main.py
import logging
import uuid
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from .config import API_TITLE, API_VERSION, ALLOWED_ORIGINS, TMP_BASE_PATH, DEFAULT_MAX_FILE_SIZE
from .schemas import RepoRequest, RepoResponse, State
from .nodes.clone import clone_node
from .nodes.tree import tree_node
from .nodes.route import route_node, determine_next_node
from .nodes.pattern import pattern_node
from .nodes.process import process_node
from .nodes.cleanup import cleanup_node

from langgraph.graph import StateGraph, START, END

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

def build_graph() -> StateGraph:
    # 创建图构建器
    builder = StateGraph(State)
    
    # 添加所有节点，使用更具描述性的节点名
    builder.add_node("clone_repo", clone_node)
    builder.add_node("scan_tree", tree_node)  # 改为 scan_tree
    builder.add_node("route_task", route_node)
    builder.add_node("generate_pattern", pattern_node)
    builder.add_node("process_content", process_node)
    builder.add_node("cleanup_resources", cleanup_node)
    
    # 设置入口
    builder.add_edge(START, "clone_repo")
    
    # 设置主要处理流程
    builder.add_edge("clone_repo", "scan_tree")
    builder.add_edge("scan_tree", "route_task")
    
    # 添加条件边
    builder.add_conditional_edges(
        "route_task",
        determine_next_node,
        {
            "pattern": "generate_pattern",
            "process": "process_content"
        }
    )
    
    # 模式生成后继续处理
    builder.add_edge("generate_pattern", "process_content")
    
    # 处理完成后清理
    builder.add_edge("process_content", "cleanup_resources")
    
    # 清理完成后结束
    builder.add_edge("cleanup_resources", END)
    
    return builder.compile()

# 创建图实例
GRAPH = build_graph()

def _prepare_initial_state(request: RepoRequest) -> dict:
    """准备初始状态。"""
    # 生成唯一的 ID 和本地路径
    _id = str(uuid.uuid4())
    repo_name = os.path.basename(request.url.rstrip('/')).replace('.git', '')
    local_path = str(Path(TMP_BASE_PATH) / _id / repo_name)
    
    return {
        "url": request.url,
        "max_file_size": request.max_file_size or DEFAULT_MAX_FILE_SIZE,
        "pattern_type": request.pattern_type,
        "patterns": request.pattern.split(',') if request.pattern else [],
        "user_query": request.query,
        "messages": [],  # LLM 交互消息列表
        "paths_to_clean": [],  # 待清理路径列表
        "should_generate_patterns": False,  # 路由标志位
        "local_path": local_path,  # 添加本地路径
        "repo_name": repo_name,  # 添加仓库名称以便后续使用
    }

@app.post("/api/analyze", response_model=RepoResponse)
async def analyze_repository(request: RepoRequest):
    """分析仓库内容的 API 端点。
    
    Args:
        request: 包含仓库 URL 和分析参数的请求对象

    Returns:
        RepoResponse: 分析结果
        
    Raises:
        HTTPException: 处理过程中的错误
    """
    try:
        logger.info(f"Starting repository analysis: {request.url}")
        
        # 准备初始状态
        initial_state = _prepare_initial_state(request)
        
        # 如果有用户查询，添加到消息历史
        if request.query:
            initial_state["messages"].append(
                HumanMessage(content=request.query)
            )
        
        # 执行图
        try:
            final_state = await GRAPH.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Graph execution failed: {str(e)}")
            raise ValueError(f"Failed to process repository: {str(e)}")
        
        # 构建响应
        response = RepoResponse(
            summary=final_state["summary"],
            tree=final_state["tree"],
            content=final_state["content"],
            generated_patterns=final_state.get("generated_patterns")
        )
        
        logger.info("Analysis completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)