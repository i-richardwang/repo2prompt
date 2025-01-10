# src/config.py
import os

# Base path for temporary files
# This directory will store cloned repositories and temporary files
TMP_BASE_PATH = os.getenv("TMP_BASE_PATH", "tmp")

# Maximum file size in bytes (default: 50KB)
# Files larger than this size will be skipped during processing
DEFAULT_MAX_FILE_SIZE = 50 * 1024 

# API Configuration 
# Title and version information for the FastAPI documentation
API_TITLE = "RepoToPrompt API"
API_VERSION = "1.0.0"

# CORS Configuration
# Comma-separated list of allowed origins for CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Clone Configuration
# Timeout for repository cloning operations
CLONE_TIMEOUT = 20  # seconds

# Process Limits
# Safety limits to prevent resource exhaustion
MAX_FILES = 10_000  # Maximum number of files to process
MAX_TOTAL_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB total repository size limit
MAX_DIRECTORY_DEPTH = 20  # Maximum depth for directory traversal