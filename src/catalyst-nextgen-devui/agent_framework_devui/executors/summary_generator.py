import logging
from typing import Any, Never

from agent_framework import ChatAgent, Executor, WorkflowContext, handler
from agent_framework_devui.models.comparison_models import ComparisonAnalysis

logger = logging.getLogger(__name__)

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
