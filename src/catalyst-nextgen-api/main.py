"""
Catalyst NextGen API - FastAPI Backend
Manages workflows and project data with Azure Cosmos DB
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import cosmos_client
from app.routes import workflows, projects

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Catalyst NextGen API...")
    # Initialize Cosmos DB connection
    await cosmos_client.initialize()
    logger.info("Cosmos DB connection established")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Catalyst NextGen API...")
    await cosmos_client.close()


# Initialize FastAPI app
app = FastAPI(
    title="Catalyst NextGen API",
    description="Backend API for workflow management with Azure Cosmos DB",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "catalyst-nextgen-api",
        "cosmos_db": cosmos_client.is_connected()
    }


# Include routers
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
