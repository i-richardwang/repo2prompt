# src/main.py
import logging
import uuid
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from .config import API_TITLE, API_VERSION, ALLOWED_ORIGINS, TMP_BASE_PATH, DEFAULT_MAX_FILE_SIZE
from .schemas import RepoRequest, RepoResponse, State, LLMConfig
from .utils.crypto import AESCipher
from .nodes.clone import clone_node
from .nodes.tree import tree_node
from .nodes.route import route_node, determine_next_node
from .nodes.pattern import pattern_node
from .nodes.process import process_node
from .nodes.cleanup import cleanup_node

from langgraph.graph import StateGraph, START, END

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

def build_graph() -> StateGraph:
    # Create graph builder
    builder = StateGraph(State)
    
    # Add all nodes with more descriptive names
    builder.add_node("clone_repo", clone_node)
    builder.add_node("scan_tree", tree_node)
    builder.add_node("route_task", route_node)
    builder.add_node("generate_pattern", pattern_node)
    builder.add_node("process_content", process_node)
    builder.add_node("cleanup_resources", cleanup_node)
    
    # Set entry point
    builder.add_edge(START, "clone_repo")
    
    # Set main processing flow
    builder.add_edge("clone_repo", "scan_tree")
    builder.add_edge("scan_tree", "route_task")
    
    # Add conditional edges
    builder.add_conditional_edges(
        "route_task",
        determine_next_node,
        {
            "pattern": "generate_pattern",
            "process": "process_content"
        }
    )
    
    # Continue processing after pattern generation
    builder.add_edge("generate_pattern", "process_content")
    
    # Clean up after processing
    builder.add_edge("process_content", "cleanup_resources")
    
    # End after cleanup
    builder.add_edge("cleanup_resources", END)
    
    return builder.compile()

# Create graph instance
GRAPH = build_graph()

def _prepare_initial_state(
    request: RepoRequest,
    llm_config: Optional[LLMConfig] = None
) -> dict:
    """Prepare initial state.
    
    Args:
        request: Analysis request
        llm_config: Optional custom LLM configuration
        
    Returns:
        Initial state dictionary
    """
    # Generate unique ID and local path
    _id = str(uuid.uuid4())
    repo_name = os.path.basename(request.url.rstrip('/')).replace('.git', '')
    local_path = str(Path(TMP_BASE_PATH) / _id / repo_name)
    
    state = {
        "url": request.url,
        "max_file_size": request.max_file_size or DEFAULT_MAX_FILE_SIZE,
        "pattern_type": request.pattern_type,
        "patterns": request.pattern.split(',') if request.pattern else [],
        "user_query": request.query,
        "messages": [],  # LLM interaction message history
        "paths_to_clean": [],  # Paths to clean up
        "should_generate_patterns": False,  # Routing flag
        "local_path": local_path,  # Add local path
        "repo_name": repo_name,  # Add repo name for later use
    }
    
    # Add LLM configuration if provided
    if llm_config:
        state["llm_config"] = llm_config
        
    return state

@app.post("/api/analyze", response_model=RepoResponse)
async def analyze_repository(
    request: RepoRequest,
    request_obj: Request
):
    """API endpoint for analyzing repository content.
    
    Args:
        request: Request object containing repository URL and analysis parameters
        request_obj: FastAPI request object for accessing headers

    Returns:
        RepoResponse: Analysis results
        
    Raises:
        HTTPException: Errors during processing
    """
    try:
        logger.info(f"Starting repository analysis: {request.url}")
        
        # Parse LLM configuration from headers if provided
        llm_config = None
        try:
            if any(key.startswith('x-llm-') for key in request_obj.headers):
                cipher = AESCipher()
                llm_config = LLMConfig.from_encrypted_headers(dict(request_obj.headers), cipher)
                if llm_config:
                    logger.info("Using custom LLM configuration from headers")
        except Exception as e:
            logger.warning(f"Failed to parse LLM configuration from headers: {str(e)}")
        
        # Prepare initial state
        initial_state = _prepare_initial_state(request, llm_config)
        
        # If there's a user query, add it to message history
        if request.query:
            initial_state["messages"].append(
                HumanMessage(content=request.query)
            )
        
        # Execute graph
        try:
            final_state = await GRAPH.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Graph execution failed: {str(e)}")
            raise ValueError(f"Failed to process repository: {str(e)}")
        
        # Build response
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