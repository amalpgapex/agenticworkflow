# Copyright (c) Microsoft. All rights reserved.

"""Document Comparison Workflow using Semantic Alignment.

This workflow demonstrates:
1. Semantic Alignment - Matches chunks from two documents using embeddings
2. Comparison Analysis - Analyzes aligned chunks to identify differences
3. Summary Generation - Creates a comprehensive comparison report

Use case: Compare two versions of a document (e.g., before/after edits,
original vs. translated, different drafts) by aligning similar sections
and highlighting meaningful changes.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add parent directory to Python path for imports


from agent_framework import ChatAgent, Executor, WorkflowBuilder, WorkflowContext, handler
from executors import AlignmentInput, AlignmentResult, SemanticAlignmentExecutor
from _utils import create_foundry_agent
from pydantic import BaseModel, Field
from typing_extensions import Never

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

@dataclass
class ComparisonAnalysis:
    """Analysis of differences between aligned chunks."""

    alignment_summary: str
    total_alignments: int
    unaligned_count: int
    detailed_comparisons: list[dict[str, Any]]


# ============================================================================
# Executors
# ============================================================================
class SampleDataProvider(Executor):
    """
    Provides sample input data for the comparison workflow.
    
    This executor is primarily for demonstration purposes.
    """

    id: str = "SampleDataProvider"
    
    @handler
    async def handle_request(
        self, _: str, ctx: WorkflowContext[AlignmentInput, None]
    ) -> None:
        """Provide sample input data.

        Args:
            _: No input expected
            ctx: Workflow context for sending messages
        """
        sample_input = build_demo_input()
        logger.info("Providing sample document comparison input")
        await ctx.send_message(sample_input)

class ComparisonAnalyzer(Executor):
    """
    Analyzes aligned chunks to identify and describe differences.
    
    Takes alignment results and produces a detailed comparison analysis
    of what changed between the two documents.
    """

    agent: ChatAgent | None

    def __init__(self, agent: ChatAgent | None = None, id: str = "ComparisonAnalyzer"):
        """Initialize the comparison analyzer.

        Args:
            agent: Optional Foundry agent for deep analysis
            id: Executor ID for workflow tracking
        """
        self.agent = agent
        super().__init__(id=id)

    def _analyze_without_agent(self, alignment_result: AlignmentResult) -> ComparisonAnalysis:
        """Perform basic analysis without an AI agent."""
        detailed_comparisons = []

        for alignment in alignment_result.alignments:
            source_text = alignment["source_chunk"]["text"]
            target_text = alignment["target_chunk"]["text"]
            similarity = alignment["similarity_score"]

            # Simple difference detection
            is_identical = source_text.strip() == target_text.strip()
            word_diff = abs(len(source_text.split()) - len(target_text.split()))

            comparison = {
                "source_index": alignment["source_chunk"]["chunk_index"],
                "target_index": alignment["target_chunk"]["chunk_index"],
                "source_text": source_text[:100] + "..." if len(source_text) > 100 else source_text,
                "target_text": target_text[:100] + "..." if len(target_text) > 100 else target_text,
                "similarity": similarity,
                "identical": is_identical,
                "word_count_diff": word_diff,
                "status": "identical" if is_identical else ("similar" if similarity > 0.7 else "modified"),
            }
            detailed_comparisons.append(comparison)

        # Generate summary
        identical_count = sum(1 for c in detailed_comparisons if c["identical"])
        modified_count = len(detailed_comparisons) - identical_count

        summary = (
            f"Analyzed {alignment_result.aligned_count} aligned chunk pairs. "
            f"{identical_count} identical, {modified_count} modified. "
            f"{alignment_result.total_source_chunks - alignment_result.aligned_count} source chunks unaligned."
        )

        return ComparisonAnalysis(
            alignment_summary=summary,
            total_alignments=alignment_result.aligned_count,
            unaligned_count=len(alignment_result.unaligned_source_indices),
            detailed_comparisons=detailed_comparisons,
        )

    async def _analyze_with_agent(self, alignment_result: AlignmentResult) -> ComparisonAnalysis:
        """Perform deep analysis using AI agent."""
        if not self.agent:
            return self._analyze_without_agent(alignment_result)

        detailed_comparisons = []

        # Analyze each alignment with the agent
        for alignment in alignment_result.alignments[:10]:  # Limit to first 10 for demo
            source_text = alignment["source_chunk"]["text"]
            target_text = alignment["target_chunk"]["text"]
            similarity = alignment["similarity_score"]

            # Ask agent to analyze the difference
            prompt = f"""Compare these two text chunks and describe the key differences:

SOURCE: {source_text}

TARGET: {target_text}

