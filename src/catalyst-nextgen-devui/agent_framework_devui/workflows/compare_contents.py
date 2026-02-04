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

async def create_comparison_workflow() -> Workflow:
    """Create the document comparison workflow.    

    Returns:
        Configured workflow instance
    """
    # Create Sample Data Provider (for DevUI demo)
    sample_data_provider = SampleDataProvider(id="SampleDataProvider")
    
    # Create alignment executor
    alignment_executor = SemanticAlignment(id="SemanticAlignment")

    # Create comparison analyzer
    comparison_analyzer = ComparisonAnalyzer(id="ComparisonAnalyzer")

    # Create summary generator
    summary_generator = SummaryGenerator(id="SummaryGenerator")

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
