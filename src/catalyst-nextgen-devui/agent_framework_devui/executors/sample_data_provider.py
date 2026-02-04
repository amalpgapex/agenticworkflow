from typing import Any
from agent_framework import Executor, WorkflowContext, handler
from agent_framework_devui.models.comparison_models import AlignmentInput, ComparisonRequest
import logging
logger = logging.getLogger(__name__)


class SampleDataProvider(Executor):
    """
    Provides sample input data for the comparison workflow.
    
    This executor is primarily for demonstration purposes.
    """

    id: str = "SampleDataProvider"
    sample_data: AlignmentInput
    
    def __init__(self, id: str | None) -> None:
        self.id = id or self.id
        self.build_demo_input()
        super().__init__(self.id)

    def build_demo_input(self) -> None:
        """Build sample input data for the demo."""
        # Sample document chunks
        source_chunks = [
            {
                "text": "The quick brown fox jumps over the lazy dog in the forest.",
                "document_id": "doc_v1",
                "chunk_index": 0,
            },
            {
                "text": "Python is a high-level, interpreted programming language known for simplicity.",
                "document_id": "doc_v1",
                "chunk_index": 1,
            },
            {
                "text": "Machine learning algorithms require large datasets for training.",
                "document_id": "doc_v1",
                "chunk_index": 2,
            },
            {
                "text": "The Earth orbits around the Sun in an elliptical path.",
                "document_id": "doc_v1",
                "chunk_index": 3,
            },
        ]

        target_chunks = [
            {
                "text": "A fast brown fox leaps over a sleeping dog in the woods.",
                "document_id": "doc_v2",
                "chunk_index": 0,
            },
            {
                "text": "Python is an interpreted, high-level programming language designed for code readability.",
                "document_id": "doc_v2",
                "chunk_index": 1,
            },
            {
                "text": "Deep learning models use neural networks with multiple layers.",
                "document_id": "doc_v2",
                "chunk_index": 2,
            },
            {
                "text": "JavaScript is a versatile scripting language for web development.",
                "document_id": "doc_v2",
                "chunk_index": 3,
            },
        ]

        # Create input
        self.sample_data = AlignmentInput(
            source_chunks=source_chunks, target_chunks=target_chunks, similarity_threshold=0.3
        )

    @handler
    async def handle_request(
        self, _: ComparisonRequest, ctx: WorkflowContext[AlignmentInput, None]
    ) -> None:
        """Provide sample input data.

        Args:
            _: No input expected
            ctx: Workflow context for sending messages
        """        
        logger.info("Providing sample document comparison input")
        await ctx.send_message(self.sample_data)