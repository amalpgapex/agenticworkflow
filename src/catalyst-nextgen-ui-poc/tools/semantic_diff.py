
from typing import Dict, Any, Optional, Callable, List, Set
from tools.base import AgenticTool
from langchain_openai import OpenAIEmbeddings
import numpy as np
import json

class SemanticDiffTool(AgenticTool):
    """Semantic comparison using embeddings to detect paraphrased/moved content"""

    def __init__(self, api_key: str):
        super().__init__("semantic_diff", "Find semantically similar content across documents")
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Perform semantic comparison between documents"""
        try:
            previous_output = context.get('previous_output', '')
            if not previous_output.startswith('CHUNKING_RESULT:'):
                return "Error: Semantic diff requires chunking result from previous step"

            json_data = previous_output.replace('CHUNKING_RESULT:', '').strip()
            chunking_result = json.loads(json_data)

            chunks1 = chunking_result['doc1_chunks']
            chunks2 = chunking_result['doc2_chunks']

            if streaming_callback:
                streaming_callback("🔍 Performing semantic analysis...")

            embeddings1 = np.array([c['embedding'] for c in chunks1])
            embeddings2 = np.array([c['embedding'] for c in chunks2])

            emb1_norm = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
            emb2_norm = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)

            similarity_matrix = np.dot(emb1_norm, emb2_norm.T)

            if streaming_callback:
                streaming_callback("🔍 Identifying semantic matches...")

            semantic_matches = []
            moved_content = []
            paraphrased_content = []

            for i in range(len(chunks1)):
                best_match_idx = np.argmax(similarity_matrix[i])
                best_similarity = similarity_matrix[i][best_match_idx]

                if best_similarity > 0.85:
                    chunk1 = chunks1[i]
                    chunk2 = chunks2[best_match_idx]
                    match_data = {
                        'chunk1_id': chunk1['id'],
                        'chunk2_id': chunk2['id'],
                        'similarity': float(best_similarity),
                        'chunk1_text': chunk1['text'][:200],  # First 200 chars
                        'chunk2_text': chunk2['text'][:200],
                        'position_shift': best_match_idx - i
                    }
                    semantic_matches.append(match_data)

                    if abs(best_match_idx - i) > 2:
                        moved_content.append(match_data)
                    elif best_similarity < 0.95:
                        paraphrased_content.append(match_data)

            # Find new content (chunks in doc2 with no good match in doc1)
            matched_chunks2 = set()
            for match in semantic_matches:
                matched_chunks2.add(match['chunk2_id'])

            new_content = []
            for chunk in chunks2:
                if chunk['id'] not in matched_chunks2:
                    chunk_idx = chunk['id']
                    if chunk_idx < len(similarity_matrix[0]):
                        max_sim = np.max(similarity_matrix[:, chunk_idx])
                        if max_sim < 0.7:  # Truly new content
                            new_content.append({
                                'chunk_id': chunk['id'],
                                'text': chunk['text'][:200],
                                'word_count': chunk['word_count']
                            })

            # Find removed content
            matched_chunks1 = set()
            for match in semantic_matches:
                matched_chunks1.add(match['chunk1_id'])

            removed_content = []
            for chunk in chunks1:
                if chunk['id'] not in matched_chunks1:
                    chunk_idx = chunk['id']
                    if chunk_idx < len(similarity_matrix):
                        max_sim = np.max(similarity_matrix[chunk_idx])
                        if max_sim < 0.7:
                            removed_content.append({
                                'chunk_id': chunk['id'],
                                'text': chunk['text'][:200],
                                'word_count': chunk['word_count']
                            })

            result = {
                'semantic_matches': semantic_matches,
                'moved_content': moved_content,
                'paraphrased_content': paraphrased_content,
                'new_content': new_content,
                'removed_content': removed_content,
                'summary': {
                    'total_matches': len(semantic_matches),
                    'moved_chunks': len(moved_content),
                    'paraphrased_chunks': len(paraphrased_content),
                    'new_chunks': len(new_content),
                    'removed_chunks': len(removed_content),
                    'avg_similarity': float(np.mean([m['similarity'] for m in semantic_matches])) if semantic_matches else 0.0
                }
            }

            output = f"SEMANTIC_DIFF:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Semantic analysis complete!\n\n**Summary:**\n- {len(semantic_matches)} semantic matches\n- {len(moved_content)} moved chunks\n- {len(paraphrased_content)} paraphrased chunks\n- {len(new_content)} new chunks\n- {len(removed_content)} removed chunks")

            return output

        except Exception as e:
            error_msg = f"**Semantic diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
