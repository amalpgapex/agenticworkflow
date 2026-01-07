
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
import json

class ComparisonSummaryTool(AgenticTool):
    """Extract summaries from comparison analysis outputs for LLM consumption"""

    def __init__(self):
        super().__init__("comparison_summary", "Extract key statistics from comparison analysis")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Extract summaries from previous comparison steps"""
        try:
            step_history = context.get('step_history', [])
            if not step_history or len(step_history) < 4:
                return "Error: Insufficient analysis steps completed"

            if streaming_callback:
                streaming_callback("📊 Extracting key statistics from analysis...")

            summaries = []

            for idx, step_data in enumerate(step_history[:4]):
                output = step_data.get('output', '')

                if output.startswith('CHUNKING_RESULT:'):
                    json_data = output.replace('CHUNKING_RESULT:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summaries.append(f"**Chunking Analysis:**\n- Strategy: {data.get('strategy')}\n- Document 1: {data.get('doc1_word_count')} words in {len(data.get('doc1_chunks', []))} chunks\n- Document 2: {data.get('doc2_word_count')} words in {len(data.get('doc2_chunks', []))} chunks\n- Estimated pages: ~{data.get('estimated_pages')}")
                    except:
                        pass

                elif output.startswith('ENHANCED_DIFF:'):
                    json_data = output.replace('ENHANCED_DIFF:', '').strip()
                    try:
                        data = json.loads(json_data)
                        stats = data.get('statistics', {})
                        summaries.append(f"**Visual Diff Statistics:**\n- Words removed: {stats.get('removed_words', 0)}\n- Words added: {stats.get('added_words', 0)}\n- Words unchanged: {stats.get('unchanged_words', 0)}\n- Change percentage: {stats.get('change_percentage', 0)}%\n- Total words: {stats.get('total_words', 0)}")
                    except:
                        pass

                elif output.startswith('STRUCTURAL_ANALYSIS:'):
                    json_data = output.replace('STRUCTURAL_ANALYSIS:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summary = data.get('summary', {})
                        summaries.append(f"**Structural Changes:**\n- Sections added: {summary.get('sections_added', 0)}\n- Sections removed: {summary.get('sections_removed', 0)}\n- Sections modified: {summary.get('sections_modified', 0)}\n- Sections reordered: {summary.get('sections_reordered', 0)}\n- Total sections in Doc 1: {summary.get('total_sections_doc1', 0)}\n- Total sections in Doc 2: {summary.get('total_sections_doc2', 0)}")
                    except:
                        pass

                elif output.startswith('SEMANTIC_DIFF:'):
                    json_data = output.replace('SEMANTIC_DIFF:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summary = data.get('summary', {})
                        summaries.append(f"**Semantic Analysis:**\n- Total semantic matches: {summary.get('total_matches', 0)}\n- Moved chunks: {summary.get('moved_chunks', 0)}\n- Paraphrased chunks: {summary.get('paraphrased_chunks', 0)}\n- New chunks: {summary.get('new_chunks', 0)}\n- Removed chunks: {summary.get('removed_chunks', 0)}\n- Average similarity: {summary.get('avg_similarity', 0):.1%}")
                    except:
                        pass

            if not summaries:
                return "No analysis summaries could be extracted."

            output = "\n\n".join(summaries)

            if streaming_callback:
                streaming_callback(f"✅ Summary extraction complete!\n\n{output}")

            return output

        except Exception as e:
            error_msg = f"**Summary extraction error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
