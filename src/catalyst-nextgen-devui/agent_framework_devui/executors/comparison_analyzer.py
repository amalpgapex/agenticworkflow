from typing import Any
import logging
from agent_framework import ChatAgent, Executor, WorkflowContext, handler
from agent_framework_devui.executors.align import AlignmentResult
from agent_framework_devui.models.comparison_models import ComparisonAnalysis

logger = logging.getLogger(__name__)

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