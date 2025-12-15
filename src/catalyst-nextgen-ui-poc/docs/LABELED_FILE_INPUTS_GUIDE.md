# Labeled File Inputs Guide

## Overview

The Project Setup panel now supports **dynamic, labeled file inputs** for advanced workflows that require multiple specific files in a specific order. This enhancement makes the system significantly more flexible and enables complex multi-document workflows.

## Key Features

### 1. **Flexible Task Configuration**

Tasks can now specify exactly which files they need using labeled file inputs:

```json
{
  "requires_labeled_files": true,
  "labeled_file_inputs": [
    {
      "label": "Original Primary Asset",
      "key": "original_primary",
      "description": "The original version of the primary document",
      "required": true
    },
    {
      "label": "Current Derivative Asset",
      "key": "current_derivative",
      "description": "The existing derivative document that needs to be updated",
      "required": true
    },
    {
      "label": "Updated Primary Asset",
      "key": "updated_primary",
      "description": "The new version of the primary document with changes",
      "required": true
    }
  ]
}
```

### 2. **Beautiful, Minimalist UI**

Inspired by Dieter Rams, Don Norman, and Johnny Ive:

- **Clear affordances**: Each file input clearly shows what it's for
- **Progressive disclosure**: Instructions appear only when needed
- **Visual feedback**: Green checkmarks, status indicators, and progress tracking
- **Clean aesthetics**: Rounded corners, subtle shadows, ample whitespace
- **Functional beauty**: Every element has a purpose

### 3. **Backend Support**

New API endpoint for labeled uploads:

```python
@app.post("/api/upload-labeled")
async def upload_labeled_document(file: UploadFile, label: str):
    # Stores file with its specific label
    # Makes it available to agent tools via labeled_documents
```

### 4. **New Agentic Tools**

Three new powerful tools for document workflows:

#### **RedlineDiffTool**
- Word-level granular comparison
- Visual HTML diff output with red/green highlighting
- Change statistics (words added, removed, percentage changed)

#### **DerivativeAnalysisTool**
- Uses OpenAI's o1-preview reasoning model (reasoning_effort: "medium")
- Advanced reasoning for superior pattern recognition
- Deep analysis of transformation patterns (30-60 seconds)
- Identifies how derivatives are created from originals

#### **UpdateDerivativeTool**
- Applies changes intelligently
- Maintains transformation patterns
- Preserves tone, style, and structure

## Example: Update Derivative Asset Workflow

This advanced workflow demonstrates the power of labeled file inputs:

### Step 1: Redline Diff (Original vs Updated Primary)
- Compares the two primary documents
- Generates visual diff showing exactly what changed
- Provides change statistics

### Step 2: Analyze Derivative Creation Pattern
- Uses reasoning model to understand how the derivative was created
- Identifies transformation type (summary, FAQ, checklist, etc.)
- Documents content preservation, modification, and removal patterns
- Analyzes structural and stylistic changes

### Step 3: Identify Primary Changes
- Categorizes changes as major or minor
- Assesses impact on derivative
- Prioritizes updates

### Step 4: Generate Updated Derivative
- Applies same transformation pattern to updated primary
- Maintains consistency with original derivative style
- Incorporates all relevant changes

### Step 5: Redline Diff (Current vs New Derivative)
- Shows what changed in the derivative
- Visual diff for easy review

### Step 6: Update Summary and Rationale
- Comprehensive explanation of all changes
- Verification of pattern consistency
- Quality assurance notes
- Recommendations for manual review

## Creating Tasks with Labeled File Inputs

### 1. Define the Task Structure

In `prompts.json`:

```json
{
  "your_task_key": {
    "name": "Your Task Name",
    "description": "What your task does",
    "icon": "📄",
    "canvas_type": "text_editor",
    "category": "update",
    "requires_labeled_files": true,
    "labeled_file_inputs": [
      {
        "label": "First Document",
        "key": "doc1",
        "description": "Description of what this file should be",
        "required": true
      },
      {
        "label": "Second Document",
        "key": "doc2",
        "description": "Description of what this file should be",
        "required": true
      }
    ],
    "steps": [
      // Your workflow steps
    ]
  }
}
```

### 2. Access Files in Your Tools

In your agentic tools, access labeled documents via context:

```python
labeled_docs = context.get('labeled_documents', {})
doc1_content = labeled_docs.get('doc1', {}).get('content', '')
doc2_content = labeled_docs.get('doc2', {}).get('content', '')
```

### 3. Use Labeled Documents in Step Parameters

For tools like `redline_diff`:

```json
{
  "step_name": "Compare Documents",
  "step_type": "redline_diff",
  "parameters": {
    "doc1_label": "doc1",
    "doc2_label": "doc2"
  }
}
```

## Design Principles Applied

### Dieter Rams' 10 Principles

1. **Good design is innovative**: Labeled file inputs enable previously impossible workflows
2. **Good design makes a product useful**: Clear labels and descriptions guide users
3. **Good design is aesthetic**: Clean, minimalist interface with purposeful elements
4. **Good design makes a product understandable**: Each file slot explains what it needs
5. **Good design is unobtrusive**: The system adapts to the task without overwhelming
6. **Good design is honest**: Shows exactly what files are needed and why
7. **Good design is long-lasting**: Flexible system that accommodates future tasks
8. **Good design is thorough down to the last detail**: Status indicators, validation, feedback
9. **Good design is environmentally-friendly**: Efficient workflows reduce rework
10. **Good design is as little design as possible**: No unnecessary UI elements

