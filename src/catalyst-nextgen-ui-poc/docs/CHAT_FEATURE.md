# 💬 Chat with Documents - RAG Feature

## Overview
Interactive chat interface that allows users to ask questions about their uploaded documents using Retrieval Augmented Generation (RAG).

---

## ✨ Features

- **Multiple File Upload** - Upload multiple docx, pdf, txt, md files
- **Semantic Search** - OpenAI embeddings + FAISS vector store
- **Source Citations** - Every answer includes references to source documents
- **Simple RAG** - Out-of-the-box LangChain components
- **In-Memory Storage** - Fast, no disk persistence needed for now
- **Clean Chat UI** - Modern iMessage-style interface

---

## 🔧 How It Works

### 1. Document Upload
```
User uploads multiple files → 
Each file's content extracted →
Stored in current_state['all_documents']
```

### 2. RAG Initialization
```
User clicks "Run Draft" →
RAGSetupTool executes →
Documents split into chunks (1000 chars, 200 overlap) →
Chunks embedded using OpenAI text-embedding-3-small →
FAISS vector store created →
Session ID generated →
Returns "RAG_INITIALIZED:{session_id, doc_count, chunk_count}"
```

### 3. Chat Interaction
```
User types question →
Frontend sends {session_id, question} to /api/chat →
Backend retrieves top 4 relevant chunks →
LLM generates answer with [Source N] citations →
Answer displayed with source tags →
User can continue conversation
```

---

## 📐 Architecture

### Backend Components

#### `agentic_tools.py`

**RAGSetupTool Class:**
- Inherits from `AgenticTool`
- Uses `OpenAIEmbeddings` for vectorization
- Uses `FAISS.from_documents()` for vector store
- Uses `RecursiveCharacterTextSplitter` for chunking
- Stores session in global `_rag_sessions` dictionary

**rag_chat() Function:**
- Retrieves session from `_rag_sessions`
- Uses `vectorstore.as_retriever(k=4)` for semantic search
- Formats context with source attributions
- Prompts LLM to include `[Source N]` citations
- Returns `{answer, sources}`

#### `app_fastapi.py`

**Upload Endpoint:**
- Stores each uploaded file in `current_state['all_documents']`
- Format: `{'filename': str, 'content': str, 'file_type': str}`

**Stream Endpoint:**
- Passes `all_documents` in context to RAGSetupTool
- Receives `RAG_INITIALIZED:...` response

**Chat Endpoint** (`/api/chat`):
- POST endpoint
- Accepts `{session_id, question}`
- Calls `rag_chat(session_id, question)`
- Returns `{answer, sources, question}`

### Frontend Components

#### `templates/index.html`

**Chat Interface Canvas:**
- Triggered when `currentCanvasType === 'chat_interface'`
- Displays messages in chat bubbles
- Shows source citations as tags
- Input field with send button
- Auto-scrolls to latest message

**State Management:**
```javascript
chatMessages: []        // Array of {type, content, sources}
chatSessionId: null     // UUID from RAG initialization
userQuestion: ''        // Current input
isWaitingForChat: false // Loading state
```

**Methods:**
- `initializeChatSession()` - Extracts session ID from stepOutput
- `sendChatMessage()` - Sends question to /api/chat and displays response

---

## 🎨 UI Design

### Message Types

**System Message:**
```
┌─────────────────────────────────────┐
│ ✅ Ready to chat! Indexed 3...      │
└─────────────────────────────────────┘
```

**User Message (right-aligned, blue):**
```
                    ┌──────────────────────┐
                    │ What is the policy   │
                    │ on remote work?      │
                    └──────────────────────┘
```

**Assistant Message (left-aligned, gray with sources):**
```
┌───────────────────────────────────────────┐
│ The remote work policy allows up to 3...  │
│ [Source 1] mentions flexible schedules.   │
│                                            │
│ 📎 Sources:                                │
│ [Employee_Handbook.docx] [Policy_Guide.pdf]│
└───────────────────────────────────────────┘
```

---

## 📋 Configuration

