"""
InK Studio - Startup Script
Launches the FastAPI server with hot-reload for development
"""

import uvicorn
from config import HOST, PORT, RELOAD

if __name__ == "__main__":
    print("=" * 60)
    print(f"  InK Studio")
    print(f"  Starting server at http://{HOST}:{PORT}")
    print("=" * 60)
    
    uvicorn.run(
        #"app_fastapi:app",
        # MCP Server
        "app_host:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        reload_dirs=[".", "templates"],
        log_level="info"
    )