### Don Norman's Design Principles

- **Visibility**: All file requirements are immediately visible
- **Feedback**: Real-time status updates and progress tracking
- **Constraints**: Only allows valid file uploads
- **Mapping**: Visual layout matches mental model
- **Consistency**: Same patterns throughout the interface
- **Affordances**: Buttons and inputs clearly indicate their function

### Johnny Ive's Design Philosophy

- **Simplicity**: Complex functionality presented simply
- **Intentional**: Every element serves a purpose
- **Human-centered**: Designed for how people actually work
- **Refined**: Attention to spacing, typography, and visual hierarchy
- **Integrated**: Hardware (backend) and software (frontend) work seamlessly

## Best Practices

### For Task Creators

1. **Be specific with labels**: "Original Primary Asset" is better than "File 1"
2. **Write helpful descriptions**: Explain what the file should contain
3. **Mark required fields**: Use `"required": true` for essential files
4. **Use semantic keys**: `original_primary` is better than `file1`
5. **Order logically**: Present files in the order users would think about them

### For Users

1. **Read the descriptions**: They explain exactly what's needed
2. **Upload files in order**: Makes it easier to track progress
3. **Check the status indicator**: Shows how many files are uploaded
4. **Verify file types**: Make sure you're uploading the right format

## Migration from Traditional Uploads

### Old Way
```json
{
  "requires_dual_upload": true,
  "input_file_types": ["docx", "txt"]
}
```

### New Way (More Powerful)
```json
{
  "requires_labeled_files": true,
  "labeled_file_inputs": [
    {
      "label": "Original Document",
      "key": "original",
      "required": true
    },
    {
      "label": "Updated Document",
      "key": "updated",
      "required": true
    }
  ]
}
```

### Compatibility

- Traditional upload methods still work
- System automatically detects which method to use
- Tasks can use either system, not both

## Technical Details

### Frontend (Alpine.js)

```javascript
// Labeled files are stored in an object by key
labeledFiles: {
  'original_primary': { name: 'doc1.docx', type: 'docx', label: '...' },
  'current_derivative': { name: 'doc2.docx', type: 'docx', label: '...' },
  'updated_primary': { name: 'doc3.docx', type: 'docx', label: '...' }
}

// Upload method
async addLabeledFile(event, label) {
  // Creates FormData with file and label
  // Calls /api/upload-labeled
  // Stores result in labeledFiles[label]
}
```

### Backend (FastAPI)

```python
# Labeled documents stored in global state
current_state = {
    "labeled_documents": {
        "original_primary": {
            "filename": "doc1.docx",
            "content": "...",
            "file_type": "docx",
            "label": "original_primary"
        }
    }
}

# Passed to agent tools in context
context = {
    "labeled_documents": current_state.get("labeled_documents", {}),
    # ... other context
}
```

### Agent Tools

```python
class YourTool(AgenticTool):
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        labeled_docs = context.get('labeled_documents', {})
        
        # Access specific labeled files
        original = labeled_docs.get('original_primary', {}).get('content', '')
        derivative = labeled_docs.get('current_derivative', {}).get('content', '')
        
        # Process files
        # Return results
```

## Advanced Patterns

### Conditional File Inputs

Currently, all labeled inputs are shown. Future enhancement could support:
- Optional files
- Conditional fields based on other selections
- Dynamic file input generation

### File Validation

Tasks can specify allowed file types globally:

```json
{
  "input_file_types": ["docx", "txt", "md"],
  "labeled_file_inputs": [
    // These inherit the file type restrictions
  ]
}
```

### Multi-Stage Workflows

Labeled inputs work perfectly for workflows with multiple stages:

1. **Analysis Stage**: Compare documents, identify changes
2. **Reasoning Stage**: Deep analysis with reasoning models
3. **Generation Stage**: Create updated outputs
4. **Validation Stage**: Verify changes with diffs and summaries

## Troubleshooting

### Files Not Uploading
- Check file size limits
- Verify file type is supported
- Check browser console for errors

### Labels Not Matching
- Ensure keys in `labeled_file_inputs` match keys used in `parameters`
- Check spelling and case sensitivity

### Tool Not Finding Files
- Verify `context.get('labeled_documents')` in your tool
- Check that files were uploaded successfully
- Confirm backend is passing labeled_documents in context

## Future Enhancements

- [ ] Drag-and-drop file uploads
- [ ] File preview before upload
- [ ] Batch file selection
- [ ] File swap/reorder functionality
- [ ] Persistent file storage across sessions
- [ ] File comparison preview
- [ ] Custom file type validation per input

## Conclusion

Labeled file inputs transform the Project Setup panel from a simple file uploader into a powerful, flexible system that can handle complex multi-document workflows. The design is clean, intuitive, and scalable—enabling endless possibilities for advanced document processing tasks.

