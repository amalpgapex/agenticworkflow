# Canvas Types Architecture

## Overview

InK Studio now supports a **modular canvas type system** that allows you to easily add new types of output viewers and editors based on the input file type and selected direction/transformation.

This architecture separates the **canvas rendering logic** from the **workflow logic**, making the application highly extensible.

---

## Architecture Components

### 1. **Canvas Types Configuration** (`canvas_types.json`)

Defines all available canvas types with their properties, capabilities, and supported file types.

```json
{
  "canvas_types": {
    "text_editor": {
      "id": "text_editor",
      "name": "Text Editor",
      "description": "Rich text editor with formatting toolbar",
      "supported_file_types": ["docx", "txt", "md"],
      "capabilities": {
        "editable": true,
        "exportable": true,
        "formatting": true
      },
      "export_formats": ["docx", "txt", "md"],
      "component": "wysiwyg-editor",
      "icon": "📝"
    }
  },
  "file_type_mappings": {
    "docx": "text_editor",
    "mp3": "audio_player"
  }
}
```

**Key Properties:**
- **id**: Unique identifier for the canvas type
- **name**: Human-readable name
- **supported_file_types**: Array of compatible file extensions
- **capabilities**: What the canvas can do (edit, export, format, etc.)
- **export_formats**: Output formats supported
- **component**: Frontend component identifier
- **icon**: Emoji or icon for UI display

---

### 2. **Direction/Transformation Metadata** (`prompts.json`)

Each direction now includes canvas type and input file type metadata:

```json
{
  "executive_summary": {
    "name": "Executive Summary",
    "description": "Creates a concise executive summary",
    "canvas_type": "text_editor",
    "input_file_types": ["docx", "txt", "md", "pdf"],
    "steps": [...]
  },
  "generate_podcast": {
    "name": "Generate Podcast",
    "description": "Converts document into audio podcast",
    "canvas_type": "audio_player",
    "input_file_types": ["docx", "txt", "md", "pdf"],
    "steps": [...]
  }
}
```

**New Fields:**
- **canvas_type**: Which canvas type to use for this direction
- **input_file_types**: Array of compatible input file types

---

### 3. **Backend API Updates** (`app_fastapi.py`)

#### New Endpoints

**Get All Canvas Types:**
```
GET /api/canvas-types
```
Returns the complete canvas types configuration.

**Get Specific Canvas Type:**
```
GET /api/canvas-type/{canvas_type_id}
```
Returns details for a specific canvas type.

**Updated Transformations Endpoint:**
```
GET /api/transformations
```
Now includes `canvas_type` and `input_file_types` for each transformation.

#### Enhanced Upload Endpoint

**Upload Document:**
```
POST /api/upload
```

**Response:**
```json
{
  "success": true,
  "filename": "document.docx",
  "file_type": "docx",
  "default_canvas_type": "text_editor",
  "word_count": 1234,
  "char_count": 6789
}
```

Now detects file type and suggests a default canvas type.

---

### 4. **Frontend Canvas Rendering** (`templates/index.html`)

#### Data Structure

```javascript
{
  canvasTypes: {},              // All available canvas types
  currentCanvasType: 'text_editor',  // Active canvas type
  uploadedFileType: '',         // Type of uploaded file
  defaultCanvasType: 'text_editor',  // Default based on file
  compatibleTransformations: [] // Computed property
}
```

#### Dynamic Canvas Rendering

The canvas dynamically renders based on `currentCanvasType`:

```html
<!-- TEXT EDITOR CANVAS -->
<div x-show="currentCanvasType === 'text_editor'">
  <!-- Formatting toolbar and WYSIWYG editor -->
</div>

<!-- AUDIO PLAYER CANVAS -->
<div x-show="currentCanvasType === 'audio_player'">
  <!-- Audio player controls -->
</div>

<!-- IMAGE VIEWER CANVAS -->
<div x-show="currentCanvasType === 'image_viewer'">
  <!-- Image viewing/editing interface -->
</div>
```

#### Workflow

1. **Upload**: File type is detected → Default canvas type set
2. **Select Direction**: Canvas type updates based on direction's `canvas_type`
3. **Processing**: Streaming preview uses markdown rendering
4. **Complete**: Appropriate canvas component renders for editing/viewing
5. **Export**: Uses canvas capabilities to determine export options

---

## Currently Implemented Canvas Types

### 📝 Text Editor
- **Files**: `.docx`, `.txt`, `.md`
- **Features**: Rich text editing, formatting toolbar, markdown support
- **Export**: Word, Text, Markdown

### 🎧 Audio Player
- **Files**: Generated audio (`.mp3`)
- **Features**: HTML5 audio playback, play/pause, progress bar
- **Export**: MP3

---

## Adding a New Canvas Type

### Step 1: Define in `canvas_types.json`

```json
{
  "canvas_types": {
    "my_new_canvas": {
      "id": "my_new_canvas",
      "name": "My New Canvas",
      "description": "Description of what this canvas does",
      "supported_file_types": ["ext1", "ext2"],
      "capabilities": {
        "editable": true,
        "exportable": true,
        "custom_capability": true
      },
      "export_formats": ["format1"],
      "component": "my-canvas-component",
      "icon": "🎨"
    }
  },
  "file_type_mappings": {
    "ext1": "my_new_canvas"
  }
}
```

