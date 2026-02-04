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

import logging
from typing import Any

from agent_framework import WorkflowBuilder, Workflow
from agent_framework_devui.executors import (
    SemanticAlignment, 
    SampleDataProvider,
    ComparisonAnalyzer,
    SummaryGenerator
)
from .._utils import create_foundry_agent

logger = logging.getLogger(__name__)

# ============================================================================
# Workflow Builder
# ============================================================================

async def create_comparison_workflow(use_ai: bool = False) -> Workflow:
    """Create the document comparison workflow.

    Args:
        use_ai: Whether to use AI agents for analysis and summaries

    Returns:
        Configured workflow instance
    """
    # Create Sample Data Provider (for DevUI demo)
    sample_data_provider = SampleDataProvider(id="SampleDataProvider")
    
    # Create alignment executor
    alignment_executor = SemanticAlignment(id="SemanticAlignment")

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
