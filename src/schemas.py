# src/schemas.py
from typing import Annotated, Optional, Literal, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, HttpUrl
from langgraph.graph.message import add_messages

import logging

logger = logging.getLogger(__name__)


class RepoRequest(BaseModel):
    """Repository analysis request schema.
    
    This model defines the structure of incoming repository analysis requests,
    including URL, LLM configuration, and filtering options.
    """
    model_config = {
        "protected_namespaces": ()  # Disable protected namespaces to resolve warning
    }

    # Repository configuration
    url: str = Field(..., description="Git repository URL to analyze")
    max_file_size: Optional[int] = Field(
        default=None, 
        description="Maximum file size in bytes to process"
    )
    
    # LLM configuration
    base_url: Optional[HttpUrl] = Field(
        default=None,
        description="Custom LLM API base URL. If not provided, uses environment variable."
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Custom LLM model name. If not provided, uses environment variable."
    )
    
    # Filter configuration
    pattern_type: Optional[Literal["include", "exclude"]] = Field(
        default="exclude",
        description="Type of pattern matching to apply"
    )
    pattern: Optional[str] = Field(
        default="",
        description="Comma-separated patterns for filtering files"
    )
    query: Optional[str] = Field(
        default=None,
        description="Natural language query for generating file patterns"
    )

class PatternGeneratorResult(BaseModel):
    """Result schema for pattern generation.
    
    This model represents the output of the LLM-based pattern generation process,
    including the generated patterns and their explanation.
    """
    pattern_type: Literal["include", "exclude"] = Field(
        ..., 
        description="Type of pattern matching applied"
    )
    patterns: list[str] = Field(
        ..., 
        description="List of generated patterns"
    )
    explanation: str = Field(
        ..., 
        description="Explanation of the generated patterns"
    )

class RepoResponse(BaseModel):
    """Repository analysis response schema.
    
    This model defines the structure of the analysis response,
    containing the repository summary, structure, and processed content.
    """
    summary: str = Field(
        ..., 
        description="Summary of the repository analysis"
    )
    tree: str = Field(
        ..., 
        description="Tree representation of repository structure"
    )
    content: str = Field(
        ..., 
        description="Processed content of repository files"
    )
    generated_patterns: Optional[PatternGeneratorResult] = Field(
        default=None,
        description="Generated patterns if query was provided"
    )

class State(TypedDict):
    """State schema for the Langgraph state machine.
    
    This class defines the structure of the state object that flows through
    the processing graph, containing all necessary information for each node.
    """
    # Repository information
    url: str  # Repository URL being analyzed
    local_path: str  # Local path where repository is cloned
    max_file_size: int  # Maximum size for individual files
    
    # File filtering configuration
    pattern_type: Literal["include", "exclude"]  # Type of pattern matching
    patterns: list[str]  # List of patterns to apply
    user_query: Optional[str]  # Natural language query if provided
    
    # Processing state information
    generated_patterns: Optional[PatternGeneratorResult]  # LLM-generated patterns
    tree: Optional[str]  # Repository structure representation
    content: Optional[str]  # Processed file contents
    summary: Optional[str]  # Analysis summary
    
    # Message history
    messages: Annotated[list, add_messages]  # Message history for LLM
    
    # Resource cleanup tracking
    paths_to_clean: list[str]  # Paths pending cleanup
    cleaned_paths: list[str]  # Paths already cleaned
    
    # Process control
    should_generate_patterns: bool  # Whether to generate patterns using LLM
    
    # Scan results
    scan_result: Optional[Dict[str, Any]]  # Results from repository scan
    
    # LLM model
    model: Any  # Initialized language model instance