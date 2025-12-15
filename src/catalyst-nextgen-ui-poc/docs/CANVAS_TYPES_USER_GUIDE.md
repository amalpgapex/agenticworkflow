# Canvas Types - User Guide

## What Are Canvas Types?

**Canvas Types** are different ways to view and edit content in InK Studio. The application automatically selects the right canvas based on your uploaded file and chosen direction.

---

## Currently Available Canvas Types

### 📝 **Text Editor**
- **What it does**: Lets you edit documents with rich text formatting
- **Works with**: Word documents (`.docx`), text files (`.txt`), Markdown (`.md`)
- **Features**:
  - Bold, italic, underline formatting
  - Headings (H1, H2, H3)
  - Bullet and numbered lists
  - Word-like editing experience
- **Export to**: Word (.docx), Text (.txt), Markdown (.md)

### 🎧 **Audio Player**
- **What it does**: Plays generated podcast audio
- **Works with**: Generated audio files from "Generate Podcast" direction
- **Features**:
  - Play/pause controls
  - Progress bar
  - Volume control
- **Export to**: MP3 audio file

### 📷 **Image Viewer** (Coming Soon)
- View and annotate images
- Works with PNG, JPG, GIF, WebP

### 📄 **PDF Viewer** (Coming Soon)
- View PDF documents
- Page navigation, zoom, search

### 💻 **Code Editor** (Coming Soon)
- Edit code with syntax highlighting
- Works with Python, JavaScript, etc.

### 📊 **Spreadsheet Viewer** (Coming Soon)
- View and edit tables
- Works with Excel, CSV

---

## How It Works

### 1. **Upload Your File**
The system detects your file type and prepares the appropriate canvas.

**Example:**
- Upload `report.docx` → Sets up **Text Editor** canvas
- Upload from podcast generation → Sets up **Audio Player** canvas

### 2. **Choose a Direction**
Only directions compatible with your file type will be shown.

**Example:**
- If you uploaded `.docx`, you'll see:
  - ✅ Technical Guide to FAQs
  - ✅ Executive Summary
  - ✅ Generate Podcast
  - ✅ Fact-Checked Rewrite
  
**Visual Indicator:**
Below the direction dropdown, you'll see which canvas will be used:
```
📝 Text Editor
```

### 3. **Run the Workflow**
The output streams to the canvas in real-time.

### 4. **Edit in the Canvas**
Each canvas type has its own editing capabilities:

**Text Editor:**
- Click to edit text
- Use toolbar to format
- Changes are live

**Audio Player:**
- Click play to listen
- Use timeline to navigate
- (Audio content is not editable)

### 5. **Re-run from Any Step**
- Click on any completed step in the Workflow panel
- Edit the content in the canvas
- Click the small 🔄 button next to that step
- Workflow re-runs from that step with your edits

### 6. **Export**
Click **Export to Word** (or appropriate export button for canvas type)

---

## Canvas Compatibility

| Your File | Compatible Directions | Canvas Used |
|-----------|----------------------|-------------|
| `.docx` Word | All text transformations | 📝 Text Editor |
| `.txt` Text | All text transformations | 📝 Text Editor |
| `.md` Markdown | All text transformations | 📝 Text Editor |
| `.pdf` PDF* | Read-only transformations | 📄 PDF Viewer |
| Generated audio | Podcast playback | 🎧 Audio Player |

*Future support

---

## Tips & Tricks

### 🎯 **Quick Formatting (Text Editor)**
- Select text and click toolbar buttons
- Keyboard shortcuts work too (Ctrl+B for bold, etc.)

### 🔄 **Iterative Refinement**
1. Run initial workflow
2. Click on step 2 output
3. Edit the text
4. Click 🔄 next to step 2
5. Steps 2+ re-run with your edits

### 📋 **Direction Filtering**
- Only see directions that work with your file type
- Upload different file types to unlock different directions

### 🎨 **Canvas Indicators**
- Look for the canvas icon below the Direction dropdown
- This tells you what editing experience to expect

---

## Examples

### Example 1: Text Document Workflow
```
1. Upload: presentation.docx
   → Canvas: 📝 Text Editor

2. Choose: "Executive Summary"
   → Confirms: 📝 Text Editor

3. Click "Draft"
   → Streams to Text Editor canvas

4. Edit the summary
   → Use formatting toolbar

5. Export to Word
   → Downloads formatted .docx
```

### Example 2: Podcast Generation
```
1. Upload: article.docx
   → Canvas: 📝 Text Editor (default)

2. Choose: "Generate Podcast"
   → Switches to: 🎧 Audio Player

3. Click "Draft"
   → Step 1: Creates script (Text Editor)
   → Step 2: Generates audio (Audio Player)

4. Click Step 2
   → Audio player appears
   → Click play to listen

5. Export
   → Downloads .mp3 file
```

### Example 3: Iterative Editing
```
1. Run "Fact-Checked Rewrite"
   → Step 1: Initial Rewrite
   → Step 2: Verify Facts
   → Step 3: Final Corrections

2. Click Step 1 in workflow
   → View initial rewrite in Text Editor

3. Make edits to improve tone

4. Click 🔄 next to Step 1
   → Steps 1, 2, 3 re-run with your edits
```

---

## Future Canvas Types

We're planning to add:

- **📷 Image Viewer**: View and annotate images
- **📄 PDF Viewer**: Navigate and annotate PDFs
- **💻 Code Editor**: Syntax highlighting for code
- **📊 Spreadsheet Viewer**: Edit tables and data
- **🎬 Video Player**: View and scrub through videos
- **🗺️ Mind Map Viewer**: Visualize concept relationships

---

## Troubleshooting

**Q: Why don't I see my favorite direction?**  
A: The direction may not support your file type. Try uploading a different file format.

**Q: The canvas looks wrong**  
A: Refresh the page (Ctrl+F5). The canvas should auto-detect based on your direction.

**Q: I can't edit the content**  
A: Some canvases are view-only (like Audio Player). Check the canvas capabilities.

**Q: Export button is missing**  
A: Make sure the workflow is complete. Export only works after processing finishes.

**Q: Audio isn't playing**  
A: Check browser console for errors. Ensure the audio file was generated successfully.

---

## Developer: Adding New Canvas Types

See `CANVAS_TYPES_ARCHITECTURE.md` for technical details on:
- Creating new canvas types
- Registering them in the system
- Building custom UI components
- Implementing export logic

---

*Last Updated: September 30, 2025*
