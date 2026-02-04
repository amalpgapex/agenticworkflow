from asyncio.log import logger
from dataclasses import asdict

from agent_framework import WorkflowCheckpoint
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions


class CosmosDBCheckpointStorage:
    """Azure Cosmos DB-based checkpoint storage for distributed persistence."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_key: str,
        database_name: str,
        container_name: str = "checkpoints",
    ):
        """
        Initialize Cosmos DB checkpoint storage.

        Args:
            cosmos_endpoint: Azure Cosmos DB endpoint URL
            cosmos_key: Azure Cosmos DB primary/secondary key
            database_name: Name of the Cosmos DB database
            container_name: Name of the container (default: "checkpoints")
        """
        self.cosmos_endpoint = cosmos_endpoint
        self.cosmos_key = cosmos_key
        self.database_name = database_name
        self.container_name = container_name
        self.client: CosmosClient | None = None
        self.database = None
        self.container = None
        logger.info(
            f"Initialized Cosmos DB checkpoint storage: {database_name}/{container_name}"
        )

    async def initialize(self) -> None:
        """Initialize Cosmos DB client and ensure container exists."""
        try:
            # Create async Cosmos client
            self.client = CosmosClient(
                url=self.cosmos_endpoint, credential=self.cosmos_key
            )

            # Get database reference
            self.database = self.client.get_database_client(self.database_name)

            # Get container reference
            self.container = self.database.get_container_client(self.container_name)

            # Test connection by reading container properties
            await self.container.read()
            logger.info(
                f"Successfully connected to Cosmos DB: {self.database_name}/{self.container_name}"
            )
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to initialize Cosmos DB checkpoint storage: {e}")
            raise

    async def close(self) -> None:
        """Close Cosmos DB client connection."""
        if self.client:
            await self.client.close()
            logger.info("Cosmos DB checkpoint storage connection closed")

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> str:
        """Save a checkpoint to Cosmos DB."""
        if not self.container:
            raise RuntimeError(
                "Cosmos DB not initialized. Call initialize() first."
            )

        checkpoint_dict = asdict(checkpoint)
        checkpoint_dict["id"] = checkpoint.checkpoint_id
        checkpoint_dict["partition_key"] = checkpoint.workflow_id

        try:
            await self.container.upsert_item(checkpoint_dict)
            logger.info(
                f"Saved checkpoint {checkpoint.checkpoint_id} to Cosmos DB"
            )
            return checkpoint.checkpoint_id
        except exceptions.CosmosHttpResponseError as e:
            logger.error(
                f"Failed to save checkpoint {checkpoint.checkpoint_id}: {e}"
            )
            raise

    async def load_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        """Load a checkpoint from Cosmos DB by ID."""
        if not self.container:
            raise RuntimeError(
                "Cosmos DB not initialized. Call initialize() first."
            )

        try:
            # Query for checkpoint by ID since we don't have partition key
            query = "SELECT * FROM c WHERE c.id = @checkpoint_id"
            parameters = [{"name": "@checkpoint_id", "value": checkpoint_id}]

            async for item in self.container.query_items(
                query=query, parameters=parameters # type: ignore
            ):
                # Remove Cosmos DB system properties before creating checkpoint
                item_copy = {
                    k: v for k, v in item.items() if not k.startswith("_")
                }
                checkpoint = WorkflowCheckpoint(**item_copy)
                logger.info(f"Loaded checkpoint {checkpoint_id} from Cosmos DB")
                return checkpoint

            logger.info(f"Checkpoint {checkpoint_id} not found in Cosmos DB")
            return None
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            raise

    async def list_checkpoint_ids(
        self, workflow_id: str | None = None
    ) -> list[str]:
        """List checkpoint IDs, optionally filtered by workflow_id."""
        if not self.container:
            raise RuntimeError(
                "Cosmos DB not initialized. Call initialize() first."
            )

        try:
            checkpoint_ids: list[str] = []
            if workflow_id:
                # Use partition key for efficient query
                query = "SELECT c.id FROM c"
                async for item in self.container.query_items(
                    query=query, partition_key=workflow_id
                ):
                    checkpoint_ids.append(item.get("id")) # type: ignore
            else:
                # Query all checkpoints without partition key filter
                query = "SELECT c.id FROM c"
                async for item in self.container.query_items(query=query):
                    checkpoint_ids.append(item.get("id")) # type: ignore

            logger.info(
                f"Listed {len(checkpoint_ids)} checkpoint IDs"
                + (f" for workflow {workflow_id}" if workflow_id else "")
            )
            return checkpoint_ids
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to list checkpoint IDs: {e}")
            raise

    async def list_checkpoints(
        self, workflow_id: str | None = None
    ) -> list[WorkflowCheckpoint]:
        """List all checkpoint objects, optionally filtered by workflow_id."""
        if not self.container:
            raise RuntimeError(
                "Cosmos DB not initialized. Call initialize() first."
            )

        try:
            checkpoints: list[WorkflowCheckpoint] = []
            if workflow_id:
                # Use partition key for efficient query
                query = "SELECT * FROM c"
                async for item in self.container.query_items(
                    query=query, partition_key=workflow_id
                ):
                    # Remove Cosmos DB system properties
                    item_copy = {
                        k: v for k, v in item.items() if not k.startswith("_")
                    }
                    checkpoints.append(WorkflowCheckpoint(**item_copy))
            else:
                # Query all checkpoints without partition key filter
                query = "SELECT * FROM c"
                async for item in self.container.query_items(query=query):
                    # Remove Cosmos DB system properties
                    item_copy = {
                        k: v for k, v in item.items() if not k.startswith("_")
                    }
                    checkpoints.append(WorkflowCheckpoint(**item_copy))

            logger.info(
                f"Listed {len(checkpoints)} checkpoints"
                + (f" for workflow {workflow_id}" if workflow_id else "")
            )
            return checkpoints
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to list checkpoints: {e}")
            raise

    async def delete_checkpoint(self, checkpoint_id: str, workflow_id: str) -> bool:
        """Delete a checkpoint by ID. Requires workflow_id as partition key."""
        if not self.container:
            raise RuntimeError(
                "Cosmos DB not initialized. Call initialize() first."
            )

        try:
            await self.container.delete_item(
                item=checkpoint_id, partition_key=workflow_id
            )
            logger.info(f"Deleted checkpoint {checkpoint_id} from Cosmos DB")
            return True
        except exceptions.CosmosResourceNotFoundError:
            logger.info(f"Checkpoint {checkpoint_id} not found in Cosmos DB")
            return False
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            raise