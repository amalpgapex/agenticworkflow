"""
Pydantic models and schemas for workflow and project management
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class WorkflowStep(BaseModel):
    """Individual step within a workflow"""
    step_id: str = Field(..., description="Unique identifier for the step")
    step_type: str = Field(..., description="Type of step (e.g., 'transform', 'analyze', 'generate')")
    step_name: str = Field(..., description="Human-readable step name")
    config: Dict[str, Any] = Field(default_factory=dict, description="Step configuration")
    order: int = Field(..., description="Step execution order")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "step_id": "step_001",
            "step_type": "transform",
            "step_name": "Document Analysis",
            "config": {"model": "gpt-4", "temperature": 0.7},
            "order": 1
        }
    })


class WorkflowBase(BaseModel):
    """Base workflow model with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    canvas_type: Optional[str] = Field(None, description="Canvas type identifier")
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT, description="Workflow status")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow"""
    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating an existing workflow"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    canvas_type: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    steps: Optional[List[WorkflowStep]] = None
    metadata: Optional[Dict[str, Any]] = None


class Workflow(WorkflowBase):
    """Complete workflow model with all fields including Cosmos DB fields"""
    id: str = Field(..., description="Cosmos DB document ID")
    CreatedBy: str = Field(..., description="User ID who created the workflow")
    CreatedAt: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    UpdatedAt: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "workflow_123",
                "name": "Document Transformation Pipeline",
                "description": "Transform and analyze documents using AI",
                "canvas_type": "transformation",
                "status": "active",
                "CreatedBy": "user@example.com",
                "CreatedAt": "2025-12-30T10:00:00Z",
                "UpdatedAt": "2025-12-30T10:00:00Z",
                "steps": [
                    {
                        "step_id": "step_001",
                        "step_type": "transform",
                        "step_name": "Extract Text",
                        "config": {},
                        "order": 1
                    }
                ],
                "metadata": {"tags": ["analysis", "transformation"]}
            }
        }
    )


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows"""
    total: int = Field(..., description="Total number of workflows")
    workflows: List[Workflow] = Field(..., description="List of workflows")


class WorkflowResponse(BaseModel):
    """Response model for single workflow operations"""
    success: bool = Field(..., description="Operation success status")
    workflow: Optional[Workflow] = Field(None, description="Workflow data")
    message: Optional[str] = Field(None, description="Response message")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ProjectStatus(str, Enum):
    """Project status enumeration"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectBase(BaseModel):
    """Base project model with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING, description="Project status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class Project(ProjectBase):
    """Complete project model with all fields including Cosmos DB fields"""
    id: str = Field(..., description="Cosmos DB document ID")
    CreatedBy: str = Field(..., description="User ID who created the project")
    CreatedAt: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    UpdatedAt: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "project_123",
                "name": "Document Processing Pipeline",
                "description": "AI-powered document analysis and transformation",
                "status": "in_progress",
                "CreatedBy": "user@example.com",
                "CreatedAt": "2025-12-30T10:00:00Z",
                "UpdatedAt": "2025-12-30T10:00:00Z",
                "metadata": {"tags": ["automation", "analysis"]}
            }
        }
    )


class ProjectListResponse(BaseModel):
    """Response model for listing projects"""
    total: int = Field(..., description="Total number of projects")
    projects: List[Project] = Field(..., description="List of projects")


class ProjectResponse(BaseModel):
    """Response model for single project operations"""
    success: bool = Field(..., description="Operation success status")
    project: Optional[Project] = Field(None, description="Project data")
    message: Optional[str] = Field(None, description="Response message")
