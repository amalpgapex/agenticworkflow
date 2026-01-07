
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
import difflib
import json

class RedlineDiffTool(AgenticTool):
    """Generate redline diff between two documents with word-level granularity"""

    def __init__(self):
        super().__init__("redline_diff", "Generate word-level redline diff between two documents")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate redline diff between two text documents"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            doc1_label = context.get('doc1_label', 'document1')
            doc2_label = context.get('doc2_label', 'document2')

            doc1_content = labeled_docs.get(doc1_label, {}).get('content', '')
            doc2_content = labeled_docs.get(doc2_label, {}).get('content', '')

            if not doc1_content or not doc2_content:
                all_docs = context.get('all_documents', [])
                if len(all_docs) >= 2:
                    doc1_content = all_docs[0].get('content', '')
                    doc2_content = all_docs[1].get('content', '')

            if not doc1_content or not doc2_content:
                return "Error: Two documents required for redline comparison"

            if streaming_callback:
                streaming_callback("📄 Analyzing documents for differences...")

            differ = difflib.Differ()
            words1 = doc1_content.split()
            words2 = doc2_content.split()
            diff = list(differ.compare(words1, words2))

            if streaming_callback:
                streaming_callback("📄 Building redline document...")

            html_parts = ['<div class="redline-diff">']
            current_line = []

            for item in diff:
                if item.startswith('- '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-removed">{word}</span>')
                elif item.startswith('+ '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-added">{word}</span>')
                elif item.startswith('  '):
                    word = item[2:]
                    current_line.append(word)
                elif item.startswith('? '):
                    continue

            html_parts.append(' '.join(current_line))
            html_parts.append('</div>')

            removed_count = sum(1 for item in diff if item.startswith('- '))
            added_count = sum(1 for item in diff if item.startswith('+ '))
            unchanged_count = sum(1 for item in diff if item.startswith('  '))

            total_words = removed_count + added_count + unchanged_count
            change_percentage = ((removed_count + added_count) / total_words * 100) if total_words > 0 else 0

            result = {
                'diff_html': ''.join(html_parts),
                'removed_words': removed_count,
                'added_words': added_count,
                'unchanged_words': unchanged_count,
                'change_percentage': round(change_percentage, 2),
                'doc1_label': doc1_label,
                'doc2_label': doc2_label
            }

            output = f"REDLINE_DIFF:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Redline comparison complete!\n\n**Summary:**\n- {removed_count} words removed\n- {added_count} words added\n- {change_percentage:.1f}% changed")

            return output

        except Exception as e:
            error_msg = f"**Redline diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
