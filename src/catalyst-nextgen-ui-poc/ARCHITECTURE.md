# InK Studio - Architecture Guide

Complete guide to the codebase structure, components, and how everything works together.

---

## Table of Contents
1. [Overview](#overview)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Component Details](#component-details)
5. [State Management](#state-management)
6. [Adding Features](#adding-features)
7. [Troubleshooting](#troubleshooting)

---

## Overview

InK Studio is an AI document transformation platform with a **modular UI architecture** (refactored October 2025).

### Key Stats
- **Main HTML**: 180 lines (was 3,282)
- **UI Components**: 4 focused files
- **Canvas Types**: 9 fully functional
- **Feature Parity**: 100% with original

---

## Frontend Architecture

### Structure
```
templates/index.html (180 lines)
├── Flexbox three-panel layout
├── Context-aware panel sizing
└── Dynamic component loading

static/components/
├── setup_panel.html (250 lines) - Task selection & files
├── canvas_panel.html (635 lines) - All 9 canvas types
├── actions_panel.html (71 lines) - Workflow timeline
└── manager_view.html (26 lines) - Task library

static/css/main.css - All custom styles
static/js/app.js - All application logic (Alpine.js)
```

### How Components Load
1. Page loads with three empty `<div>` containers
2. JavaScript fetches component HTML via `fetch()`
3. Components inserted into DOM
4. Alpine.js initializes and binds reactive data

### Layout System
**Simple Flexbox** (no complex Grid syntax):
```css
display: flex;
gap: 1.5rem;

#setup-panel   { width: 50%; }      /* Setup mode */
#canvas-panel  { flex: 1; }         /* Always flexible */
#actions-panel { width: 0; }        /* Hidden initially */
```

JavaScript adjusts widths based on workflow state:
- **Setup Mode**: 50% | flex | hidden
- **Working Mode**: 350px | flex | 350px

---

## Backend Architecture

### FastAPI Server (`app_fastapi.py`)
- Serves HTML templates
- Mounts static files (`/static/`)
- Provides REST API endpoints
- Handles SSE streaming for workflows

### LangGraph Agent (`langgraph_agent.py`)
- Orchestrates multi-step AI workflows
- Manages state between steps
- Streams output in real-time

### Document Processor (`document_processor.py`)
- Handles DOCX, PDF, Excel, TXT files
- Extracts content
- Prepares for AI processing

### Agentic Tools (`agentic_tools.py`)
- RAG (Retrieval-Augmented Generation) for chat
- Vector store management
- Document indexing

---

## Component Details

### Setup Panel (`setup_panel.html`)

**Features**:
- Task search with live filtering
- Category pills (Ask, Analyze, Compare, Create, Update)
- Rich task cards with icons and metadata
- Labeled file inputs (for complex workflows)
- Traditional file uploads
- File validation messages
- Dynamic task options
- Status indicator

**Key Bindings**:
- `x-model="taskSearch"` - Search input
- `x-model="selectedTransform"` - Selected task
- `@click="selectTask(key)"` - Task card click
- `@change="addFile"` - File upload
- `@click="runDraft()"` - Start button

**Backend Connections**:
- Calls `selectTask()` → clears old RAG sessions
- Calls `filterTasks()` → updates filtered list
- Calls `processDualExcel()` → when 2 Excel files uploaded
- Calls `updateDynamicTaskOptions()` → populates Excel column dropdowns

### Canvas Panel (`canvas_panel.html`)

**9 Canvas Types**:
1. `text_editor` - WYSIWYG with toolbar
2. `alignment_viewer` - Three-column alignment
3. `chat_interface` - Document Q&A
4. `relationship_viewer` - Entity connections
5. `audio_player` - Podcast playback
6. `image_viewer` - Image display
7. `pdf_viewer` - PDF viewing
8. `code_editor` - Code display
9. `standard` - Markdown (fallback)

**Conditional Rendering**:
```html
<div x-show="currentCanvasType === 'text_editor'">
    <!-- Text editor UI -->
</div>
<div x-show="currentCanvasType === 'chat_interface'">
    <!-- Chat UI -->
</div>
```

**Special Features**:
- Focus mode badge (appears when both panels collapsed)
- Edit mode toggle (for alignment viewer)
- Live streaming indicator
- Export button with download link

### Actions Panel (`actions_panel.html`)

**Features**:
- Visual timeline with colored indicators
- Click to navigate between steps
- Replay button to rerun from any step
- Status badges (completed, processing, pending)
- Keyboard accessible (Enter/Space)

**Key Bindings**:
- `@click="viewStep(idx)"` - Navigate to step
- `@click="rerunFromStep(idx)"` - Replay functionality

---

## State Management

### Alpine.js State (`app.js`)

All state stored in one `appData()` function:

```javascript
appData() {
    return {
        // View state
        currentView: 'workflow',
        
        // Task state
        selectedTransform: '',
        transformations: [],
        taskSearch: '',
        selectedCategory: 'all',
        filteredTasks: [],
        
        // File state
        uploadedFiles: [],
        labeledFiles: {},
        
        // Workflow state
        processing: false,
        steps: [],
        stepOutputs: [],
        currentViewingStep: 0,
        
        // Canvas state
        currentCanvasType: 'text_editor',
        alignmentData: null,
        chatMessages: [],
        chatSessionId: null,
        
        // UI state
        leftPanelCollapsed: false,
        rightPanelCollapsed: false,
        
        // ... and all functions
    }
}
```

### Computed Properties
Alpine.js reactive getters:
- `currentTaskFileTypes` - Accepted file extensions
- `currentTaskUsesLabeledFiles` - Boolean for labeled inputs
- `filesMatchTask` - File validation
- `filteredTasks` - Search/filtered results

### Key Functions
- `selectTask(key)` - Select task, update canvas type, clear RAG
- `addFile()` - Upload file
- `runDraft()` - Start workflow
- `viewStep(idx)` - Navigate to step
- `exportToWord()` - Export output
- `formatText()` - Text formatting
- `sendChatMessage()` - Chat functionality

---

## Adding Features

### Add a New Canvas Type

1. Edit `static/components/canvas_panel.html`
2. Add your canvas section:
```html
<div x-show="currentCanvasType === 'my_new_canvas'">
    <div class="p-6 bg-white border border-slate-200 rounded-2xl">
        <!-- Your canvas UI here -->
        <div x-html="renderMarkdown(stepOutputs[currentViewingStep] || '')"></div>
    </div>
</div>
```
3. Create task with `canvas_type: 'my_new_canvas'`
4. Done!

### Add UI to Setup Panel

1. Edit `static/components/setup_panel.html`
2. Add HTML where appropriate
3. Use Alpine.js directives:
```html
<input x-model="myVariable">              <!-- Two-way binding -->
<div x-show="myCondition">...</div>       <!-- Conditional -->
<button @click="myFunction()">...</button> <!-- Event -->
```
4. Add logic to `app.js` if needed

### Add a Style

1. Edit `static/css/main.css`
2. Add your CSS class
3. Use in component files
4. Refresh browser - instant update!

### Add Backend Logic

1. Edit appropriate Python file
2. Add function or modify existing
3. Test with workflow
4. No frontend changes needed if API stays same

---

## Important Technical Details

### IDs That Must Not Change
- `wysiwyg-editor` - Text editor (JS expects this ID)
- `left-scroll-container` - Alignment left column
- `right-scroll-container` - Alignment right column  
- `chat-messages-container` - Chat messages
- `setup-panel`, `canvas-panel`, `actions-panel` - Container IDs

### CSS Classes Used Throughout
- `.panel` - Panel styling with transitions
- `.timeline`, `.timeline-step` - Step visualization
- `.markdown-content` - Rendered markdown
- `.wysiwyg-editor` - Editable text
- `.diff-content` - Diff highlighting
- `.relationship-node` - Alignment cards

### Alpine.js Patterns
- `x-model` - Two-way data binding
- `x-show` - Conditional display
- `x-if` - Conditional rendering (removed from DOM)
- `@click` - Click handler
- `@change` - Change handler
- `x-text` - Text binding
- `x-html` - HTML binding
- `x-init` - Initialization
- `:class` - Dynamic classes

---

## Backend API Endpoints

### Main Endpoints
- `GET /` - Main application
- `GET /api/transformations` - Get available tasks
- `POST /api/upload` - Upload file
- `POST /api/stream/{task_key}` - Run workflow (SSE)
- `POST /api/export-to-word` - Export to DOCX
- `POST /api/chat` - Chat with documents
- `POST /api/session/reset` - Clear RAG sessions
- `DELETE /api/transformation/{key}` - Delete task

### SSE Stream Format
```javascript
{
    "type": "step_status",
    "step": 0,
    "status": "processing",
    "name": "Step Name"
}
{
    "type": "step_output",
    "step": 0,
    "output": "Generated content..."
}
```

---

## Troubleshooting

### Layout Issues
**Panels stacking vertically?**
- Check browser console for errors
- Verify components loaded (check Network tab)
- Hard refresh (Ctrl+Shift+R)

### Features Not Working
**Canvas not switching?**
- Check `currentCanvasType` in Alpine DevTools
- Verify task has correct `canvas_type` in definition

**Files not uploading?**
- Check backend logs
- Verify `/api/upload` endpoint working
- Check file type is accepted

**Chat referencing old docs?**
- Should be fixed (clears on task selection)
- Check console for session reset call

### Backend Issues
**Server won't start?**
- Check Python installed: `python --version`
- Verify dependencies: `pip list`
- Check API key in config.py
- Look for port conflicts (default: 8000)

---

## Development Workflow

### Making a Change
1. Edit appropriate file (component, CSS, or JS)
2. Save file
3. Refresh browser (Ctrl+R)
4. See changes immediately
5. No build step needed!

### Testing
- Manual testing in browser
- Check all canvas types
- Test panel collapse/expand
- Verify file uploads
- Test workflows end-to-end

### Debugging
- F12 - Open DevTools
- Console - See JavaScript errors
- Network - Check API calls
- Elements - Inspect DOM structure
- Alpine DevTools - View reactive state

---

## Project Philosophy

### Keep It Simple
- Small, focused components
- One file, one responsibility
- Use existing patterns
- Avoid complexity

### Maintain Modularity
- Don't put everything in one file
- Separate concerns (UI vs logic vs styles)
- Use components for reusable pieces

### Document Complex Features
- Add comments for non-obvious code
- Update this guide for architecture changes
- Keep docs in sync with code

---

## Resources

### Documentation
- **GET_STARTED.md** (this file) - Quick start
- **ARCHITECTURE.md** - You are here
- **docs/** folder - Feature-specific guides

### Code
- **static/components/** - Start here for UI
- **app.js** - State and logic
- **app_fastapi.py** - Backend entry point

### External
- Alpine.js: https://alpinejs.dev/
- Tailwind CSS: https://tailwindcss.com/
- FastAPI: https://fastapi.tiangolo.com/
- LangGraph: https://langchain-ai.github.io/langgraph/

---

**Ready to code!** Check GET_STARTED.md if you need help running the app. 🚀





















