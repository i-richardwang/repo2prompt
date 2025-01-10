# src/main.py
import logging
import uuid
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
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

@app.post("/api/analyze", response_model=RepoResponse)
async def analyze_repository(
    request: RepoRequest,
    authorization: Optional[str] = Header(None, description="Bearer token for API authentication")
):
    """API endpoint for analyzing repository content.
    
    Args:
        request: Request object containing repository URL and analysis parameters
        authorization: Optional Bearer token containing API key. If not provided, uses environment variable.

    Returns:
        RepoResponse: Analysis results
        
    Raises:
        HTTPException: Errors during processing
    """
    try:
        logger.info(f"Starting repository analysis: {request.url}")
        
        # Get API key from authorization header or environment
        api_key = None
        if authorization:
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header format")
            api_key = authorization.replace("Bearer ", "")
        
        # Initialize LLM model before graph execution
        from .llm_tools import init_language_model
        model = init_language_model(
            api_key=api_key,  # If None, will use environment variable
            base_url=str(request.base_url) if request.base_url else None,  # If None, will use environment variable
            model_name=request.model_name  # If None, will use environment variable
        )
        
        # Prepare initial state
        initial_state = {
            "url": request.url,
            "max_file_size": request.max_file_size or DEFAULT_MAX_FILE_SIZE,
            "pattern_type": request.pattern_type,
            "patterns": request.pattern.split(',') if request.pattern else [],
            "user_query": request.query,
            "messages": [],  # LLM interaction message history
            "paths_to_clean": [],  # Paths to clean up
            "should_generate_patterns": False,  # Routing flag
            "local_path": str(Path(TMP_BASE_PATH) / str(uuid.uuid4()) / os.path.basename(request.url.rstrip('/')).replace('.git', '')),
            "repo_name": os.path.basename(request.url.rstrip('/')).replace('.git', ''),
            "model": model,  # Add initialized model to state
        }
        
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