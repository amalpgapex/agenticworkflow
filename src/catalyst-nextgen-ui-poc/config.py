"""
Configuration Management
Centralized configuration for InK Studio

SECURITY NOTE: Set OPENAI_API_KEY via environment variable, not in this file!
For development: $env:OPENAI_API_KEY = "sk-..." (PowerShell)
For production: Use proper secret management
"""
from dotenv import load_dotenv
load_dotenv(override=False)
import os
from pathlib import Path

# ============================================================================
# API Configuration
# ============================================================================
# IMPORTANT: Set via environment variable for security!
# Example: $env:OPENAI_API_KEY = "sk-proj-your-key-here"
#OPENAI_API_KEY = "SECRET REMOVED"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "SECRET REMOVED")

if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY not set!")
    print("   Set it via environment variable: $env:OPENAI_API_KEY = 'sk-...'")
    print("   Or edit config.py (not recommended for production)")


# ============================================================================
# Server Configuration
# ============================================================================
HOST = "0.0.0.0"  # Bind to all interfaces (use "127.0.0.1" for localhost only)
PORT = 8000  # Default port for InK Studio
RELOAD = True  # Hot-reload during development (set False in production)

# ============================================================================
# Model Configuration
# ============================================================================
DEFAULT_MODEL = "gpt-4o-mini"  # Fast, cost-effective model for most tasks
# Alternatives: "gpt-4", "gpt-4-turbo", "gpt-4o" for higher quality

# ============================================================================
# File Paths
# ============================================================================
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_AUDIO_DIR = BASE_DIR / "generated_audio"
PROMPTS_FILE = BASE_DIR / "prompts.json"
CANVAS_TYPES_FILE = BASE_DIR / "canvas_types.json"

# Ensure required directories exist
GENERATED_AUDIO_DIR.mkdir(exist_ok=True)

# ============================================================================
# Application Metadata
# ============================================================================
APP_NAME = "InK Studio"
APP_VERSION = "2.0.0"  # Updated with alignment, comparison, and editing features
APP_DESCRIPTION = "AI-powered document transformation with multi-canvas support, Excel alignment, and intelligent comparison"


# ============================================================================
# MCP Server Configuration
# ============================================================================

# Current MCP URL (your local deployment)
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8000/mcp/")

# Logical name for MCP (optional, recommended for portability)
MCP_LOGICAL_NAME = os.getenv("MCP_LOGICAL_NAME", "catalyst-mcp")
