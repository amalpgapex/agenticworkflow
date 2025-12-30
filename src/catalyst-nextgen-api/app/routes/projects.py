"""
Project API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from app.models import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectListResponse,
    ProjectResponse,
)
from app.auth import get_current_user
from app.database import cosmos_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="Get all projects for authenticated user",
    description="Retrieve all projects created by the authenticated user"
)
async def get_projects(
    current_user: str = Depends(get_current_user),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of projects to return"),
    status_filter: Optional[str] = Query(None, description="Filter by project status")
):
    """
    Get all projects for the authenticated user
    
    - **limit**: Optional limit on number of results (1-100)
    - **status_filter**: Optional filter by project status (planning, in_progress, on_hold, completed, archived)
    """
    try:
        projects = await cosmos_client.get_projects_by_user(
            user_id=current_user,
            max_items=limit
        )
        
        # Apply status filter if provided
        if status_filter:
            projects = [p for p in projects if p.get("status") == status_filter]
        
        return ProjectListResponse(
            total=len(projects),
            projects=projects
        )
        
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )


@router.get(
    "/{project_id}",
    response_model=Project,
    summary="Get a specific project",
    description="Retrieve a specific project by ID for the authenticated user"
)
async def get_project(
    project_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get a specific project by ID
    
    - **project_id**: The unique identifier of the project
    """
    try:
        project = await cosmos_client.get_project_by_id(
            project_id=project_id,
            user_id=current_user
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project for the authenticated user"
)
async def create_project(
    project_data: ProjectCreate,
    current_user: str = Depends(get_current_user)
):
    """
    Create a new project
    
    - **name**: Project name (required)
    - **description**: Project description (optional)
    - **status**: Project status (default: planning)
    - **metadata**: Additional metadata (optional)
    """
    try:
        # Prepare project document
        project_doc = project_data.model_dump()
        project_doc["id"] = str(uuid.uuid4())
        project_doc["CreatedBy"] = current_user
        project_doc["CreatedAt"] = datetime.utcnow().isoformat()
        project_doc["UpdatedAt"] = datetime.utcnow().isoformat()
        project_doc["type"] = "project"  # Set document type
        
        # Create project in Cosmos DB
        created_project = await cosmos_client.create_project(project_doc)
        
        return ProjectResponse(
            success=True,
            project=created_project,
            message="Project created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    description="Update an existing project for the authenticated user"
)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: str = Depends(get_current_user)
):
    """
    Update an existing project
    
    - **project_id**: The unique identifier of the project
    - All fields are optional; only provided fields will be updated
    """
    try:
        # First, fetch the existing project
        existing_project = await cosmos_client.get_project_by_id(
            project_id=project_id,
            user_id=current_user
        )
        
        if not existing_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        # Update only provided fields
        update_data = project_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing_project[key] = value
        
        # Update timestamp
        existing_project["UpdatedAt"] = datetime.utcnow().isoformat()
        
        # Update in Cosmos DB
        updated_project = await cosmos_client.update_project(
            project_id=project_id,
            user_id=current_user,
            project_data=existing_project
        )
        
        return ProjectResponse(
            success=True,
            project=updated_project,
            message="Project updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Delete a project for the authenticated user"
)
async def delete_project(
    project_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete a project
    
    - **project_id**: The unique identifier of the project
    """
    try:
        deleted = await cosmos_client.delete_project(
            project_id=project_id,
            user_id=current_user
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.post(
    "/{project_id}/duplicate",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a project",
    description="Create a copy of an existing project"
)
async def duplicate_project(
    project_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Duplicate an existing project
    
    - **project_id**: The unique identifier of the project to duplicate
    """
    try:
        # Fetch the existing project
        existing_project = await cosmos_client.get_project_by_id(
            project_id=project_id,
            user_id=current_user
        )
        
        if not existing_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        # Create a copy with new ID and updated metadata
        new_project = existing_project.copy()
        new_project["id"] = str(uuid.uuid4())
        new_project["name"] = f"{existing_project['name']} (Copy)"
        new_project["CreatedAt"] = datetime.utcnow().isoformat()
        new_project["UpdatedAt"] = datetime.utcnow().isoformat()
        new_project["status"] = "planning"
        new_project["type"] = "project"
        
        # Create the duplicate in Cosmos DB
        created_project = await cosmos_client.create_project(new_project)
        
        return ProjectResponse(
            success=True,
            project=created_project,
            message="Project duplicated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate project: {str(e)}"
        )