Provide a concise summary of changes (1-2 sentences)."""

            try:
                response = await self.agent.run(prompt)
                analysis = response.text if hasattr(response, "text") else str(response)
            except Exception as e:
                logger.warning(f"Agent analysis failed: {e}")
                analysis = "Analysis unavailable"

            comparison = {
                "source_index": alignment["source_chunk"]["chunk_index"],
                "target_index": alignment["target_chunk"]["chunk_index"],
                "source_text": source_text[:100] + "..." if len(source_text) > 100 else source_text,
                "target_text": target_text[:100] + "..." if len(target_text) > 100 else target_text,
                "similarity": similarity,
                "analysis": analysis,
            }
            detailed_comparisons.append(comparison)

        # Generate overall summary
        summary = (
            f"AI-powered analysis of {alignment_result.aligned_count} aligned chunks. "
            f"{len(alignment_result.unaligned_source_indices)} source chunks unaligned."
        )

        return ComparisonAnalysis(
            alignment_summary=summary,
            total_alignments=alignment_result.aligned_count,
            unaligned_count=len(alignment_result.unaligned_source_indices),
            detailed_comparisons=detailed_comparisons,
        )

    @handler
    async def handle_analysis(
        self, alignment_result: AlignmentResult | dict[str, Any], ctx: WorkflowContext[ComparisonAnalysis]
    ) -> None:
        """Analyze alignment results.

        Args:
            alignment_result: Results from semantic alignment
            ctx: Workflow context for sending messages
        """
        # Parse input
        if isinstance(alignment_result, dict):
            try:
                alignment_result = AlignmentResult(**alignment_result)
            except Exception as e:
                logger.error(f"Failed to parse alignment result: {e}")
                return

        logger.info(f"Analyzing {alignment_result.aligned_count} alignments")

        # Perform analysis
        if self.agent:
            analysis = await self._analyze_with_agent(alignment_result)
        else:
            analysis = self._analyze_without_agent(alignment_result)

        logger.info(f"Analysis complete: {analysis.alignment_summary}")

        # Send to next executor
        await ctx.send_message(analysis)


class SummaryGenerator(Executor):
    """
    Generates a comprehensive summary report of the comparison.
    
    Takes the comparison analysis and produces a human-readable report.
    """

    agent: ChatAgent | None

    def __init__(self, agent: ChatAgent | None = None, id: str = "SummaryGenerator"):
        """Initialize the summary generator.

        Args:
            agent: Optional Foundry agent for rich summaries
            id: Executor ID for workflow tracking
        """
        self.agent = agent
        super().__init__(id=id)

    def _generate_basic_summary(self, analysis: ComparisonAnalysis) -> str:
        """Generate basic text summary without AI."""
        summary_parts = [
            "=" * 80,
            "DOCUMENT COMPARISON SUMMARY",
            "=" * 80,
            "",
            f"Total Alignments: {analysis.total_alignments}",
            f"Unaligned Chunks: {analysis.unaligned_count}",
            "",
            analysis.alignment_summary,
            "",
            "DETAILED COMPARISONS:",
            "-" * 80,
        ]

        for idx, comp in enumerate(analysis.detailed_comparisons[:5], 1):
            summary_parts.extend(
                [
                    f"\n{idx}. Chunks {comp['source_index']} → {comp['target_index']}",
                    f"   Similarity: {comp['similarity']:.2%}",
                    f"   Source: {comp['source_text']}",
                    f"   Target: {comp['target_text']}",
                ]
            )

            if "analysis" in comp:
                summary_parts.append(f"   Analysis: {comp['analysis']}")
            elif "status" in comp:
                summary_parts.append(f"   Status: {comp['status']}")

        if len(analysis.detailed_comparisons) > 5:
            summary_parts.append(f"\n... and {len(analysis.detailed_comparisons) - 5} more alignments")

        summary_parts.extend(["", "=" * 80])

        return "\n".join(summary_parts)

    async def _generate_ai_summary(self, analysis: ComparisonAnalysis) -> str:
        """Generate rich summary using AI agent."""
        if not self.agent:
            return self._generate_basic_summary(analysis)

        # Prepare data for agent
        comparison_data = "\n\n".join(
            [
                f"Alignment {i+1} (similarity: {c['similarity']:.2%}):\n"
                f"Source: {c['source_text']}\n"
                f"Target: {c['target_text']}\n"
                f"Analysis: {c.get('analysis', c.get('status', 'N/A'))}"
                for i, c in enumerate(analysis.detailed_comparisons[:5])
            ]
        )

        prompt = f"""Create a comprehensive summary of this document comparison:

{analysis.alignment_summary}

Key Statistics:
- Total alignments: {analysis.total_alignments}
- Unaligned chunks: {analysis.unaligned_count}

Sample Comparisons:
{comparison_data}

Provide:
1. Overall assessment of similarity
2. Key differences identified
3. Notable patterns or trends
4. Recommendations (if applicable)

