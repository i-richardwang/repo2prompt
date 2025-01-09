# src/schemas.py
from typing import Annotated, Optional, Literal, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

from .utils.crypto import AESCipher

class LLMConfig(BaseModel):
    """LLM configuration from request headers.
    
    This model represents the custom LLM configuration provided in request headers,
    including API credentials and model selection.
    """
    model_config = {
        "protected_namespaces": ()  # Disable protected namespaces to resolve warning
    }
    
    api_key: str = Field(..., description="LLM API key")
    api_base: str = Field(..., description="LLM API base URL")
    model_name: str = Field(..., description="LLM model name")

    @classmethod
    def from_encrypted_headers(cls, headers: Dict[str, str], cipher: AESCipher) -> Optional['LLMConfig']:
        """Create LLMConfig from encrypted headers.
        
        Args:
            headers: Request headers dictionary
            cipher: AESCipher instance for decryption
            
        Returns:
            LLMConfig instance if all required headers are present, None otherwise
        """
        try:
            if all(key in headers for key in ['X-LLM-API-Key', 'X-LLM-API-Base', 'X-LLM-Model']):
                return cls(
                    api_key=cipher.decrypt(headers['X-LLM-API-Key']),
                    api_base=cipher.decrypt(headers['X-LLM-API-Base']),
                    model_name=cipher.decrypt(headers['X-LLM-Model'])
                )
            return None
        except Exception as e:
            logger.warning(f"Failed to parse LLM config from headers: {str(e)}")
            return None

class RepoRequest(BaseModel):
    """Repository analysis request schema.
    
    This model defines the structure of incoming repository analysis requests,
    including URL, file size limits, and filtering options.
    """
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
    
    # LLM configuration and interaction
    llm_config: Optional[LLMConfig]  # Custom LLM configuration if provided
    messages: Annotated[list, add_messages]  # Message history for LLM
    
    # Resource cleanup tracking
    paths_to_clean: list[str]  # Paths pending cleanup
    cleaned_paths: list[str]  # Paths already cleaned
    
    # Process control
    should_generate_patterns: bool  # Whether to generate patterns using LLM
    
    # Scan results
    scan_result: Optional[Dict[str, Any]]  # Results from repository scan