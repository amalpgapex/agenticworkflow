
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.schema import Document
import json
import uuid

# Global storage for RAG sessions (module-level)
_rag_sessions = {}

def clear_rag_sessions() -> None:
    """Clear all stored RAG sessions to free memory/resources."""
    global _rag_sessions
    _rag_sessions = {}

def get_rag_session(session_id: str):
    """Get RAG session by ID"""
    return _rag_sessions.get(session_id)

def rag_chat(session_id: str, question: str) -> Dict[str, Any]:
    """Handle chat query with RAG"""
    session = get_rag_session(session_id)

    if not session:
        return {
            'answer': 'Error: Chat session not found. Please restart the workflow.',
            'sources': []
        }

    try:
        vectorstore = session['vectorstore']
        llm = session['llm']

        retriever = vectorstore.as_retriever(
            search_kwargs={'k': 4}
        )
        docs = retriever.get_relevant_documents(question)

        context_parts = []
        sources = []

        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
            if source not in sources:
                sources.append(source)

        context = "\n\n".join(context_parts)

        prompt = f"""Answer the question based ONLY on the provided context from the user's documents. 
Include inline citations using [Source N] format where information comes from.

Context:
{context}

Question: {question}

Answer (with citations):"""

        response = llm.invoke(prompt)
        answer = response.content

        return {
            'answer': answer,
            'sources': sources
        }

    except Exception as e:
        return {
            'answer': f'Error processing question: {str(e)}',
            'sources': []
        }

class RAGSetupTool(AgenticTool):
    """Set up RAG system for document chat"""

    def __init__(self, api_key: str):
        super().__init__("rag_setup", "Set up Retrieval Augmented Generation for document chat")
        self.api_key = api_key
        self.embeddings = OpenAIEmbeddings(api_key=api_key)
        self.llm = ChatOpenAI(
            model="gpt-5-mini", 
            temperature=0.3, 
            api_key=api_key
        )
        self.vectorstore = None
        self.session_id = None

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Set up RAG system with uploaded documents"""
        try:
            # Get all document contents
            all_documents = context.get('all_documents', [])

            if not all_documents:
                return "RAG_INITIALIZED:No documents provided"

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=200, 
                length_function=len,
            )

            # Create Document objects with metadata
            docs = []
            for doc_info in all_documents:
                content = doc_info.get('content', '')
                filename = doc_info.get('filename', 'unknown')

                # Split the content
                chunks = text_splitter.split_text(content)

                # Create Document objects with source metadata
                for i, chunk in enumerate(chunks):
                    docs.append(Document(
                        page_content=chunk, 
                        metadata={
                            'source': filename, 
                            'chunk': i
                            }
                    ))

            if not docs:
                return "RAG_INITIALIZED:No content to index"

            # Create vector store
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)

            # Generate session ID for this RAG instance
            import uuid
            self.session_id = str(uuid.uuid4())

            # Store vectorstore globally (will be accessed by chat endpoint)
            global _rag_sessions
            if '_rag_sessions' not in globals():
                _rag_sessions = {}
            _rag_sessions[self.session_id] = {
                'vectorstore': self.vectorstore,
                'llm': self.llm,
                'document_count': len(all_documents),
                'chunk_count': len(docs)
            }

            result = {
                'session_id': self.session_id,
                'document_count': len(all_documents),
                'chunk_count': len(docs),
                'status': 'ready'
            }

            return f"RAG_INITIALIZED:{json.dumps(result)}"

        except Exception as e:
            error_msg = f"RAG setup error: {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return f'RAG_INITIALIZED:{{"error": "{str(e)}"}}'