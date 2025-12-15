"""
Configuration Template
Copy this file to config.py and update with your values
"""

import os
from pathlib import Path

# ============================================================================
# API CONFIGURATION
# ============================================================================

# OpenAI API Key - Get from https://platform.openai.com/api-keys
# Option 1: Set as environment variable (recommended)
# Option 2: Replace with your actual key below
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-proj-your-api-key-here")

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

HOST = "0.0.0.0"      # Listen on all interfaces
PORT = 8000           # Server port
RELOAD = True         # Auto-reload on code changes (disable in production)

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

DEFAULT_MODEL = "gpt-4o-mini"  # OpenAI model to use
# Other options: "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"

# ============================================================================
# FILE PATHS
# ============================================================================

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_AUDIO_DIR = BASE_DIR / "generated_audio"
PROMPTS_FILE = BASE_DIR / "prompts.json"
CANVAS_TYPES_FILE = BASE_DIR / "canvas_types.json"

# Ensure directories exist
GENERATED_AUDIO_DIR.mkdir(exist_ok=True)

# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_NAME = "InK Studio"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "AI-powered document transformation with multi-canvas support"

