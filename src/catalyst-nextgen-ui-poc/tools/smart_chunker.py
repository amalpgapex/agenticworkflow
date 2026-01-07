
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
from langchain_openai import OpenAIEmbeddings
import numpy as np
import re
import json

class SmartChunkerTool(AgenticTool):
    """Intelligent document chunking with structure detection and embeddings"""

    def __init__(self, api_key: str):
        super().__init__("smart_chunker", "Intelligently segment documents by structure")
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Chunk documents intelligently based on structure and size"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])

            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
            else:
                return "Error: Two documents required for comparison"

            if streaming_callback:
                streaming_callback("📄 Analyzing document structure...")

            doc1_words = len(doc1_content.split())
            doc2_words = len(doc2_content.split())
            max_words = max(doc1_words, doc2_words)
            est_pages = max_words / 250

            if streaming_callback:
                streaming_callback(f"📄 Estimated document size: ~{int(est_pages)} pages\n\nChoosing chunking strategy...")

            if est_pages <= 50:
                strategy = "paragraph"
                chunk_size = 500  # words
            elif est_pages <= 200:
                strategy = "section"
                chunk_size = 1000
            else:
                strategy = "adaptive"
                chunk_size = 1500

            if streaming_callback:
                streaming_callback(f"📄 Using {strategy} chunking strategy\n\nSegmenting documents...")

            chunks1 = self._chunk_document(doc1_content, strategy, chunk_size)
            chunks2 = self._chunk_document(doc2_content, strategy, chunk_size)

            if streaming_callback:
                streaming_callback(f"📄 Document 1: {len(chunks1)} chunks\n📄 Document 2: {len(chunks2)} chunks\n\nGenerating embeddings...")

            embeddings1 = self.embeddings.embed_documents([c['text'] for c in chunks1])
            embeddings2 = self.embeddings.embed_documents([c['text'] for c in chunks2])

            for i, emb in enumerate(embeddings1):
                chunks1[i]['embedding'] = emb
            for i, emb in enumerate(embeddings2):
                chunks2[i]['embedding'] = emb

            result = {
                'strategy': strategy,
                'chunk_size': chunk_size,
                'estimated_pages': int(est_pages),
                'doc1_chunks': chunks1,
                'doc2_chunks': chunks2,
                'doc1_word_count': doc1_words,
                'doc2_word_count': doc2_words
            }

            output = f"CHUNKING_RESULT:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Chunking complete!\n\n**Summary:**\n- Strategy: {strategy}\n- Doc 1: {len(chunks1)} chunks ({doc1_words} words)\n- Doc 2: {len(chunks2)} chunks ({doc2_words} words)")

            return output

        except Exception as e:
            error_msg = f"**Chunking error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

    def _chunk_document(self, content: str, strategy: str, chunk_size: int) -> List[Dict]:
        """Chunk document based on strategy"""
        chunks = []

        if strategy == "paragraph":
            # Split by double newlines (paragraphs)
            paragraphs = re.split(r'\n\s*\n', content)
            
            current_chunk = []
            current_words = 0
            chunk_id = 0
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                para_words = len(para.split())

                if current_words + para_words > chunk_size and current_chunk:
                    chunks.append({
                        'id': chunk_id,
                        'text': '\n\n'.join(current_chunk),
                        'type': 'paragraph',
                        'word_count': current_words,
                        'structure_level': self._detect_structure_level(current_chunk[0])
                    })
                    chunk_id += 1
                    current_chunk = []
                    current_words = 0

                current_chunk.append(para)
                current_words += para_words

            if current_chunk:
                chunks.append({
                    'id': chunk_id,
                    'text': '\n\n'.join(current_chunk),
                    'type': 'paragraph',
                    'word_count': current_words,
                    'structure_level': self._detect_structure_level(current_chunk[0])
                })

        elif strategy == "section":
            lines = content.split('\n')
            current_section = []
            current_words = 0
            chunk_id = 0
            current_heading = None

            for line in lines:
                line_stripped = line.strip()
                is_heading = self._is_heading(line_stripped)

                if is_heading and current_section and current_words > chunk_size // 2:
                    chunks.append({
                        'id': chunk_id,
                        'text': '\n'.join(current_section),
                        'type': 'section',
                        'word_count': current_words,
                        'heading': current_heading,
                        'structure_level': self._detect_structure_level(current_heading or '')
                    })
                    chunk_id += 1
                    current_section = []
                    current_words = 0

                if is_heading:
                    current_heading = line_stripped

                current_section.append(line)
                current_words += len(line_stripped.split())

            if current_section:
                chunks.append({
                    'id': chunk_id,
                    'text': '\n'.join(current_section),
                    'type': 'section',
                    'word_count': current_words,
                    'heading': current_heading,
                    'structure_level': self._detect_structure_level(current_heading or '')
                })

        else:  # adaptive
            chunks = self._chunk_document(content, "section", chunk_size)

        return chunks

    def _is_heading(self, text: str) -> bool:
        """Detect if text is likely a heading"""
        if not text:
            return False
        if re.match(r'^#{1,6}\s+', text):
            return True
        if text.isupper() and len(text) < 100:
            return True
        if text.istitle() and len(text) < 80 and not text.endswith(('.', '!', '?', ',')):
            return True
        # Numbered section
        if re.match(r'^\d+\.(\d+\.)*\s+[A-Z]', text):
            return True
        return False

    def _detect_structure_level(self, text: str) -> int:
        """Detect the structural level (heading depth)"""
        match = re.match(r'^(#{1,6})\s+', text)
        if match:
            return len(match.group(1))
        if re.match(r'^(\d+\.)+', text):
            return text[:20].count('.')
        if text.isupper():
            return 1
        if text.istitle():
            return 2
        return 0