### `prompts.json`
```json
"chat_with_documents": {
  "name": "Chat with my documents",
  "description": "Interactive chat with RAG",
  "canvas_type": "chat_interface",
  "input_file_types": ["docx", "txt", "md", "pdf"],
  "category": "ask",
  "icon": "💬",
  "allow_multiple_files": true,
  "steps": [{
    "step_name": "Initialize RAG",
    "step_type": "rag_setup"
  }]
}
```

### `canvas_types.json`
```json
"chat_interface": {
  "id": "chat_interface",
  "name": "Chat Interface",
  "description": "Interactive chat interface for RAG",
  "capabilities": {
    "interactive": true,
    "chat": true
  }
}
```

---

## 🚀 Usage

### 1. Upload Documents
- Select "Chat with my documents" task
- Upload one or more files (docx, pdf, txt, md)
- Multiple files supported

### 2. Run Workflow
- Click "Run Draft"
- Wait for "Ready to chat!" message
- Chat input becomes enabled

### 3. Ask Questions
- Type your question
- Press Enter or click Send
- See answer with source citations
- Continue conversation

---

## 🔧 Technical Details

### Chunking Strategy
```python
RecursiveCharacterTextSplitter(
    chunk_size=1000,      # 1000 characters per chunk
    chunk_overlap=200,     # 200 char overlap for context
    length_function=len
)
```

### Retrieval Settings
```python
retriever = vectorstore.as_retriever(
    search_kwargs={'k': 4}  # Retrieve top 4 most relevant chunks
)
```

### Embedding Model
- `text-embedding-3-small` (via OpenAI API)
- Fast and cost-effective
- High quality semantic search

### LLM Model
- `gpt-4o-mini`
- Temperature: 0.3 (more focused answers)
- Prompted to include `[Source N]` citations

---

## 💾 Storage

### Current: In-Memory
- Vector store lives in `_rag_sessions` dictionary
- Fast access, no disk I/O
- Lost on server restart
- Lost after workflow completes

**Pros:**
- Simple implementation
- Fast performance
- No file management

**Cons:**
- Re-index on every workflow run
- No persistence across sessions
- Uses RAM

### Future: Disk Persistence (Optional)
Could add:
- `FAISS.save_local()` / `FAISS.load_local()`
- Cache indices by document hash
- Reuse indices for same documents
- Survive server restarts

---

## 🧪 Testing Checklist

- [ ] Upload single document → RAG initializes
- [ ] Upload multiple documents → All indexed
- [ ] Ask question → Get answer with citations
- [ ] Ask follow-up → Context maintained
- [ ] Check sources → Match uploaded files
- [ ] Verify citations in answer text
- [ ] Test with different file types (docx, pdf, txt, md)
- [ ] Test error handling (no session, no question)
- [ ] Verify auto-scroll works
- [ ] Check "Initializing..." → "Connected" status

---

## 📊 Example Conversation

**User uploads:**
- Employee_Handbook.docx
- Remote_Work_Policy.pdf
- Benefits_Guide.txt

**System:**
✅ Ready to chat! Indexed 3 document(s) into 47 searchable chunks.

**User:**
What is the remote work policy?

**Assistant:**
According to the Remote Work Policy [Source 1], employees can work remotely up to 3 days per week with manager approval. The policy requires a dedicated workspace and reliable internet connection [Source 2].

📎 Sources: [Remote_Work_Policy.pdf] [Employee_Handbook.docx]

---

## 🔒 Security Notes

- Documents stay in server memory only
- Not persisted to disk (unless you add it)
- Session IDs are UUIDs (hard to guess)
- No auth currently (local use only)
- For production: add user authentication and session management

---

## ⚙️ Dependencies

Added to `requirements.txt`:
```
langchain-community>=0.3.0
faiss-cpu>=1.7.4
```

Install with:
```bash
pip install langchain-community faiss-cpu
```

---

*Chat Feature Documentation*  
*Simple RAG implementation with OpenAI + LangChain + FAISS*  
*Clean, fast, effective document Q&A*
