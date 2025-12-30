"""
Azure Cosmos DB client configuration and connection management
"""

import logging
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class CosmosDBClient:
    """Singleton Cosmos DB client for managing database connections"""
    
    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.workflows_container = None
        self._connected = False
    
    async def initialize(self):
        """Initialize Cosmos DB client and get database/container references"""
        try:
            # Create Cosmos client
            self.client = CosmosClient(
                url=settings.COSMOS_ENDPOINT,
                credential=settings.COSMOS_KEY
            )
            
            # Get database reference
            self.database = self.client.get_database_client(settings.COSMOS_DATABASE)
            
            # Get container reference for workflows
            self.workflows_container = self.database.get_container_client(
                settings.COSMOS_CONTAINER
            )
            
            # Test connection by reading container properties
            await self.workflows_container.read()
            
            self._connected = True
            logger.info(f"Successfully connected to Cosmos DB: {settings.COSMOS_DATABASE}/{settings.COSMOS_CONTAINER}")
            
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            self._connected = False
            raise
    
    async def close(self):
        """Close Cosmos DB client connection"""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Cosmos DB connection closed")
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected
    
    async def get_workflows_by_user(
        self, 
        user_id: str, 
        max_items: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all workflows for a specific user
        
        Args:
            user_id: The authenticated user's ID (partition key)
            max_items: Optional limit on number of items to return
            
        Returns:
            List of workflow documents
        """
        if not self.workflows_container:
            raise Exception("Cosmos DB not initialized")
        
        try:
            # Query workflows by partition key (CreatedBy)
            query = "SELECT * FROM c WHERE c.CreatedBy = @userId ORDER BY c._ts DESC"
            parameters = [{"name": "@userId", "value": user_id}]
            
            items = []
            async for item in self.workflows_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id,
                max_item_count=max_items
            ):
                items.append(item)
            
            logger.info(f"Retrieved {len(items)} workflows for user: {user_id}")
            return items
            
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error querying workflows: {e}")
            raise
    
    async def get_workflow_by_id(
        self, 
        workflow_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific workflow by ID for a user
        
        Args:
            workflow_id: The workflow document ID
            user_id: The authenticated user's ID (partition key)
            
        Returns:
            Workflow document or None if not found
        """
        if not self.workflows_container:
            raise Exception("Cosmos DB not initialized")
        
        try:
            item = await self.workflows_container.read_item(
                item=workflow_id,
                partition_key=user_id
            )
            logger.info(f"Retrieved workflow {workflow_id} for user: {user_id}")
            return item
            
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Workflow {workflow_id} not found for user: {user_id}")
            return None
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error retrieving workflow: {e}")
            raise
    
    async def create_workflow(
        self, 
        workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new workflow document
        
        Args:
            workflow_data: Workflow document data (must include CreatedBy field)
            
        Returns:
            Created workflow document with generated id
        """
        if not self.workflows_container:
            raise Exception("Cosmos DB not initialized")
        
        if "CreatedBy" not in workflow_data:
            raise ValueError("Workflow data must include CreatedBy field")
        
        try:
            created_item = await self.workflows_container.create_item(
                body=workflow_data
            )
            logger.info(f"Created workflow {created_item['id']} for user: {workflow_data['CreatedBy']}")
            return created_item
            
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error creating workflow: {e}")
            raise
    
    async def update_workflow(
        self, 
        workflow_id: str,
        user_id: str,
        workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing workflow document
        
        Args:
            workflow_id: The workflow document ID
            user_id: The authenticated user's ID (partition key)
            workflow_data: Updated workflow data
            
        Returns:
            Updated workflow document
        """
        if not self.workflows_container:
            raise Exception("Cosmos DB not initialized")
        
        try:
            # Ensure id and partition key are set correctly
            workflow_data["id"] = workflow_id
            workflow_data["CreatedBy"] = user_id
            
            updated_item = await self.workflows_container.replace_item(
                item=workflow_id,
                body=workflow_data
            )
            logger.info(f"Updated workflow {workflow_id} for user: {user_id}")
            return updated_item
            
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Workflow {workflow_id} not found for user: {user_id}")
            raise
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error updating workflow: {e}")
            raise
    
    async def delete_workflow(
        self, 
        workflow_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a workflow document
        
        Args:
            workflow_id: The workflow document ID
            user_id: The authenticated user's ID (partition key)
            
        Returns:
            True if deleted successfully
        """
        if not self.workflows_container:
            raise Exception("Cosmos DB not initialized")
        
        try:
            await self.workflows_container.delete_item(
                item=workflow_id,
                partition_key=user_id
            )
            logger.info(f"Deleted workflow {workflow_id} for user: {user_id}")
            return True
            
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Workflow {workflow_id} not found for user: {user_id}")
            return False
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error deleting workflow: {e}")
            raise

        # ==================== PROJECT OPERATIONS ====================
    
        async def get_projects_by_user(
            self, 
            user_id: str, 
            max_items: Optional[int] = None
        ) -> List[Dict[str, Any]]:
            """
            Fetch all projects for a specific user
        
            Args:
                user_id: The authenticated user's ID (partition key)
                max_items: Optional limit on number of items to return
            
            Returns:
                List of project documents
            """
            if not self.workflows_container:
                raise Exception("Cosmos DB not initialized")
        
            try:
                # Query projects by partition key (CreatedBy) and type
                query = "SELECT * FROM c WHERE c.CreatedBy = @userId AND c.type = @type ORDER BY c._ts DESC"
                parameters = [
                    {"name": "@userId", "value": user_id},
                    {"name": "@type", "value": "project"}
                ]
            
                items = []
                async for item in self.workflows_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=user_id,
                    max_item_count=max_items
                ):
                    items.append(item)
            
                logger.info(f"Retrieved {len(items)} projects for user: {user_id}")
                return items
            
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error querying projects: {e}")
                raise
    
        async def get_project_by_id(
            self, 
            project_id: str, 
            user_id: str
        ) -> Optional[Dict[str, Any]]:
            """
            Fetch a specific project by ID for a user
        
            Args:
                project_id: The project document ID
                user_id: The authenticated user's ID (partition key)
            
            Returns:
                Project document or None if not found
            """
            if not self.workflows_container:
                raise Exception("Cosmos DB not initialized")
        
            try:
                item = await self.workflows_container.read_item(
                    item=project_id,
                    partition_key=user_id
                )
            
                # Verify it's a project document
                if item.get("type") != "project":
                    logger.warning(f"Document {project_id} is not a project for user: {user_id}")
                    return None
            
                logger.info(f"Retrieved project {project_id} for user: {user_id}")
                return item
            
            except exceptions.CosmosResourceNotFoundError:
                logger.warning(f"Project {project_id} not found for user: {user_id}")
                return None
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error retrieving project: {e}")
                raise
    
        async def create_project(
            self, 
            project_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """
            Create a new project document
        
            Args:
                project_data: Project document data (must include CreatedBy field)
            
            Returns:
                Created project document with generated id
            """
            if not self.workflows_container:
                raise Exception("Cosmos DB not initialized")
        
            if "CreatedBy" not in project_data:
                raise ValueError("Project data must include CreatedBy field")
        
            # Set document type
            project_data["type"] = "project"
        
            try:
                created_item = await self.workflows_container.create_item(
                    body=project_data
                )
                logger.info(f"Created project {created_item['id']} for user: {project_data['CreatedBy']}")
                return created_item
            
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error creating project: {e}")
                raise
    
        async def update_project(
            self, 
            project_id: str,
            user_id: str,
            project_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """
            Update an existing project document
        
            Args:
                project_id: The project document ID
                user_id: The authenticated user's ID (partition key)
                project_data: Updated project data
            
            Returns:
                Updated project document
            """
            if not self.workflows_container:
                raise Exception("Cosmos DB not initialized")
        
            try:
                # Ensure id, partition key, and type are set correctly
                project_data["id"] = project_id
                project_data["CreatedBy"] = user_id
                project_data["type"] = "project"
            
                updated_item = await self.workflows_container.replace_item(
                    item=project_id,
                    body=project_data
                )
                logger.info(f"Updated project {project_id} for user: {user_id}")
                return updated_item
            
            except exceptions.CosmosResourceNotFoundError:
                logger.warning(f"Project {project_id} not found for user: {user_id}")
                raise
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error updating project: {e}")
                raise
    
        async def delete_project(
            self, 
            project_id: str,
            user_id: str
        ) -> bool:
            """
            Delete a project document
        
            Args:
                project_id: The project document ID
                user_id: The authenticated user's ID (partition key)
            
            Returns:
                True if deleted successfully
            """
            if not self.workflows_container:
                raise Exception("Cosmos DB not initialized")
        
            try:
                await self.workflows_container.delete_item(
                    item=project_id,
                    partition_key=user_id
                )
                logger.info(f"Deleted project {project_id} for user: {user_id}")
                return True
            
            except exceptions.CosmosResourceNotFoundError:
                logger.warning(f"Project {project_id} not found for user: {user_id}")
                return False
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error deleting project: {e}")
                raise

# Global singleton instance
cosmos_client = CosmosDBClient()
