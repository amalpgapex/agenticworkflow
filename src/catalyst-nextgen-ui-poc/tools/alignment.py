
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
from langchain_openai import OpenAIEmbeddings
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import difflib
import json
import re

class AlignmentTool(AgenticTool):
    """Align items from two Excel files using OpenAI embeddings and Hungarian algorithm"""

    def __init__(self, api_key: str):
        super().__init__("alignment", "Align items from two Excel files using semantic matching")
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute alignment between two Excel files"""
        try:
            file1_path = context.get('file1_path')
            file2_path = context.get('file2_path')
            user_options = context.get('user_options', {})

            column1_str = user_options.get('column1', '0')
            column2_str = user_options.get('column2', '0')

            try:
                column1 = int(column1_str) if column1_str else 0
            except (ValueError, TypeError):
                column1 = 0

            try:
                column2 = int(column2_str) if column2_str else 0
            except (ValueError, TypeError):
                column2 = 0

            include_diff = user_options.get('include_diff', 'no') == 'yes'

            if not file1_path or not file2_path:
                return "Error: Both Excel file paths are required"

            if streaming_callback:
                streaming_callback("📊 Loading Excel files...")

            df1 = pd.read_excel(file1_path)
            df2 = pd.read_excel(file2_path)

            if isinstance(column1, int):
                col1_data = df1.iloc[:, column1].astype(str).tolist()
                col1_name = str(df1.columns[column1])
            else:
                col1_data = df1[column1].astype(str).tolist()
                col1_name = str(column1)

            if isinstance(column2, int):
                col2_data = df2.iloc[:, column2].astype(str).tolist()
                col2_name = str(df2.columns[column2])
            else:
                col2_data = df2[column2].astype(str).tolist()
                col2_name = str(column2)

            if streaming_callback:
                streaming_callback(f"📊 Loaded {len(col1_data)} items from file 1 and {len(col2_data)} items from file 2\n\n🔮 Generating embeddings...")

            embeddings1 = self.embeddings.embed_documents(col1_data)
            embeddings2 = self.embeddings.embed_documents(col2_data)

            if streaming_callback:
                streaming_callback(f"🔮 Embeddings generated\n\n🔗 Computing similarity matrix and finding optimal matches...")

            emb1 = np.array(embeddings1)
            emb2 = np.array(embeddings2)

            emb1_norm = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
            emb2_norm = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)

            similarity_matrix = np.dot(emb1_norm, emb2_norm.T)

            cost_matrix = 1 - similarity_matrix
            row_indices, col_indices = linear_sum_assignment(cost_matrix)

            if streaming_callback:
                streaming_callback("🔗 Optimal matching complete\n\n📋 Formatting results...")

            match_dict_1to2 = {}
            match_dict_2to1 = {}
            for i, j in zip(row_indices, col_indices):
                match_dict_1to2[i] = j
                match_dict_2to1[j] = i

            matched_indices1 = set(row_indices)
            matched_indices2 = set(col_indices)

            unified_pairs = []
            for i in range(len(col1_data)):
                if i in match_dict_1to2:
                    j = match_dict_1to2[i]
                    similarity_score = similarity_matrix[i, j]
                    pair_data = {
                        'file1_index': int(i),
                        'file2_index': int(j),
                        'file1_value': col1_data[i],
                        'file2_value': col2_data[j],
                        'similarity': float(similarity_score),
                        'is_matched': True,
                        'type': 'match'
                    }
                    if include_diff:
                        diff_html = self._calculate_diff(col1_data[i], col2_data[j])
                        pair_data['diff'] = diff_html
                    unified_pairs.append(pair_data)
                else:
                    unified_pairs.append({
                        'file1_index': int(i),
                        'file2_index': None,
                        'file1_value': col1_data[i],
                        'file2_value': None,
                        'similarity': 0.0,
                        'is_matched': False,
                        'type': 'orphan_file1'
                    })

            for j in range(len(col2_data)):
                if j not in matched_indices2:
                    unified_pairs.append({
                        'file1_index': None,
                        'file2_index': int(j),
                        'file1_value': None,
                        'file2_value': col2_data[j],
                        'similarity': 0.0,
                        'is_matched': False,
                        'type': 'orphan_file2'
                    })

            orphans1 = [{'index': int(i), 'value': col1_data[i]}
                        for i in range(len(col1_data)) if i not in matched_indices1]
            orphans2 = [{'index': int(i), 'value': col2_data[i]}
                        for i in range(len(col2_data)) if i not in matched_indices2]

            matched_only = [p for p in unified_pairs if p['is_matched']]

            result = {
                'unified_pairs': unified_pairs,
                'matched_pairs': matched_only,
                'orphans_file1': orphans1,
                'orphans_file2': orphans2,
                'file1_column': col1_name,
                'file2_column': col2_name,
                'total_matches': len(matched_only),
                'total_orphans': len(orphans1) + len(orphans2),
                'avg_similarity': float(np.mean([p['similarity'] for p in matched_only])) if matched_only else 0.0,
                'include_diff': include_diff
            }

            output = f"ALIGNMENT_RESULT:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Alignment complete!\n\n**Summary:**\n- {len(matched_only)} pairs matched\n- {len(orphans1)} unmatched from file 1\n- {len(orphans2)} unmatched from file 2\n- Average similarity: {result['avg_similarity']:.2%}")

            return output

        except Exception as e:
            error_msg = f"**Alignment error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

    def _calculate_diff(self, text1: str, text2: str) -> str:
        """Calculate diff between two text blocks and return HTML"""
        differ = difflib.Differ()
        diff = list(differ.compare(text1.split(), text2.split()))

        html_parts = []
        for item in diff:
            if item.startswith('- '):
                word = item[2:]
                html_parts.append(f'<span class="diff-removed">{word}</span>')
            elif item.startswith('+ '):
                word = item[2:]
                html_parts.append(f'<span class="diff-added">{word}</span>')
            elif item.startswith('  '):
                word = item[2:]
                html_parts.append(word)

        return ' '.join(html_parts)
