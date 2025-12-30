"""
Workflow API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from app.models import (
    Workflow,
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowListResponse,
    WorkflowResponse,
    ErrorResponse
)
from app.auth import get_current_user
from app.database import cosmos_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=WorkflowListResponse,
    summary="Get all workflows for authenticated user",
    description="Retrieve all workflows created by the authenticated user"
)
async def get_workflows(
    current_user: str = Depends(get_current_user),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of workflows to return"),
    status_filter: Optional[str] = Query(None, description="Filter by workflow status")
):
    """
    Get all workflows for the authenticated user
    
    - **limit**: Optional limit on number of results (1-100)
    - **status_filter**: Optional filter by workflow status (draft, active, completed, archived)
    """
    try:
        workflows = await cosmos_client.get_workflows_by_user(
            user_id=current_user,
            max_items=limit
        )
        
        # Apply status filter if provided
        if status_filter:
            workflows = [w for w in workflows if w.get("status") == status_filter]
        
        return WorkflowListResponse(
            total=len(workflows),
            workflows=workflows
        )
        
    except Exception as e:
        logger.error(f"Error fetching workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflows: {str(e)}"
        )


@router.get(
    "/{workflow_id}",
    response_model=Workflow,
    summary="Get a specific workflow",
    description="Retrieve a specific workflow by ID for the authenticated user"
)
async def get_workflow(
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get a specific workflow by ID
    
    - **workflow_id**: The unique identifier of the workflow
    """
    try:
        workflow = await cosmos_client.get_workflow_by_id(
            workflow_id=workflow_id,
            user_id=current_user
        )
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return workflow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow: {str(e)}"
        )


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow",
    description="Create a new workflow for the authenticated user"
)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: str = Depends(get_current_user)
):
    """
    Create a new workflow
    
    - **name**: Workflow name (required)
    - **description**: Workflow description (optional)
    - **canvas_type**: Canvas type identifier (optional)
    - **status**: Workflow status (default: draft)
    - **steps**: List of workflow steps (optional)
    - **metadata**: Additional metadata (optional)
    """
    try:
        # Prepare workflow document
        workflow_doc = workflow_data.model_dump()
        workflow_doc["id"] = str(uuid.uuid4())
        workflow_doc["CreatedBy"] = current_user
        workflow_doc["CreatedAt"] = datetime.utcnow().isoformat()
        workflow_doc["UpdatedAt"] = datetime.utcnow().isoformat()
        
        # Create workflow in Cosmos DB
        created_workflow = await cosmos_client.create_workflow(workflow_doc)
        
        return WorkflowResponse(
            success=True,
            workflow=created_workflow,
            message="Workflow created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update a workflow",
    description="Update an existing workflow for the authenticated user"
)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    current_user: str = Depends(get_current_user)
):
    """
    Update an existing workflow
    
    - **workflow_id**: The unique identifier of the workflow
    - All fields are optional; only provided fields will be updated
    """
    try:
        # First, fetch the existing workflow
        existing_workflow = await cosmos_client.get_workflow_by_id(
            workflow_id=workflow_id,
            user_id=current_user
        )
        
        if not existing_workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Update only provided fields
        update_data = workflow_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing_workflow[key] = value
        
        # Update timestamp
        existing_workflow["UpdatedAt"] = datetime.utcnow().isoformat()
        
        # Update in Cosmos DB
        updated_workflow = await cosmos_client.update_workflow(
            workflow_id=workflow_id,
            user_id=current_user,
            workflow_data=existing_workflow
        )
        
        return WorkflowResponse(
            success=True,
            workflow=updated_workflow,
            message="Workflow updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workflow",
    description="Delete a workflow for the authenticated user"
)
async def delete_workflow(
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete a workflow
    
    - **workflow_id**: The unique identifier of the workflow
    """
    try:
        deleted = await cosmos_client.delete_workflow(
            workflow_id=workflow_id,
            user_id=current_user
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}"
        )


@router.post(
    "/{workflow_id}/duplicate",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a workflow",
    description="Create a copy of an existing workflow"
)
async def duplicate_workflow(
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Duplicate an existing workflow
    
    - **workflow_id**: The unique identifier of the workflow to duplicate
    """
    try:
        # Fetch the existing workflow
        existing_workflow = await cosmos_client.get_workflow_by_id(
            workflow_id=workflow_id,
            user_id=current_user
        )
        
        if not existing_workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Create a copy with new ID and updated metadata
        new_workflow = existing_workflow.copy()
        new_workflow["id"] = str(uuid.uuid4())
        new_workflow["name"] = f"{existing_workflow['name']} (Copy)"
        new_workflow["CreatedAt"] = datetime.utcnow().isoformat()
        new_workflow["UpdatedAt"] = datetime.utcnow().isoformat()
        new_workflow["status"] = "draft"
        
        # Create the duplicate in Cosmos DB
        created_workflow = await cosmos_client.create_workflow(new_workflow)
        
        return WorkflowResponse(
            success=True,
            workflow=created_workflow,
            message="Workflow duplicated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate workflow: {str(e)}"
        )