Keep the summary concise but informative."""

        try:
            response = await self.agent.run(prompt)
            summary = response.text if hasattr(response, "text") else str(response)
            return f"{'=' * 80}\nAI-GENERATED COMPARISON SUMMARY\n{'=' * 80}\n\n{summary}\n\n{'=' * 80}"
        except Exception as e:
            logger.warning(f"AI summary generation failed: {e}, falling back to basic summary")
            return self._generate_basic_summary(analysis)

    @handler
    async def handle_summary(
        self, analysis: ComparisonAnalysis, ctx: WorkflowContext[Never, str]
    ) -> None:
        """Generate summary report.

        Args:
            analysis: Comparison analysis from previous executor
            ctx: Workflow context for yielding output
        """
        logger.info("Generating comparison summary")

        # Generate summary
        if self.agent:
            summary = await self._generate_ai_summary(analysis)
        else:
            summary = self._generate_basic_summary(analysis)

        logger.info("Summary generation complete")

        # Yield final output
        await ctx.yield_output(summary)


# ============================================================================
# Workflow Builder
# ============================================================================


async def create_comparison_workflow(use_ai: bool = False) -> Any:
    """Create the document comparison workflow.

    Args:
        use_ai: Whether to use AI agents for analysis and summaries

    Returns:
        Configured workflow instance
    """
    # Create Sample Data Provider (for DevUI demo)
    sample_data_provider = SampleDataProvider(id="SampleDataProvider")
    
    # Create alignment executor
    alignment_executor = SemanticAlignmentExecutor(id="SemanticAlignment")

    # Create comparison analyzer
    if use_ai:
        try:
            analyzer_agent = await create_foundry_agent(
                agent_name="ComparisonAnalyzer",
                instructions="You are an expert at analyzing text differences. Provide clear, concise descriptions of changes.",
            )
            comparison_analyzer = ComparisonAnalyzer(agent=analyzer_agent, id="ComparisonAnalyzer") # type: ignore
        except Exception as e:
            logger.warning(f"Failed to create analyzer agent: {e}, using basic mode")
            comparison_analyzer = ComparisonAnalyzer(agent=None, id="ComparisonAnalyzer")
    else:
        comparison_analyzer = ComparisonAnalyzer(agent=None, id="ComparisonAnalyzer")

    # Create summary generator
    if use_ai:
        try:
            summary_agent = await create_foundry_agent(
                agent_name="SummaryGenerator",
                instructions="You are an expert at creating comprehensive document comparison summaries.",
            )
            summary_generator = SummaryGenerator(agent=summary_agent, id="SummaryGenerator") # type: ignore
        except Exception as e:
            logger.warning(f"Failed to create summary agent: {e}, using basic mode")
            summary_generator = SummaryGenerator(agent=None, id="SummaryGenerator")
    else:
        summary_generator = SummaryGenerator(agent=None, id="SummaryGenerator")

    # Build workflow: Alignment → Analysis → Summary
    workflow = (
        WorkflowBuilder(
            name="Document Comparison Workflow",
            description="Semantic alignment → Comparison analysis → Summary generation",
        )
        .set_start_executor(sample_data_provider)
        .add_edge(sample_data_provider, alignment_executor)
        .add_edge(alignment_executor, comparison_analyzer)
        .add_edge(comparison_analyzer, summary_generator)
        .build()
    )

    return workflow


# Create the workflow for DevUI (basic mode by default)
workflow = asyncio.run(create_comparison_workflow(use_ai=False))


# ============================================================================
# Demo & Main
# ============================================================================


async def demo():
    """Run a demonstration of the comparison workflow."""
    print("\n" + "=" * 80)
    print("DOCUMENT COMPARISON WORKFLOW DEMO")
    print("=" * 80 + "\n")

    input_data = build_demo_input()

    # Create and run workflow
    wf = await create_comparison_workflow(use_ai=False)

    print("Processing document comparison...\n")

    # Stream workflow events
    from agent_framework import WorkflowOutputEvent

    async for event in wf.run_stream(input_data.model_dump()):
        if isinstance(event, WorkflowOutputEvent):
            print(event.data)


def build_demo_input() -> AlignmentInput:
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
    return AlignmentInput(
        source_chunks=source_chunks, target_chunks=target_chunks, similarity_threshold=0.3
    )


def main():
    """Launch the comparison workflow in DevUI."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    # Check if running demo
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            asyncio.run(demo())
            return
        if sys.argv[1] == "--sample-data":
            sample_input = build_demo_input()            
            print(sample_input.model_dump_json(indent=2))
            return

    # Launch DevUI server
    from agent_framework.devui import serve

    logger.info("Starting Document Comparison Workflow")
    logger.info("Available at: http://localhost:8090")
    logger.info(f"Entity ID: workflow_{workflow.name.replace(' ', '')}")
    logger.info("\nWorkflow stages:")
    logger.info("  1. Semantic Alignment - Matches chunks using embeddings")
    logger.info("  2. Comparison Analysis - Identifies differences")
    logger.info("  3. Summary Generation - Creates comparison report")
    logger.info("\nTo run demo, use: python -m agent_framework_devui.workflows.compare_contents --demo")

    # Launch server with the workflow
    serve(entities=[workflow], port=8090)


if __name__ == "__main__":
    main()
