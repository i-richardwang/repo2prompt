# src/schemas.py
from typing import Annotated, Optional, Literal, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

class RepoRequest(BaseModel):
    """Repository analysis request schema."""
    url: str = Field(..., description="Git repository URL to analyze")
    max_file_size: Optional[int] = Field(
        default=None, 
        description="Maximum file size in bytes to process"
    )
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
    """Result schema for pattern generation."""
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
    """Repository analysis response schema."""
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
    """State schema for the Langgraph state machine."""
    # Repository information
    url: str
    local_path: str
    max_file_size: int
    
    # File filtering
    pattern_type: Literal["include", "exclude"]
    patterns: list[str]
    user_query: Optional[str]
    
    # Processing state
    generated_patterns: Optional[PatternGeneratorResult]
    tree: Optional[str]
    content: Optional[str]
    summary: Optional[str]
    
    # Messages for LLM interaction
    messages: Annotated[list, add_messages]
    
    # Cleanup information
    paths_to_clean: list[str]
    cleaned_paths: list[str]

    # Control flags
    should_generate_patterns: bool

    scan_result: Optional[Dict[str, Any]]