### Step 2: Create Direction in `prompts.json`

```json
{
  "my_new_direction": {
    "name": "My New Direction",
    "description": "What this direction does",
    "canvas_type": "my_new_canvas",
    "input_file_types": ["ext1", "ext2"],
    "steps": [...]
  }
}
```

### Step 3: Add Frontend Component in `templates/index.html`

```html
<!-- MY NEW CANVAS -->
<div x-show="currentCanvasType === 'my_new_canvas'" 
     class="p-4 bg-white border border-gray-200 rounded-lg">
  <!-- Your custom canvas UI here -->
  <!-- Access data via: stepOutputs[currentViewingStep] -->
</div>
```

### Step 4: (Optional) Add Backend Processing

If your canvas requires special backend processing (like TTS for audio):

1. Create a tool in `agentic_tools.py`
2. Register it in `ToolRegistry`
3. Use `step_type` in your direction's steps

### Step 5: (Optional) Update Export Logic

If your canvas has custom export needs:

```javascript
// In exportToWord() or create new export method
if (this.currentCanvasType === 'my_new_canvas') {
  // Custom export logic
  const response = await fetch('/api/export-my-format', {
    method: 'POST',
    body: JSON.stringify({ content: this.stepOutputs[...] })
  });
}
```

---

## Planned Canvas Types

### 📷 Image Viewer
- View and annotate images
- Support for PNG, JPG, GIF, WebP
- Export to various image formats

### 📄 PDF Viewer
- View PDF documents
- Pagination, zoom, search
- Export to PDF

### 📊 Spreadsheet Viewer
- View and edit tabular data
- Support for XLSX, CSV
- Sorting, filtering
- Export to Excel/CSV

### 💻 Code Editor
- Syntax-highlighted code editing
- Support for Python, JavaScript, etc.
- Line numbers, auto-indentation
- Export to source files

### 🎬 Video Player
- Video playback with controls
- Support for MP4, WebM
- Timeline scrubbing

---

## Benefits of This Architecture

✅ **Separation of Concerns**: Canvas types are independent of transformations  
✅ **Extensibility**: Add new canvas types without touching core logic  
✅ **Type Safety**: File types automatically map to appropriate canvases  
✅ **Flexibility**: Same transformation can work with different canvas types  
✅ **Reusability**: Canvas components can be shared across directions  
✅ **Maintainability**: Configuration-driven, easy to update  

---

## File Compatibility Matrix

| File Type | Default Canvas | Compatible Directions |
|-----------|----------------|----------------------|
| `.docx` | Text Editor | All text transformations |
| `.txt` | Text Editor | All text transformations |
| `.md` | Text Editor | All text transformations |
| `.pdf` | PDF Viewer | Read-only transformations |
| `.mp3` | Audio Player | Podcast playback |
| `.png/.jpg` | Image Viewer | Image analysis |
| `.xlsx/.csv` | Spreadsheet | Data analysis |
| `.py/.js` | Code Editor | Code review/refactoring |

---

## Configuration Flow

```
1. User uploads file
   ↓
2. Backend detects file_type (.docx, .mp3, etc.)
   ↓
3. file_type_mappings → default_canvas_type
   ↓
4. Frontend filters directions by input_file_types
   ↓
5. User selects direction
   ↓
6. Direction's canvas_type → currentCanvasType
   ↓
7. Appropriate canvas component renders
   ↓
8. Processing streams to canvas
   ↓
9. User edits/views in canvas
   ↓
10. Export uses canvas capabilities
```

---

## API Reference

### Canvas Types API

**Get All Canvas Types**
```
GET /api/canvas-types
Response: { canvas_types: {...}, file_type_mappings: {...} }
```

**Get Specific Canvas Type**
```
GET /api/canvas-type/{id}
Response: { id, name, description, capabilities, ... }
```

### Transformations API

**Get All Transformations**
```
GET /api/transformations
Response: {
  transformations: [
    { key, name, description, steps, canvas_type, input_file_types }
  ]
}
```

**Get Transformation Details**
```
GET /api/transformation/{key}
Response: { name, description, steps, canvas_type, input_file_types }
```

---

## Next Steps

1. ✅ **Core Architecture** - Complete
2. ✅ **Text Editor Canvas** - Complete
3. ✅ **Audio Player Canvas** - Complete
4. 🔲 **Image Viewer Canvas** - Planned
5. 🔲 **PDF Viewer Canvas** - Planned
6. 🔲 **Code Editor Canvas** - Planned
7. 🔲 **Spreadsheet Viewer Canvas** - Planned
8. 🔲 **Multi-file Upload** - Future enhancement
9. 🔲 **Canvas Plugins System** - Future enhancement

---

## Troubleshooting

**Problem**: Direction not appearing in dropdown after upload  
**Solution**: Check that `input_file_types` in `prompts.json` includes the uploaded file extension

**Problem**: Wrong canvas rendering  
**Solution**: Verify `canvas_type` in direction matches a key in `canvas_types.json`

**Problem**: Export not working for new canvas  
**Solution**: Check `export_formats` capability and implement backend export endpoint if needed

**Problem**: File type not recognized  
**Solution**: Add mapping in `file_type_mappings` in `canvas_types.json`

---

*Last Updated: September 30, 2025*
