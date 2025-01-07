# src/config.py
import os

# Base path for temporary files
TMP_BASE_PATH = os.getenv("TMP_BASE_PATH", "tmp")

# Maximum file size in bytes (default: 50KB)
DEFAULT_MAX_FILE_SIZE = 50 * 1024 

# API Configuration 
API_TITLE = "RepoToPrompt API"
API_VERSION = "1.0.0"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "siliconcloud")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

# Clone Configuration
CLONE_TIMEOUT = 20  # seconds

# Process Limits
MAX_FILES = 10_000  # Maximum number of files to process
MAX_TOTAL_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_DIRECTORY_DEPTH = 20  # Maximum depth of directory traversal