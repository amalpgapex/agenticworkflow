
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
import difflib
import re
import json

class EnhancedDiffTool(AgenticTool):
    """Advanced diff generation with multi-level granularity and PDF support"""

    def __init__(self):
        super().__init__("enhanced_diff", "Generate multi-level diffs with visual rendering")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate enhanced diff between two documents"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])

            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
                doc1_name = list(labeled_docs.keys())[0]
                doc2_name = list(labeled_docs.keys())[1]
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
                doc1_name = all_docs[0].get('filename', 'Document 1')
                doc2_name = all_docs[1].get('filename', 'Document 2')
            else:
                return "Error: Two documents required for diff"

            if streaming_callback:
                streaming_callback("📊 Generating multi-level diff analysis...")

            words1 = doc1_content.split()
            words2 = doc2_content.split()

            differ = difflib.Differ()
            diff = list(differ.compare(words1, words2))

            if streaming_callback:
                streaming_callback("📊 Creating visual markup...")

            html_parts = ['<div class="enhanced-diff">']

            removed_count = sum(1 for item in diff if item.startswith('- '))
            added_count = sum(1 for item in diff if item.startswith('+ '))
            unchanged_count = sum(1 for item in diff if item.startswith('  '))

            total_words = removed_count + added_count + unchanged_count
            change_percentage = ((removed_count + added_count) / total_words * 100) if total_words > 0 else 0

            current_line = []
            line_number = 0
            changes_by_type = {'additions': [], 'deletions': [], 'modifications': []}

            for item in diff:
                if item.startswith('- '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-removed" data-word="{word}">{word}</span>')
                    changes_by_type['deletions'].append({'word': word, 'position': line_number})
                elif item.startswith('+ '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-added" data-word="{word}">{word}</span>')
                    changes_by_type['additions'].append({'word': word, 'position': line_number})
                elif item.startswith('  '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-unchanged">{word}</span>')

                if len(current_line) > 20 or (item.endswith('.') or item.endswith('?') or item.endswith('!')):
                    if current_line:
                        html_parts.append(f'<div class="diff-line" data-line="{line_number}">{" ".join(current_line)}</div>')
                        line_number += 1
                        current_line = []

            if current_line:
                html_parts.append(f'<div class="diff-line" data-line="{line_number}">{" ".join(current_line)}</div>')

            html_parts.append('</div>')

            sentences1 = re.split(r'[.!?]+\s+', doc1_content)
            sentences2 = re.split(r'[.!?]+\s+', doc2_content)

            sentence_matcher = difflib.SequenceMatcher(None, sentences1, sentences2)
            sentence_changes = []
            for tag, i1, i2, j1, j2 in sentence_matcher.get_opcodes():
                if tag != 'equal':
                    sentence_changes.append({
                        'type': tag,
                        'doc1_sentences': sentences1[i1:i2],
                        'doc2_sentences': sentences2[j1:j2],
                        'doc1_range': [i1, i2],
                        'doc2_range': [j1, j2]
                    })

            result = {
                'diff_html': ''.join(html_parts),
                'statistics': {
                    'removed_words': removed_count,
                    'added_words': added_count,
                    'unchanged_words': unchanged_count,
                    'total_words': total_words,
                    'change_percentage': round(change_percentage, 2),
                    'doc1_word_count': len(words1),
                    'doc2_word_count': len(words2)
                },
                'changes_by_type': changes_by_type,
                'sentence_changes': sentence_changes[:50],
                'doc1_name': doc1_name,
                'doc2_name': doc2_name,
                'change_summary': f"{removed_count} deletions, {added_count} additions, {round(change_percentage, 1)}% changed"
            }

            output = f"ENHANCED_DIFF:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Diff generation complete!\n\n**Summary:**\n- {removed_count} words removed\n- {added_count} words added\n- {unchanged_count} words unchanged\n- {change_percentage:.1f}% changed")

            return output

        except Exception as e:
            error_msg = f"**Enhanced diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
